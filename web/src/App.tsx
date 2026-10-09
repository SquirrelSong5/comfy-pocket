import { useEffect, useRef, useState } from 'react'
import { Aperture, ArrowDownToLine, ArrowUpRight, Check, ChevronDown, Clock3, Film, ImagePlus, Images, Loader2, Power, Play, RefreshCw, ShieldCheck, Smartphone, X } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Field, FieldLabel, FieldDescription, FieldGroup } from '@/components/ui/field'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription, EmptyMedia } from '@/components/ui/empty'
import './App.css'

type Value = string | number | boolean
interface Control { key:string; label:string; kind:string; default:Value; min?:number; max?:number; step?:number; options?:Value[]; advanced?:boolean; random_seed?:boolean }
interface Group { label:string; fields:string[]; min:number; count?:string; toggle?:string }
interface Application { id:string; name:string; model:string; title:string; purpose:string; description:string; revision:string; fields:Control[]; imageGroups:Group[] }
interface Preferences { selected:string; drafts:Record<string,Record<string,Value>> }
interface Upload { id:string; name:string; preview:string }
interface Output { filename:string; kind:string }
interface RuntimeState {state:string;online:boolean;manageable:boolean;error:string;pid:number|null}
interface Job { id:string; app:string; title:string; status:string; created:number; error?:string; outputs:Output[]; values:Record<string,Value>; phase?:string; progress?:{node:string;label:string;value:number;max:number}; texts?:{node:string;label:string;text:string}[] }
const statusLabel:Record<string,string>={queued:'排队中',running:'正在生成',success:'已完成',error:'生成失败',cancelled:'已取消'}
async function api<T>(path:string, options:RequestInit={}):Promise<T> {
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),90000)
  try { const r=await fetch('/api'+path,{...options,headers:{'X-Requested-With':'comfy-lite',...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...options.headers},signal:controller.signal})
  const d=await r.json();if(!r.ok)throw new Error(d.error||'请求失败');return d } finally {clearTimeout(timeout)}
}
function media(job:Job,index:number){return `/api/media/${job.id}/${index}`}
function Preview({job,onError,realtime}:{job:Job|undefined;onError:(message:string)=>void;realtime:boolean}) {
  if(!job)return <Empty className="preview-empty"><EmptyHeader><EmptyMedia><Aperture className="empty-aperture"/></EmptyMedia><EmptyTitle>从一个想法开始</EmptyTitle><EmptyDescription>描述画面，点击生成。<br/>作品会出现在这里。</EmptyDescription></EmptyHeader></Empty>
  if(job.status==='running'||job.status==='queued')return <Empty className="preview-empty"><EmptyHeader><EmptyMedia><Loader2 className="animate-spin"/></EmptyMedia><EmptyTitle>{job.phase==='finishing'?'正在整理结果':statusLabel[job.status]}</EmptyTitle><EmptyDescription>任务在电脑上执行，可以暂时离开页面。<br/>首次加载模型可能需要更久。</EmptyDescription></EmptyHeader><div className="generation-progress"><div className="progress-heading"><span>{job.progress?.label||(job.status==='queued'?'等待电脑开始执行':'等待节点进度')}</span>{!!job.progress?.max&&<strong>{Math.floor(job.progress.value/job.progress.max*100)}%</strong>}</div><Progress aria-label="当前节点进度" value={realtime&&job.progress?.max?job.progress.value/job.progress.max*100:null}/><p>{!realtime?'实时连接恢复中，任务仍在电脑上执行':job.progress?.max?`当前节点 ${job.progress.value} / ${job.progress.max} · 非整个任务百分比`:'模型加载等阶段可能没有百分比'}</p></div><Button variant="outline" onClick={()=>void api(`/jobs/${job.id}/cancel`,{method:'POST',body:'{}'}).catch(e=>onError(e.message))}>取消此任务</Button></Empty>
  if(job.status==='error')return <Alert variant="destructive"><AlertDescription>{job.error||'生成失败，请重试。'}</AlertDescription></Alert>
  if(!job.outputs.length)return <Empty><EmptyHeader><EmptyTitle>{statusLabel[job.status]}</EmptyTitle><EmptyDescription>此任务没有可显示的图片或视频输出。</EmptyDescription></EmptyHeader></Empty>
  return <div className="output-grid">{job.outputs.map((o,i)=><figure key={i} className="output-item">{o.kind==='video'?<video src={media(job,i)} controls playsInline preload="metadata"/>:o.kind==='audio'?<audio src={media(job,i)} controls preload="none"/>:<img src={media(job,i)+'?preview=1'} alt="生成结果" loading="lazy" decoding="async"/>}<figcaption><span>{o.filename}</span>{o.kind==='image'&&<a className="original-link" href={media(job,i)} target="_blank" rel="noreferrer">查看原图</a>}<Button variant="ghost" size="icon" render={<a href={media(job,i)+'?download=1'} download aria-label="下载作品"/>}><ArrowDownToLine/></Button></figcaption></figure>)}</div>
}
function App(){
  const [auth,setAuth]=useState<{authenticated:boolean;local:boolean}|null>(null)
  const [apps,setApps]=useState<Application[]>([]),[unsupported,setUnsupported]=useState<{name:string;error:string}[]>([])
  const [selected,setSelected]=useState(''),[view,setView]=useState<'create'|'history'>('create')
  const [drafts,setDrafts]=useState<Record<string,Record<string,Value>>>({}),[files,setFiles]=useState<Record<string,Record<string,Upload>>>({})
  const [runtime,setRuntime]=useState<RuntimeState|null>(null),[runtimeBusy,setRuntimeBusy]=useState(false)
  const wasOnline=useRef<boolean|undefined>(undefined)
  const [realtime,setRealtime]=useState(false)
  const [jobs,setJobs]=useState<Job[]>([]),[shown,setShown]=useState<string|null>(null)
  const [error,setError]=useState(''),[loading,setLoading]=useState(false),[uploading,setUploading]=useState(false),[submitting,setSubmitting]=useState(false)
  const [code,setCode]=useState(''),[pairCode,setPairCode]=useState(''),[phoneOpen,setPhoneOpen]=useState(false)
  const [accessUrls,setAccessUrls]=useState<string[]>([])
  const objectUrls=useRef<string[]>([])
  const revisions=useRef<Record<string,string>>({})
  const pendingValues=useRef<Record<string,Record<string,Value>>>({})
  const saveQueue=useRef<Promise<void>>(Promise.resolve())
  const queuedApps=useRef(new Set<string>())
  const saveVersion=useRef(0)
  const [saveStatus,setSaveStatus]=useState('参数自动保存到电脑'),[saveFailed,setSaveFailed]=useState(false)
  const current=apps.find(a=>a.id===selected),values=drafts[selected]||{},pictures=files[selected]||{}
  const latest=jobs.find(j=>j.id===shown)||jobs.find(j=>j.app===selected)
  const activeCount=jobs.filter(j=>['queued','running'].includes(j.status)).length
  const sync=async(force=false)=>{setLoading(true);setError('');try{
    const d=await api<{apps:Application[];unsupported:{name:string;error:string}[]}>(`/apps${force?'?refresh=1':''}`)
    await saveQueue.current
    const saved=await api<Preferences>('/preferences')
    setApps(d.apps);setUnsupported(d.unsupported)
    setSelected(s=>d.apps.some(a=>a.id===s)?s:d.apps.some(a=>a.id===saved.selected)?saved.selected:d.apps[0]?.id||'')
    setDrafts(Object.fromEntries(d.apps.map(a=>[a.id,{...saved.drafts[a.id],...pendingValues.current[a.id]}])))
    const previous=revisions.current
    setFiles(old=>Object.fromEntries(d.apps.map(a=>[a.id,previous[a.id]===a.revision?old[a.id]||{}:{}])))
    revisions.current=Object.fromEntries(d.apps.map(a=>[a.id,a.revision]))
  }catch(e){setError((e as Error).message)}finally{setLoading(false)}}
  useEffect(()=>{void api<{authenticated:boolean;local:boolean}>('/session').then(setAuth).catch(e=>setError(e.message));return()=>objectUrls.current.forEach(URL.revokeObjectURL)},[])
  useEffect(()=>{if(auth?.authenticated)void sync()},[auth?.authenticated])
  useEffect(()=>{if(!auth?.authenticated)return;let stopped=false;let timer:ReturnType<typeof setTimeout>;const poll=async()=>{try{const d=await api<{jobs:Job[]}>('/jobs');if(!stopped)setJobs(d.jobs)}catch(e){if(!stopped)setError((e as Error).message)}if(!stopped)timer=setTimeout(poll,3000)};void poll();return()=>{stopped=true;clearTimeout(timer)}},[auth?.authenticated])
  useEffect(()=>{
    if(!auth?.authenticated)return
    const stream=new EventSource('/api/events')
    stream.onmessage=e=>{const d=JSON.parse(e.data) as {job?:Job;realtime:boolean};setRealtime(d.realtime);if(d.job){const job=d.job;setJobs(old=>[job,...old.filter(j=>j.id!==job.id)].sort((a,b)=>b.created-a.created).slice(0,30))}}
    stream.onerror=()=>setRealtime(false)
    return()=>stream.close()
  },[auth?.authenticated])
  useEffect(()=>{
    if(!auth?.authenticated)return
    let stopped=false;let timer:ReturnType<typeof setTimeout>
    const poll=async()=>{try{const d=await api<RuntimeState>('/runtime');if(!stopped){setRuntime(d);if(d.online&&wasOnline.current===false)void sync(true);wasOnline.current=d.online}}catch(e){if(!stopped)setError((e as Error).message)}if(!stopped)timer=setTimeout(poll,3000)}
    void poll();return()=>{stopped=true;clearTimeout(timer)}
  },[auth?.authenticated])
  async function controlRuntime(action:'start'|'stop'|'restart'){
    setRuntimeBusy(true);setError('')
    try{const d=await api<RuntimeState>('/runtime',{method:'POST',body:JSON.stringify({action})});setRuntime(d);if(d.online)void sync(true)}catch(e){setError((e as Error).message)}finally{setRuntimeBusy(false)}
  }
  function savePreferences(app:string,patch?:Record<string,Value>,reset=false){
    if(patch)pendingValues.current[app]={...pendingValues.current[app],...patch}
    saveVersion.current++
    setSaveStatus('正在保存到电脑…');setSaveFailed(false)
    if(patch&&queuedApps.current.has(app))return
    if(patch)queuedApps.current.add(app)
    saveQueue.current=saveQueue.current.then(async()=>{
      if(patch){queuedApps.current.delete(app);patch={...pendingValues.current[app]}}
      const version=saveVersion.current
      try{
        const saved=await api<Preferences>('/preferences',{method:'POST',body:JSON.stringify({app,...(patch?{values:patch}:{}),...(reset?{reset:true}:{})})})
        if(reset){delete pendingValues.current[app];setDrafts(old=>({...old,[app]:saved.drafts[app]||{}}))}
        else for(const [key,value] of Object.entries(patch||{}))if(pendingValues.current[app]?.[key]===value)delete pendingValues.current[app][key]
        if(version===saveVersion.current){setSaveStatus('已保存到电脑 · 所有设备共用');setSaveFailed(false)}
      }catch(e){setSaveStatus('保存失败：'+(e as Error).message);setSaveFailed(true)}
    })
  }
  const choose=(id:string)=>{setSelected(id);setShown(null);setView('create');setError('');savePreferences(id)}
  const change=(key:string,value:Value)=>{
    setDrafts(d=>({...d,[selected]:{...d[selected],[key]:value}}))
    const field=current?.fields.find(f=>f.key===key)
    if(field&&(field.kind==='int'||field.kind==='float')&&(typeof value!=='number'||!Number.isFinite(value)||(field.kind==='int'&&!Number.isInteger(value))||value<(field.min??-Infinity)||value>(field.max??Infinity))){saveVersion.current++;setSaveStatus('参数尚未保存：请输入范围内的有效数值');setSaveFailed(true);return}
    savePreferences(selected,{...pendingValues.current[selected],[key]:value})
  }
  async function addFiles(list:FileList|null,keys:string[]){
    if(!list||!current)return;const incoming=Array.from(list);const appId=current.id
    if(incoming.length>keys.length){setError(`最多还可添加 ${keys.length} 张图片`);return}
    setUploading(true);setError('')
    try{for(let i=0;i<incoming.length;i++){const file=incoming[i];if(file.size>20*1024*1024)throw new Error('单张图片不能超过 20 MB');const form=new FormData();form.append('file',file);const result=await api<{id:string;name:string}>('/upload',{method:'POST',body:form});const preview=URL.createObjectURL(file);objectUrls.current.push(preview);setFiles(d=>({...d,[appId]:{...d[appId],[keys[i]]:{...result,preview}}}))}}catch(e){setError((e as Error).message)}finally{setUploading(false)}
  }
  function removeFile(key:string){const next={...pictures};if(next[key])URL.revokeObjectURL(next[key].preview);delete next[key];setFiles(d=>({...d,[selected]:next}))}
  function uploadArea(label:string,keys:string[],minimum:number){const used=keys.filter(k=>pictures[k]);const available=keys.filter(k=>!pictures[k]);return <Field key={keys.join()}><div className="field-heading"><FieldLabel>{label}</FieldLabel><span className="quiet">{used.length} / {keys.length}{minimum===0?' · 可选':''}</span></div><div className="uploads">{used.map((key,i)=><div className="upload-thumb" key={key}><img src={pictures[key].preview} alt={pictures[key].name}/><span>{i+1}</span><Button size="icon-xs" variant="secondary" aria-label={`移除图片 ${i+1}`} onClick={()=>removeFile(key)}><X/></Button></div>)}{available.length>0&&<label className="upload-trigger"><ImagePlus/><span>{uploading?'上传中…':'添加图片'}</span><input aria-label={label} type="file" accept="image/png,image/jpeg,image/webp" multiple={available.length>1} disabled={uploading} onChange={e=>{void addFiles(e.target.files,available);e.target.value=''}}/></label>}</div><FieldDescription>{minimum>0?`至少 ${minimum} 张。`: '不上传也可以运行。'}支持 PNG、JPEG、WebP，单张最多 20 MB。</FieldDescription></Field>}
  function control(f:Control){const value=values[f.key]??f.default;if(f.kind==='image')return uploadArea(f.label,[f.key],f.default?0:1);if(f.kind==='bool')return <Field key={f.key} orientation="horizontal"><FieldLabel htmlFor={f.key}>{f.label}</FieldLabel><Switch id={f.key} checked={Boolean(value)} onCheckedChange={v=>change(f.key,v)}/></Field>;return <Field key={f.key}><FieldLabel htmlFor={f.key}>{f.label}</FieldLabel>{f.kind==='text'?<Textarea id={f.key} value={String(value??'')} onChange={e=>change(f.key,e.target.value)} placeholder="例如：一只橘猫坐在窗边，午后暖光，胶片摄影…" rows={4} maxLength={12000}/>:f.kind==='select'?<NativeSelect id={f.key} value={String(value)} onChange={e=>change(f.key,f.options?.find(v=>String(v)===e.target.value)??e.target.value)} className="w-full">{f.options?.map(v=><NativeSelectOption key={String(v)} value={String(v)}>{String(v)}</NativeSelectOption>)}</NativeSelect>:<Input id={f.key} type="number" inputMode={f.kind==='int'?'numeric':'decimal'} value={String(value??'')} min={f.min} max={f.max} step={f.kind==='int'?1:f.step||'any'} onChange={e=>change(f.key,e.target.value===''?'':Number(e.target.value))}/>}{f.random_seed&&<FieldDescription>-1 每次随机；固定数值可复现。</FieldDescription>}</Field>}
  async function run(){if(!current)return;setSubmitting(true);setError('');try{const job=await api<Job>('/jobs',{method:'POST',body:JSON.stringify({app:current.id,revision:current.revision,values,images:Object.fromEntries(Object.entries(pictures).map(([k,v])=>[k,v.id]))})});setJobs(j=>[job,...j]);setShown(job.id)}catch(e){setError((e as Error).message)}finally{setSubmitting(false)}}
  const hidden=new Set(current?.imageGroups.flatMap(g=>[...g.fields,g.count,g.toggle].filter(Boolean))||[])
  const visible=current?.fields.filter(f=>!hidden.has(f.key))||[]
  if(!auth?.authenticated)return <main className="login-page"><section className="login-card"><div className="brand-mark"><Aperture/></div><p className="eyebrow">COMFY POCKET</p><h1>让创作，轻一点。</h1><p className="quiet">连接你的电脑，随时运行 ComfyUI 应用。</p>{error&&<Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}{auth?<form onSubmit={e=>{e.preventDefault();setLoading(true);void api('/login',{method:'POST',body:JSON.stringify({code})}).then(()=>setAuth({...auth,authenticated:true})).catch(e=>setError(e.message)).finally(()=>setLoading(false))}}><FieldGroup><Field><FieldLabel htmlFor="access">设备访问码</FieldLabel><Input id="access" type="password" autoComplete="current-password" value={code} onChange={e=>setCode(e.target.value)} required/><FieldDescription>在电脑端打开本页面，点击「手机访问」查看。只需输入一次。</FieldDescription></Field><Button size="lg" type="submit" disabled={loading}>{loading?<Loader2 className="animate-spin"/>:<ShieldCheck/>}连接工作室</Button></FieldGroup></form>:<Button variant="outline" onClick={()=>location.reload()}>{error?'重新连接':'正在连接…'}</Button>}</section></main>
  return <div className="shell"><aside className="sidebar"><a className="brand" href="/" aria-label="Comfy Pocket 首页"><div className="brand-mark"><Aperture/></div><div>Comfy <strong>Pocket</strong><small>你的随身创作台</small></div></a><div className="sidebar-heading"><span>我的应用</span><Badge variant="secondary">{apps.length}</Badge></div><nav aria-label="应用列表">{apps.map(a=><button key={a.id} className={'app-link '+(a.id===selected&&view==='create'?'selected':'')} onClick={()=>choose(a.id)}>{a.purpose==='video'?<Film/>:<Images/>}<span><strong>{a.name}</strong><small>{a.model||a.title}</small></span>{a.id===selected&&view==='create'&&<span className="selected-dot"/>}</button>)}</nav><div className="sidebar-bottom"><Separator/><Button variant={view==='history'?'secondary':'ghost'} onClick={()=>setView('history')}><Clock3 data-icon="inline-start"/>运行记录{activeCount>0&&<Badge>{activeCount}</Badge>}</Button><Button variant="ghost" onClick={()=>void sync(true)} disabled={loading}><RefreshCw data-icon="inline-start" className={loading?'animate-spin':''}/>同步官方应用</Button>{auth.local&&<Button variant="ghost" onClick={()=>{setPhoneOpen(!phoneOpen);if(!pairCode)void api<{code:string;urls:string[]}>('/access-code').then(d=>{setPairCode(d.code);setAccessUrls(d.urls)}).catch(e=>setError(e.message))}}><Smartphone data-icon="inline-start"/>手机访问</Button>}<div className="connection"><span/>{runtime?.online?'本机 ComfyUI · 已连接':'轻量服务在线 · ComfyUI 未就绪'}</div></div></aside><main className="workspace"><header className="topbar"><span className="desktop-crumb">工作室 <span>/</span> {view==='history'?'运行记录':current?.title||'应用'}</span><span className="mobile-brand"><Aperture/>Comfy Pocket</span><div className="top-actions"><Button variant="ghost" size="icon" aria-label="同步应用" onClick={()=>void sync(true)} disabled={loading}><RefreshCw className={loading?'animate-spin':''}/></Button><Button variant={view==='history'?'secondary':'ghost'} size="icon" aria-label="运行记录" onClick={()=>setView(v=>v==='history'?'create':'history')}><Clock3/></Button><Badge variant="outline">{activeCount?`${activeCount} 个任务`:runtime?.online?'就绪':'后端未就绪'}</Badge></div></header><div className="page-content"><section className="runtime-panel" aria-label="ComfyUI 进程控制"><div><strong><Power/>ComfyUI <Badge variant={runtime?.online?'secondary':'outline'}>{runtimeBusy?'操作中…':({running:'运行中',starting:'启动中',stopped:'已停止',error:'启动失败'}[runtime?.state||'']||'检查中')}</Badge></strong><p>{runtime?.error||(runtime?.online?'电脑后端已连接，可以开始生成。':runtime?.state==='starting'?'正在加载环境和节点，首次启动可能需要一分钟。':'点击启动即可远程开启电脑上的生成服务。')}</p></div><div className="runtime-actions"><Button size="sm" disabled={runtimeBusy||!runtime?.manageable||runtime.online||runtime.state==='starting'} onClick={()=>void controlRuntime('start')}>启动</Button><Button size="sm" variant="outline" disabled={runtimeBusy||!runtime?.manageable||runtime.state==='stopped'||runtime.state==='error'||activeCount>0} onClick={()=>void controlRuntime('stop')}>停止</Button><Button size="sm" variant="outline" disabled={runtimeBusy||!runtime?.manageable||runtime.state==='starting'||activeCount>0} onClick={()=>void controlRuntime('restart')}>重启</Button></div></section>{phoneOpen&&<Alert><Smartphone/><AlertDescription><strong>手机访问</strong><p>手机开启 Tailscale 或连接同一局域网，访问：{accessUrls.join(" 或 ")}</p><p>设备访问码：<code className="pair-code">{pairCode||'加载中…'}</code></p></AlertDescription></Alert>}{error&&<Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}{unsupported.length>0&&<details className="compatibility"><summary>{unsupported.length} 个应用需要检查</summary>{unsupported.map(a=><p key={a.name}>{a.name}：{a.error}</p>)}</details>}{view==='history'?<><div className="page-heading"><p className="eyebrow">YOUR CREATIONS</p><h1>运行记录<span> / {jobs.length}</span></h1><p>这里保留通过轻量页面提交的任务。</p></div><div className="history-list">{jobs.map(j=><button key={j.id} className="history-row" onClick={()=>{choose(j.app);setShown(j.id)}}><div className="history-icon">{j.status==='success'?<Check/>:<Clock3/>}</div><div><strong>{j.title}</strong><small>{new Date(j.created*1000).toLocaleString('zh-CN')}</small></div><Badge variant={j.status==='error'?'destructive':'secondary'}>{statusLabel[j.status]}</Badge><ArrowUpRight/></button>)}{!jobs.length&&<Empty><EmptyHeader><EmptyTitle>还没有作品</EmptyTitle><EmptyDescription>选择一个应用，开始第一次生成。</EmptyDescription></EmptyHeader></Empty>}</div></>:current?<><div className="mobile-picker"><NativeSelect aria-label="选择应用" value={selected} onChange={e=>choose(e.target.value)} className="w-full">{apps.map(a=><NativeSelectOption key={a.id} value={a.id}>{a.title}</NativeSelectOption>)}</NativeSelect></div><div className="page-heading"><p className="eyebrow">{current.model||'COMFYUI APP'}</p><h1>{current.name}<span> / {current.purpose==='video'?'MOTION':'IMAGE'}</span></h1><p>{current.description||'来自官方应用，参数与工作流保持同步。'}</p></div><div className="creation-layout"><section key={current.id+current.revision} className="controls-panel" aria-label="应用参数"><div className="parameter-storage"><p role="status" className={saveFailed?'storage-error':''}>{saveStatus}</p><Button size="sm" variant="ghost" disabled={submitting||loading} onClick={()=>savePreferences(current.id,undefined,true)}>恢复默认参数</Button></div><FieldGroup>{current.imageGroups.map(g=>uploadArea(g.label,g.fields,g.min))}{visible.filter(f=>!f.advanced).map(control)}</FieldGroup>{visible.some(f=>f.advanced)&&<details className="advanced"><summary>更多参数<ChevronDown/></summary><FieldGroup>{visible.filter(f=>f.advanced).map(control)}</FieldGroup></details>}<div className="run-bar"><span>{uploading?'图片上传中':activeCount?`${activeCount} 个任务处理中`:'准备好，就开始吧'}</span><Button size="lg" onClick={()=>void run()} disabled={submitting||uploading||loading||!runtime?.online}>{submitting?<Loader2 className="animate-spin"/>:<Play data-icon="inline-start"/>}{submitting?'提交中':'开始生成'}</Button></div></section><section className="result-panel" aria-label="作品预览"><div className="result-heading"><span>作品预览</span>{latest&&<Badge variant="secondary">{statusLabel[latest.status]}</Badge>}</div><Preview job={latest} onError={setError} realtime={realtime}/>{latest?.texts?.map(t=><details key={t.node} className="text-result" open><summary>{t.label}</summary><Textarea aria-label={t.label} value={t.text} readOnly rows={8}/><p>这是该次任务实际使用的文本；可选中复制。</p></details>)}{latest?.status==='success'&&<p className="result-note">已保存在电脑的 ComfyUI 输出目录</p>}</section></div></>:<Empty><EmptyHeader><EmptyTitle>{loading?'正在同步应用':'还没有可用应用'}</EmptyTitle><EmptyDescription>{runtime?.online?'在 ComfyUI 官方界面构建应用并保存，然后点击同步。':'先点击上方启动 ComfyUI，应用列表会自动加载。'}</EmptyDescription></EmptyHeader><Button onClick={()=>void sync(true)}>重新同步</Button></Empty>}</div><footer className="page-footer"><span>COMFY POCKET</span><span>轻量界面 · 本机执行</span></footer></main></div>
}
export default App
