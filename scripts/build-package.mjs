import { spawnSync } from 'node:child_process';
import { existsSync,readdirSync,readFileSync,writeFileSync } from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
// npm_execpath lets Windows run npm without shell interpolation.
function npm(args){const r=spawnSync(process.execPath,[process.env.npm_execpath,...args],{cwd:path.join(root,'web'),stdio:'inherit'});if(r.status!==0)process.exit(r.status||1);}
if(!existsSync(path.join(root,'web/node_modules')))npm(['ci']);
npm(['run','build']);
function compress(dir){for(const ent of readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,ent.name);if(ent.isDirectory())compress(p);else if(/\.(html|js|css)$/.test(p))writeFileSync(p+'.gz',gzipSync(readFileSync(p),{level:9}));}}
compress(path.join(root,'web/dist'));
