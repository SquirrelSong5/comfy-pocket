import asyncio
import os
import hashlib
import hmac
import io
import json
import logging
import pathlib
import secrets
import time
import urllib.parse
import uuid
from aiohttp import web, ClientSession, ClientTimeout, FormData, WSMsgType
from PIL import Image, UnidentifiedImageError
from .workflows import compile_app, public_app, build_prompt
from .runtime import Runtime
from .previews import make_preview
from .progress import apply_event, record_text
from .security import sign_session, valid_session, local_client, allowed_client

ROOT=pathlib.Path(__file__).resolve().parent.parent
HOME=pathlib.Path(os.environ.get('COMFY_POCKET_HOME',str(ROOT))).resolve()
STATE=HOME/'state';STATE.mkdir(parents=True,exist_ok=True)
CONFIG=HOME/'config.json'
CLIENT_ID='comfy-pocket-'+hashlib.sha256(str(STATE).encode()).hexdigest()[:16]
CONF=json.loads(CONFIG.read_text(encoding='utf-8'))
AUTH=STATE/'access.json'
if not AUTH.exists():AUTH.write_text(json.dumps({'code':secrets.token_urlsafe(12),'secret':secrets.token_hex(32)}),encoding='utf-8')
ACCESS=json.loads(AUTH.read_text(encoding='utf-8'))
def load_state(name):
    path=STATE/name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
def save_state(name,data):
    path=STATE/name;temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');temp.replace(path)
JOBS=load_state('jobs.json');UPLOADS=load_state('uploads.json')
CATALOG={};APP_ERRORS=[];STAMP={};INFO={};LAST_REFRESH=0
LOCK=asyncio.Lock();SUBMIT_LOCK=asyncio.Lock();CLIENT=None
ATTEMPTS={}
RUNTIME=None
SUBSCRIBERS=set()
PREVIEW_LOCK=asyncio.Lock()
WS_CONNECTED=False
WS_READY=asyncio.Event()

def response(data,status=200):
    r=web.json_response(data,status=status);r.enable_compression();r.headers['Cache-Control']='no-store';return r

@web.middleware
async def guard(request,handler):
    if request.host.split(':')[0].lower() not in CONF['hosts']:return response({'error':'访问地址不受信任'},403)
    if not allowed_client(request.remote or '',CONF['networks']):return response({'error':'仅允许本机、指定局域网与 Tailscale 连接'},403)
    origin=request.headers.get('Origin')
    if origin and origin!=f'{request.scheme}://{request.host}':return response({'error':'跨站请求被拒绝'},403)
    if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('X-Requested-With')!='comfy-lite':return response({'error':'请求来源不正确'},403)
    authenticated=local_client(request.remote or '') or valid_session(ACCESS['secret'],request.cookies.get('lite_session',''))
    request['authenticated']=authenticated
    if request.path.startswith('/api/') and request.path not in ('/api/session','/api/login') and not authenticated:return response({'error':'请先输入访问码'},401)
    try:r=await handler(request)
    except ValueError as e:r=response({'error':str(e)},400)
    except (asyncio.TimeoutError,ConnectionError,OSError) as e:
        logging.warning('Backend unavailable: %s',type(e).__name__);r=response({'error':'ComfyUI 暂时无法连接，请确认电脑上的服务已启动'},502)
    except web.HTTPException:raise
    except Exception:
        logging.exception('Request failed');r=response({'error':'请求失败，请重试或查看电脑上的服务日志'},500)
    r.headers['X-Content-Type-Options']='nosniff'
    r.headers['Referrer-Policy']='no-referrer'
    r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    return r

async def upstream(path,data=None):
    async with CLIENT.request('POST' if data is not None else 'GET',CONF['comfy_url']+path,json=data) as r:
        raw=await r.read()
        body=json.loads(raw) if raw else {}
        if r.status>=400:
            error=body.get('error',{})
            message=error.get('message',str(error)) if isinstance(error,dict) else str(error)
            details=[]
            for node in body.get('node_errors',{}).values():
                details += [e.get('message','')+': '+e.get('details','') for e in node.get('errors',[])]
            raise ValueError('ComfyUI 校验失败：'+(('; '.join(details)) or message)[:1200])
        return body

async def refresh(force=False):
    global LAST_REFRESH,INFO,CATALOG,APP_ERRORS,STAMP
    async with LOCK:
        if not force and time.monotonic()-LAST_REFRESH<15:return
        listing=await upstream('/userdata?dir=workflows&recurse=true&full_info=true')
        files=[f for f in listing if f['path'].endswith('.app.json')]
        stamps={f['path']:(f['modified'],f['size']) for f in files}
        if force or not INFO or stamps!=STAMP:
            INFO=await upstream('/object_info');apps={};errors=[]
            for f in files:
                path='workflows/'+f['path']
                try:
                    d=await upstream('/userdata/'+urllib.parse.quote(path,safe=''))
                    a=compile_app(path,d,INFO);apps[a['id']]=a
                except (ValueError,KeyError,IndexError,TypeError) as e:errors.append({'name':pathlib.PurePosixPath(f['path']).name.removesuffix('.app.json'),'error':str(e)})
            CATALOG=apps;APP_ERRORS=errors;STAMP=stamps
        LAST_REFRESH=time.monotonic()

async def session(request):return response({'authenticated':request['authenticated'],'local':local_client(request.remote or ''),'product':'comfy-pocket'})
async def login(request):
    now=time.monotonic();key=request.remote;attempts=[x for x in ATTEMPTS.get(key,[]) if now-x<60];ATTEMPTS[key]=attempts
    if len(attempts)>=5:return response({'error':'尝试次数过多，请一分钟后重试'},429)
    body=await request.json();code=body.get('code','');attempts.append(now)
    if not isinstance(code,str) or not hmac.compare_digest(code,ACCESS['code']):return response({'error':'访问码不正确'},401)
    ATTEMPTS.pop(key,None);r=response({'authenticated':True});r.set_cookie('lite_session',sign_session(ACCESS['secret']),httponly=True,samesite='Strict',max_age=30*86400,secure=request.secure);return r
async def access_code(request):
    if not local_client(request.remote or ''):raise web.HTTPForbidden()
    return response({'code':ACCESS['code'],'urls':[f"http://{host}:{CONF['port']}" for host in CONF['bind'] if host!='127.0.0.1']})
async def apps(request):
    if (await RUNTIME.status())['online']:await refresh(request.query.get('refresh')=='1')
    return response({'apps':[public_app(a) for a in CATALOG.values()],'unsupported':APP_ERRORS})

async def upload(request):
    reader=await request.multipart();part=await reader.next()
    if part is None or part.name!='file':raise ValueError('请选择图片')
    raw=bytearray()
    while chunk:=await part.read_chunk():
        raw.extend(chunk)
        if len(raw)>20*1024*1024:raise ValueError('单张图片不能超过 20 MB')
    try:
        im=Image.open(io.BytesIO(raw))
        if im.width*im.height>40_000_000:raise ValueError('图片不能超过 4000 万像素')
        im.load();clean=io.BytesIO();im.convert('RGBA' if 'A' in im.getbands() else 'RGB').save(clean,format='PNG')
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise ValueError('无法读取此图片，请使用 PNG、JPEG 或 WebP')
    token=uuid.uuid4().hex;form=FormData();form.add_field('image',clean.getvalue(),filename='lite-'+token+'.png',content_type='image/png');form.add_field('overwrite','false')
    async with CLIENT.post(CONF['comfy_url']+'/upload/image',data=form) as r:
        if r.status!=200:raise ValueError('图片上传到 ComfyUI 失败')
        d=await r.json()
    filename=(d.get('subfolder','')+'/' if d.get('subfolder') else '')+d['name'];UPLOADS[token]=filename;save_state('uploads.json',UPLOADS)
    return response({'id':token,'name':part.filename or '图片','width':im.width,'height':im.height})

async def submit(request):
    body=await request.json();await refresh();ident=body.get('app');a=CATALOG.get(ident)
    if not a:raise ValueError('应用不存在，请刷新列表')
    if body.get('revision')!=a['revision']:raise ValueError('官方应用已更新，请刷新后重新填写参数')
    files=body.get('images',{})
    if not isinstance(files,dict) or len(files)>32:raise ValueError('图片参数格式不正确')
    if any(not isinstance(v,str) or v not in UPLOADS for v in files.values()):raise ValueError('图片已失效，请重新上传')
    prompt,values=build_prompt(a,body.get('values',{}),{k:UPLOADS[v] for k,v in files.items()})
    async with SUBMIT_LOCK:
        await update_jobs()
        if sum(j['status'] in ('queued','running') for j in JOBS.values())>=8:raise ValueError('待处理任务已达 8 个，请等待完成')
        pid=str(uuid.uuid4())
        JOBS[pid]={'id':pid,'app':ident,'title':a['title'],'created':time.time(),'status':'queued','values':values,'outputs':[], 'texts':[], 'node_labels':{k:v.get('_meta',{}).get('title',v['class_type']) for k,v in prompt.items()}}
        try:await upstream('/prompt',{'prompt':prompt,'client_id':CLIENT_ID,'prompt_id':pid})
        except Exception:
            JOBS.pop(pid,None);raise
        save_state('jobs.json',JOBS)
        publish(JOBS[pid])
    return response(public_job(JOBS[pid]),201)

async def update_jobs():
    active=[j for j in JOBS.values() if j['status'] in ('queued','running')]
    if not active:return
    q=await upstream('/queue');running={x[1] for x in q['queue_running']};pending={x[1] for x in q['queue_pending']}
    for j in active:
        h=await upstream('/history/'+j['id'])
        if j['id'] in h:
            r=h[j['id']];j['status']='success' if r['status']['status_str']=='success' else 'error';j['finished']=time.time();j['outputs']=[];j.pop('progress',None)
            j['texts']=[]
            for node_id,node in r.get('outputs',{}).items():
                record_text(j,node_id,node)
                for key in ('images','videos','gifs','audio'):
                    for item in node.get(key,[]):
                        if isinstance(item,dict) and item.get('filename'):
                            ext=pathlib.PurePosixPath(item['filename']).suffix.lower();kind='video' if ext in ('.mp4','.webm','.mkv') else ('audio' if key=='audio' else 'image')
                            j['outputs'].append({**{k:item.get(k,'') for k in ('filename','subfolder','type')},'kind':kind})
            for event,data in r['status'].get('messages',[]):
                if event=='execution_error':j['error']=data.get('exception_message','执行失败')[:500]
        elif j['id'] in running:j['status']='running'
        elif j['id'] in pending:j['status']='queued'
        elif time.time()-j['created']>30:j['status']='error';j['error']='任务已从 ComfyUI 队列移除或服务已重启'
    save_state('jobs.json',JOBS)

async def jobs(request):
    if (await RUNTIME.status())['online']:await update_jobs()
    return response({'jobs':[public_job(j) for j in sorted(JOBS.values(),key=lambda j:j['created'],reverse=True)[:30]],'realtime':WS_CONNECTED})
async def cancel(request):
    pid=request.match_info['ident'];j=JOBS.get(pid)
    if not j:raise web.HTTPNotFound()
    q=await upstream('/queue')
    if any(x[1]==pid for x in q['queue_running']):await upstream('/interrupt',{'prompt_id':pid})
    elif any(x[1]==pid for x in q['queue_pending']):await upstream('/queue',{'delete':[pid]})
    j['status']='cancelled';save_state('jobs.json',JOBS);return response(j)
async def media(request):
    j=JOBS.get(request.match_info['ident']);index=int(request.match_info['index'])
    if not j or not 0<=index<len(j['outputs']):raise web.HTTPNotFound()
    item=j['outputs'][index];query=urllib.parse.urlencode({k:item[k] for k in ('filename','subfolder','type')});headers={}
    if request.query.get('preview')=='1' and item['kind']=='image':
        cache=STATE/'previews';cache.mkdir(exist_ok=True)
        target=cache/(j['id']+'-'+str(index)+'.webp')
        async with PREVIEW_LOCK:
            if not target.exists():
                async with CLIENT.get(CONF['comfy_url']+'/view?'+query) as original:
                    if original.status!=200:raise web.HTTPNotFound()
                    raw=bytearray()
                    async for chunk in original.content.iter_chunked(65536):
                        raw.extend(chunk)
                        if len(raw)>80*1024*1024:raise ValueError('原图过大，请使用下载原图')
                small=await asyncio.to_thread(make_preview,bytes(raw))
                target.write_bytes(small)
        return web.FileResponse(target,headers={'Content-Type':'image/webp','Cache-Control':'private, max-age=86400'})
    if request.headers.get('Range'):headers['Range']=request.headers['Range']
    async with CLIENT.get(CONF['comfy_url']+'/view?'+query,headers=headers) as upstream_response:
        if upstream_response.status not in (200,206,416):raise web.HTTPNotFound()
        r=web.StreamResponse(status=upstream_response.status,headers={k:v for k,v in upstream_response.headers.items() if k.lower() in ('content-type','content-length','content-range','accept-ranges')})
        r.headers['Cache-Control']='private, max-age=86400';r.headers['X-Content-Type-Options']='nosniff'
        if request.query.get('download')=='1':r.headers['Content-Disposition']="attachment; filename*=UTF-8''"+urllib.parse.quote(item['filename'],safe='')
        await r.prepare(request)
        async for chunk in upstream_response.content.iter_chunked(65536):await r.write(chunk)
        return r

def public_job(job):
    return {k:v for k,v in job.items() if k!='node_labels'}

def publish(job):
    event={'job':public_job(job),'realtime':WS_CONNECTED}
    for queue in tuple(SUBSCRIBERS):
        if queue.full():queue.get_nowait()
        queue.put_nowait(event)

async def events(request):
    r=web.StreamResponse(headers={'Content-Type':'text/event-stream','Cache-Control':'no-cache','X-Accel-Buffering':'no'})
    await r.prepare(request);queue=asyncio.Queue(maxsize=64);SUBSCRIBERS.add(queue)
    try:
        await r.write(('data: '+json.dumps({'realtime':WS_CONNECTED})+'\n\n').encode())
        while True:
            try:
                data=await asyncio.wait_for(queue.get(),15)
                payload='data: '+json.dumps(data,ensure_ascii=False)+'\n\n'
            except asyncio.TimeoutError:payload=': keepalive\n\n'
            await r.write(payload.encode())
    except (ConnectionError,asyncio.CancelledError):pass
    finally:SUBSCRIBERS.discard(queue)
    return r

async def listen_progress():
    global WS_CONNECTED
    while True:
        try:
            async with CLIENT.ws_connect(CONF['comfy_url']+'/ws?clientId='+CLIENT_ID,heartbeat=20) as ws:
                WS_CONNECTED=True;WS_READY.set()
                for j in JOBS.values():
                    if j['status'] in ('queued','running'):j.pop('progress',None)
                for queue in tuple(SUBSCRIBERS):
                    if not queue.full():queue.put_nowait({'realtime':True})
                async for message in ws:
                    if message.type!=WSMsgType.TEXT:continue
                    event=json.loads(message.data)
                    if apply_event(JOBS,event):
                        publish(JOBS[event['data']['prompt_id']])
        except asyncio.CancelledError:raise
        except Exception as e:logging.warning('Progress connection: %s',type(e).__name__)
        finally:
            WS_CONNECTED=False;WS_READY.clear()
            for queue in tuple(SUBSCRIBERS):
                if not queue.full():queue.put_nowait({'realtime':False})
        await asyncio.sleep(3)

async def runtime_status(request):
    return response(await RUNTIME.status())

async def runtime_action(request):
    body=await request.json()
    if set(body)!={'action'}:raise ValueError('只能提交启动、停止或重启操作')
    async with SUBMIT_LOCK:
        return response(await RUNTIME.action(body['action']))

async def index(request):
    r=web.FileResponse(ROOT/'web/dist/index.html');r.headers['Cache-Control']='no-cache';return r

async def start():
    from .service_control import record_server, clear_record
    global CLIENT,RUNTIME
    logging.basicConfig(level=logging.INFO)
    CLIENT=ClientSession(timeout=ClientTimeout(total=90),trust_env=False)
    RUNTIME=Runtime(CONF,STATE,CLIENT)
    app=web.Application(middlewares=[guard],client_max_size=21*1024*1024)
    app.add_routes([web.get('/api/runtime',runtime_status),web.post('/api/runtime',runtime_action),web.get('/api/session',session),web.post('/api/login',login),web.get('/api/access-code',access_code),web.get('/api/apps',apps),web.post('/api/upload',upload),web.post('/api/jobs',submit),web.get('/api/jobs',jobs),web.get('/api/events',events),web.post('/api/jobs/{ident}/cancel',cancel),web.get('/api/media/{ident}/{index}',media),web.get('/',index)])
    app.router.add_static('/assets/',ROOT/'web/dist/assets',show_index=False)
    runner=web.AppRunner(app,access_log=None);await runner.setup()
    progress_task=asyncio.create_task(listen_progress())
    bound=set()
    process_record=None
    try:
        while True:
            for host in CONF['bind']:
                if host in bound:continue
                try:
                    await web.TCPSite(runner,host,CONF['port']).start();bound.add(host)
                    if host=='127.0.0.1' and process_record is None:process_record=record_server(HOME)
                    logging.info('Listening on %s:%s',host,CONF['port'])
                except OSError:pass
            await asyncio.sleep(15)
    finally:
        if process_record is not None:clear_record(HOME,process_record)
        progress_task.cancel()
        await asyncio.gather(progress_task,return_exceptions=True)
        await CLIENT.close();await runner.cleanup()
if __name__=='__main__':asyncio.run(start())
