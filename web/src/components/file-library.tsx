import { useEffect, useRef, useState } from 'react'
import { ArrowDownToLine, File, Film, Music, Play, RefreshCw, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import './file-library.css'

interface Entry { name:string; path:string; kind:string; size:number; modified:number }
interface Listing { path:string; entries:Entry[]; total:number; next_offset:number|null }
function VideoThumbnail({src}:{src:string}) {
  const [failed,setFailed]=useState(false)
  useEffect(()=>setFailed(false),[src])
  return <>{failed?<Film/>:<img src={src} alt="" loading="lazy" decoding="async" onError={()=>setFailed(true)}/>}<span className="file-video-badge"><Play/>视频</span></>
}

function size(bytes:number) { return bytes < 1048576 ? `${(bytes/1024).toFixed(0)} KB` : `${(bytes/1048576).toFixed(1)} MB` }

export function FileLibrary() {
  const [root,setRoot]=useState('output'),[kind,setKind]=useState('all'),[search,setSearch]=useState('')
  const [data,setData]=useState<Listing>({path:'',entries:[],total:0,next_offset:null}),[busy,setBusy]=useState(true),[error,setError]=useState('')
  const [revision,setRevision]=useState(0),[selected,setSelected]=useState<Entry|null>(null)
  const request=useRef(0),close=useRef<HTMLButtonElement>(null),opener=useRef<HTMLElement|null>(null)
  function url(entry:Entry,extra:Record<string,string>={}) { return '/api/files/media?'+new URLSearchParams({root,path:entry.path,...extra}) }
  async function load(offset=0) {
    const id=++request.current;setBusy(true);setError('')
    try {
      const result=await api<Listing>('/files?'+new URLSearchParams({root,kind,search,offset:String(offset)}))
      if(id===request.current)setData(old=>({...result,entries:offset?[...old.entries,...result.entries]:result.entries}))
    }catch(e){if(id===request.current)setError((e as Error).message)}finally{if(id===request.current)setBusy(false)}
  }
  useEffect(()=>{setBusy(true);setData({path:'',entries:[],total:0,next_offset:null});const timer=setTimeout(()=>void load(),200);return()=>{clearTimeout(timer);request.current++}},[root,kind,search,revision])
  useEffect(()=>{
    if(!selected)return
    opener.current=document.activeElement as HTMLElement;close.current?.focus()
    const overflow=document.body.style.overflow;document.body.style.overflow='hidden'
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')setSelected(null)}
    window.addEventListener('keydown',escape)
    return()=>{document.body.style.overflow=overflow;window.removeEventListener('keydown',escape);opener.current?.focus()}
  },[selected])
  return <section className="file-library" aria-label="电脑文件">
    <div className="page-heading"><p className="eyebrow">COMPUTER FILES</p><h1>电脑文件</h1><p>所有子文件夹中的文件集中展示，按类型筛选、预览和下载。</p></div>
    <div className="file-roots" aria-label="选择文件夹">{['output','input'].map(value=><Button key={value} variant={root===value?'secondary':'outline'} onClick={()=>{setRoot(value);setSearch('');setSelected(null)}}>{value==='output'?'output · 生成作品':'input · 输入素材'}</Button>)}</div>
    <div className="file-toolbar"><Input aria-label="搜索所有文件" placeholder="搜索文件名或路径…" value={search} onChange={e=>setSearch(e.target.value)}/><Button variant="outline" size="icon" aria-label="刷新文件" disabled={busy} onClick={()=>setRevision(v=>v+1)}><RefreshCw className={busy?'animate-spin':''}/></Button></div>
    <div className="file-type-filters" role="group" aria-label="文件类型">{[['all','全部'],['video','视频'],['image','图片'],['audio','音频'],['file','其他']].map(([value,label])=><Button key={value} size="sm" variant={kind===value?'secondary':'ghost'} aria-pressed={kind===value} onClick={()=>setKind(value)}>{label}</Button>)}</div>
    {error&&<p role="alert" className="file-error">{error}</p>}
    <p className="quiet" role="status">{busy?'正在读取电脑文件…':`${data.total} 项 · 包含所有子文件夹 · 最新优先`}</p>
    <div className="file-grid">{data.entries.map(entry=><article className="file-card" key={entry.path}><button className="file-open" onClick={()=>setSelected(entry)} aria-label={'查看 '+entry.name}><div className="file-art">{entry.kind==='image'?<img src={url(entry,{preview:'1'})} alt="" loading="lazy" decoding="async"/>:entry.kind==='video'?<VideoThumbnail src={url(entry,{preview:'1'})}/>:entry.kind==='audio'?<Music/>:<File/>}</div><strong>{entry.name}</strong><small>{size(entry.size)} · {new Date(entry.modified*1000).toLocaleDateString('zh-CN')}</small><small className="file-source-path" title={entry.path}>{entry.path.includes('/')?entry.path.slice(0,entry.path.lastIndexOf('/')):'根目录'}</small></button>{entry.kind!=='folder'&&<a className="file-download" href={url(entry,{download:'1'})} download aria-label={'下载 '+entry.name}><ArrowDownToLine/></a>}</article>)}</div>
    {!busy&&!error&&!data.total&&<p className="file-empty">{search?'没有匹配的文件。':'所有子文件夹中都没有此类型的文件。'}</p>}
    {data.next_offset!==null&&<Button variant="outline" disabled={busy} onClick={()=>void load(data.next_offset!)}>加载更多</Button>}
    {selected&&<div className="file-modal" role="dialog" aria-modal="true" aria-label={'预览 '+selected.name} onKeyDown={e=>{if(e.key==='Tab'){const elements=e.currentTarget.querySelectorAll<HTMLElement>('button,a,[controls]');const first=elements[0],last=elements[elements.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}}}}><header><strong>{selected.name}</strong><a href={url(selected,{download:'1'})} download aria-label="下载当前文件"><ArrowDownToLine/></a><Button ref={close} size="icon" variant="ghost" aria-label="关闭预览" onClick={()=>setSelected(null)}><X/></Button></header><div className="file-modal-body">{selected.kind==='image'?<img src={url(selected)} alt={selected.name}/>:selected.kind==='video'?<video src={url(selected)} controls playsInline preload="metadata"/>:selected.kind==='audio'?<audio src={url(selected)} controls preload="metadata"/>:<p>此类型请下载后打开。</p>}</div></div>}
  </section>
}
