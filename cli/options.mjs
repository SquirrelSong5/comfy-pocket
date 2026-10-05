import path from 'node:path';
import { isIP } from 'node:net';

export function parseArgs(argv) {
  const o={hosts:[],open:true};
  const names={'--home':'home','--python':'python','--comfy-dir':'comfyDir','--comfy-url':'comfyUrl','--port':'port'};
  for(let i=0;i<argv.length;i++){
    const a=argv[i];
    if((a==='start'||a==='stop')&&i===0)o.command=a;
    else if(a==='--no-open')o.open=false;
    else if(a==='--setup-only')o.setupOnly=true;
    else if(a==='--help'||a==='-h')o.help=true;
    else if(a==='--host'){
      const v=argv[++i];if(!v||isIP(v)!==4||v==='0.0.0.0')throw Error('--host requires a specific IPv4 address (not 0.0.0.0)');o.hosts.push(v);
    }else if(names[a]){
      const v=argv[++i];if(!v||v.startsWith('--'))throw Error(`Missing value for ${a}`);o[names[a]]=v;
    }else throw Error(`Unknown option: ${a}`);
  }
  if(o.port!==undefined){o.port=Number(o.port);if(!Number.isInteger(o.port)||o.port<1024||o.port>65535)throw Error('--port must be an integer from 1024 to 65535');}
  if(o.comfyUrl){const u=new URL(o.comfyUrl);if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.search||u.hash||u.pathname!=='/')throw Error('--comfy-url must be an HTTP(S) origin without credentials');o.comfyUrl=u.origin;}
  if(o.command==='stop'&&(o.setupOnly||o.python||o.comfyDir||o.comfyUrl||o.port!==undefined||o.hosts.length))throw Error('stop only accepts --home, --no-open, and --help');
  return o;
}

export function makeConfig(o) {
  const hosts=[...new Set(['127.0.0.1',...(o.hosts||[])])];
  const networks=['127.0.0.0/8',...hosts.filter(h=>h!=='127.0.0.1').map(h=>(h.split('.')[0]==='100'&&Number(h.split('.')[1])>=64&&Number(h.split('.')[1])<=127)?'100.64.0.0/10':h.split('.').slice(0,3).join('.')+'.0/24')];
  const config={comfy_url:o.comfyUrl||'http://127.0.0.1:8188',port:o.port||8189,bind:hosts,hosts:[...hosts,'localhost'],networks:[...new Set(networks)],runtime:null};
  if(o.comfyDir){
    const url=new URL(config.comfy_url);
    if(!['127.0.0.1','localhost'].includes(url.hostname))throw Error('Local process control requires a loopback --comfy-url');
    if(!o.python)throw Error('Local process control requires a ComfyUI Python executable');
    const cwd=path.resolve(o.comfyDir);
    config.runtime={cwd,executable:o.python,args:['-s',path.join(cwd,'main.py'),'--disable-auto-launch','--listen','127.0.0.1','--port',url.port||'80']};
  }
  return config;
}
