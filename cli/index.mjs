#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawn,spawnSync } from 'node:child_process';
import { createInterface } from 'node:readline/promises';
import { parseArgs,makeConfig } from './options.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const win=process.platform==='win32';
function run(command,args,opts={}){const r=spawnSync(command,args,{stdio:'inherit',windowsHide:true,...opts});if(r.error||r.status!==0)throw Error(`${command} failed. ${r.error?.message||'See output above.'}`);}
function openBrowser(url){const command=win?'rundll32':process.platform==='darwin'?'open':'xdg-open';const args=win?['url.dll,FileProtocolHandler',url]:[url];const p=spawn(command,args,{stdio:'ignore',detached:true,windowsHide:true});p.on('error',()=>console.log(`Open ${url} in your browser.`));p.unref();}
async function main(){
  const o=parseArgs(process.argv.slice(2));
  if(o.help){console.log(`Comfy Pocket\n\nUsage: comfy-pocket [options]\n  --comfy-url URL   Existing backend (default http://127.0.0.1:8188)\n  --comfy-dir DIR   Local ComfyUI directory; enables process controls\n  --python FILE    Python 3.10+ (ComfyUI Python when using --comfy-dir)\n  --home DIR       Persistent config/data directory (default ~/.comfy-pocket)\n  --host IPv4      Also listen on this LAN/Tailscale address; repeatable\n  --port PORT      Web port (default 8189)\n  --no-open        Do not open a browser\n  --setup-only     Install dependencies and create configuration, then exit\n  --help           Show help\n\n中文：首次启动创建独立 Python 环境，不修改 ComfyUI。配置保存后自动复用。\nKeep this terminal open while using the service. Ctrl+C stops Pocket, not ComfyUI.`);return;}
  const home=path.resolve(o.home||process.env.COMFY_POCKET_HOME||path.join(os.homedir(),'.comfy-pocket'));
  fs.mkdirSync(home,{recursive:true,mode:0o700});
  const configFile=path.join(home,'config.json');
  if(!fs.existsSync(configFile)&&!o.comfyDir&&!o.comfyUrl&&process.stdin.isTTY){
    const rl=createInterface({input:process.stdin,output:process.stdout});
    try{
      const dir=(await rl.question('ComfyUI folder / ComfyUI 目录（留空仅连接现有后端）: ')).trim().replace(/^"|"$/g,'');
      if(dir)o.comfyDir=dir;
      const url=(await rl.question('ComfyUI URL [http://127.0.0.1:8188]: ')).trim();o.comfyUrl=url||'http://127.0.0.1:8188';
    }finally{rl.close();}
  }
  const existing=fs.existsSync(configFile)?JSON.parse(fs.readFileSync(configFile,'utf8').replace(/^\uFEFF/,'')):null;
  const venv=path.join(home,'.venv');const servicePython=path.join(venv,win?'Scripts/python.exe':'bin/python');
  let python=o.python||existing?.runtime?.executable||existing?.python;
  if(!fs.existsSync(servicePython)||(!existing&&o.comfyDir)){
    const candidates=[python,...(o.comfyDir?['.venv','venv','env'].map(n=>path.join(o.comfyDir,n,win?'Scripts/python.exe':'bin/python')):[]),...(o.comfyDir?[path.join(o.comfyDir,'../python_embeded/python.exe')]:[]),win?'python':'python3'].filter(Boolean);
    python=undefined;
    for(const candidate of candidates){const r=spawnSync(candidate,['-c','import sys; assert sys.version_info >= (3,10); print(sys.executable)'],{encoding:'utf8',windowsHide:true});if(r.status===0){python=r.stdout.trim();break;}}
    if(!python)throw Error('Python 3.10+ not found. Install Python or pass --python PATH. / 未找到 Python，请指定路径。');
  }
  if(!fs.existsSync(servicePython)){console.log('Creating isolated Python environment / 创建独立 Python 环境…');run(python,['-m','venv',venv]);}
  const requirements=path.join(root,'requirements.txt');const desired=fs.readFileSync(requirements,'utf8');const stamp=path.join(venv,'pocket-requirements.txt');
  if(!fs.existsSync(stamp)||fs.readFileSync(stamp,'utf8')!==desired){
    console.log('Installing Pocket dependencies / 安装轻量服务依赖…');run(servicePython,['-m','pip','install','--disable-pip-version-check','-r',requirements]);fs.writeFileSync(stamp,desired);
  }
  let config=existing;
  if(!config){
    if(o.comfyDir&&!fs.existsSync(path.join(o.comfyDir,'main.py')))throw Error('--comfy-dir must contain main.py / 请选择包含 main.py 的目录');
    config=makeConfig({...o,python});config.python=servicePython;fs.writeFileSync(configFile,JSON.stringify(config,null,2),{mode:0o600});
  }else if(o.port!==undefined||o.hosts.length||o.comfyDir||o.comfyUrl)console.log('Using saved config; edit '+configFile+' to change server settings. / 已复用现有配置。');
  console.log('Config / 配置: '+configFile);
  if(o.setupOnly)return;
  if(!fs.existsSync(path.join(root,'web/dist/index.html')))throw Error('Frontend build missing. Use a release package, or run npm run build.');
  const url=`http://127.0.0.1:${config.port}`;
  try{const r=await fetch(url+'/api/session',{signal:AbortSignal.timeout(1000)});if(r.ok&&(await r.json()).product==='comfy-pocket'){console.log('Already running / 已在运行: '+url);if(o.open)openBrowser(url);return;}}catch{}
  console.log('Starting / 启动: '+url+'\nCtrl+C stops Pocket only. / 保持终端打开，Ctrl+C 仅停止轻量服务。');
  const child=spawn(servicePython,['-m','backend.server'],{cwd:root,env:{...process.env,COMFY_POCKET_HOME:home},stdio:'inherit',windowsHide:true});
  let stopping=false;
  const stop=()=>{
    if(stopping)return;stopping=true;
    // Windows venv Python may create a redirector child. Stop only this owned server tree.
    const cleanup=`import sys,psutil,os
try:
 p=psutil.Process(int(sys.argv[1]))
 if p.cmdline()[-2:]==['-m','backend.server'] and os.path.normcase(p.cwd())==os.path.normcase(sys.argv[2]):
  for q in list(reversed(p.children(recursive=True)))+[p]:
   try:
    if q.cmdline()[-2:]==['-m','backend.server']:q.terminate()
   except psutil.Error:pass
except psutil.Error:pass
`;
    spawnSync(servicePython,['-c',cleanup,String(child.pid),root],{windowsHide:true,stdio:'ignore'});
  };process.on('SIGINT',stop);process.on('SIGTERM',stop);
  child.on('error',e=>{console.error(e.message);process.exitCode=1;});
  let opened=false;const timer=setInterval(async()=>{try{const r=await fetch(url+'/api/session',{signal:AbortSignal.timeout(1000)});if(r.ok&&(await r.json()).product==='comfy-pocket'&&!opened){opened=true;clearInterval(timer);console.log('Ready / 已就绪: '+url);if(o.open)openBrowser(url);}}catch{}},500);
  child.on('exit',code=>{clearInterval(timer);process.exitCode=code||0;});
}
main().catch(e=>{console.error('\n'+e.message);process.exitCode=1;});
