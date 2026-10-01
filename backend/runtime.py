"""Control only the locally configured ComfyUI command, never arbitrary commands."""
import asyncio
import os
import pathlib
import subprocess
import time
import psutil
from aiohttp import ClientTimeout


def canonical(path,cwd):
    path=path.replace('\\','/')
    if not (len(path)>1 and path[1]==':') and not path.startswith('/'):
        path=cwd.replace('\\','/').rstrip('/')+'/'+path
    normalized=os.path.normpath(path).replace('\\','/')
    return normalized.casefold() if len(normalized)>1 and normalized[1]==':' else os.path.normcase(normalized)


def is_managed_command(cmd,cwd,config):
    if not cmd or len(cmd)!=len(config['args'])+1:return False
    if canonical(cmd[0],cwd)!=canonical(config['executable'],config['cwd']):return False
    for actual,expected in zip(cmd[1:],config['args']):
        if expected.lower().endswith('.py'):
            if canonical(actual,cwd)!=canonical(expected,config['cwd']):return False
        elif actual!=expected:return False
    return True


class Runtime:
    def __init__(self,config,state,client):
        self.config=config;self.state=pathlib.Path(state);self.client=client
        self.lock=asyncio.Lock();self.error='';self.started_at=0;self.child=None
        self.cached=None;self.checked=0

    def processes(self):
        if not self.config.get('runtime'):return []
        found=[]
        for p in psutil.process_iter(['pid','cmdline','cwd']):
            try:
                if is_managed_command(p.info['cmdline'],p.info['cwd'] or '',self.config['runtime']):found.append(p)
            except (psutil.Error,OSError):continue
        return found

    async def health(self):
        try:
            async with self.client.get(self.config['comfy_url']+'/system_stats',timeout=ClientTimeout(total=2)) as r:
                if r.status!=200:return False
                d=await r.json();return isinstance(d,dict) and 'system' in d and 'devices' in d
        except Exception:return False

    async def status(self,force=False):
        if not force and self.cached and time.monotonic()-self.checked<2:return self.cached
        online,processes=await asyncio.gather(self.health(),asyncio.to_thread(self.processes))
        alive=bool(processes)
        if self.child and self.child.poll() is not None and not alive:
            self.error=f'ComfyUI 启动进程已退出（代码 {self.child.returncode}），请查看电脑 state/comfyui.log';self.child=None
        state='running' if online else ('starting' if alive else ('error' if self.error else 'stopped'))
        self.cached={'state':state,'online':online,'manageable':bool(self.config.get('runtime')) and (alive or not online),'error':self.error if not online else '', 'pid':processes[-1].pid if processes else None}
        if alive and not online and self.started_at and time.time()-self.started_at>300:
            self.cached['error']='启动超过 5 分钟，请查看电脑 state/comfyui.log；不要重复启动'
        self.checked=time.monotonic();return self.cached

    async def idle(self):
        if not await self.health():return
        async with self.client.get(self.config['comfy_url']+'/queue',timeout=ClientTimeout(total=5)) as r:
            if r.status!=200:raise ValueError('无法确认任务队列，暂不能停止 ComfyUI')
            q=await r.json()
        if q.get('queue_running') or q.get('queue_pending'):raise ValueError('ComfyUI 还有运行或排队任务，请完成或取消后再停止/重启')

    def launch(self):
        r=self.config['runtime']
        if not pathlib.Path(r['executable']).is_file() or not pathlib.Path(r['cwd']).is_dir():raise ValueError('ComfyUI 启动路径不存在，请检查电脑 config.json')
        with (self.state/'comfyui.log').open('ab') as log:
            self.child=subprocess.Popen([r['executable'],*r['args']],cwd=r['cwd'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,env={**os.environ,'PYTHONUNBUFFERED':'1'})
        self.started_at=time.time();self.error=''

    def terminate(self,processes):
        # Recheck command identity immediately before termination, including reused PIDs.
        targets=[]
        for p in processes:
            try:
                if not is_managed_command(p.cmdline(),p.cwd(),self.config['runtime']):continue
                targets.append(p)
            except psutil.Error:continue
        for p in targets:
            try:p.terminate()
            except psutil.NoSuchProcess:pass
        _,alive=psutil.wait_procs(targets,timeout=10)
        if alive:raise ValueError('ComfyUI 尚未退出，请稍后重试')
        if self.child:self.child.poll()
        self.child=None;self.started_at=0;self.error=''

    async def action(self,action):
        if not self.config.get('runtime'):raise ValueError('未配置本机进程控制，请在电脑配置 ComfyUI 目录和 Python 路径')
        if action not in ('start','stop','restart'):raise ValueError('不支持的进程操作')
        async with self.lock:
            status=await self.status(True)
            processes=await asyncio.to_thread(self.processes)
            if action=='start' and (status['online'] or processes):return status
            if action in ('stop','restart'):
                if status['online'] and not processes:raise ValueError('正在运行的 ComfyUI 与配置的启动命令不一致，不能控制此进程')
                await self.idle()
                await asyncio.to_thread(self.terminate,processes)
            if action in ('start','restart'):await asyncio.to_thread(self.launch)
            return await self.status(True)
