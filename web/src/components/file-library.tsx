import { useEffect, useRef, useState } from 'react'
import { ArrowDownToLine, ArrowLeft, File, Film, Folder, Music, RefreshCw, X } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import './file-library.css'

interface Entry { name:string; path:string; kind:string; size:number; modified:number }
interface Listing { path:string; entries:Entry[]; total:number; next_offset:number|null }
function size(bytes:number) { return bytes < 1048576 ? `${(bytes/1024).toFixed(0)} KB` : `${(bytes/1048576).toFixed(1)} MB` }

export function FileLibrary() {
  const [root,setRoot]=useState('output'),[path,setPath]=useState(''),[kind,setKind]=useState('all'),[search,setSearch]=useState('')
  const [data,setData]=useState<Listing>({path:'',entries:[],total:0,next_offset:null}),[busy,setBusy]=useState(true),[error,setError]=useState('')
  const [revision,setRevision]=useState(0),[selected,setSelected]=useState<Entry|null>(null)
  const request=useRef(0),close=useRef<HTMLButtonElement>(null),opener=useRef<HTMLElement|null>(null)
  function url(entry:Entry,extra:Record<string,string>={}) { return '/api/files/media?'+new URLSearchParams({root,path:entry.path,...extra}) }
  async function load(offset=0) {
    const id=++request.current;setBusy(true);setError('')
    try {
      const result=await api<Listing>('/files?'+new URLSearchParams({root,path,kind,search,offset:String(offset)}))
      if(id===request.current)setData(old=>({...result,entries:offset?[...old.entries,...result.entries]:result.entries}))
    }catch(e){if(id===request.current)setError((e as Error).message)}finally{if(id===request.current)setBusy(false)}
  }
  useEffect(()=>{setBusy(true);setData({path,entries:[],total:0,next_offset:null});const timer=setTimeout(()=>void load(),200);return()=>{clearTimeout(timer);request.current++}},[root,path,kind,search,revision])
  useEffect(()=>{
    if(!selected)return
    opener.current=document.activeElement as HTMLElement;close.current?.focus()
    const overflow=document.body.style.overflow;document.body.style.overflow='hidden'
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')setSelected(null)}
    window.addEventListener('keydown',escape)
    return()=>{document.body.style.overflow=overflow;window.removeEventListener('keydown',escape);opener.current?.focus()}
  },[selected])
  return <section className="file-library" aria-label="电脑文件">
    <div className="page-heading"><p className="eyebrow">COMPUTER FILES</p><h1>电脑文件</h1><p>查看 input 素材和 output 作品，支持子文件夹、预览和下载。</p></div>
    <div className="file-roots" aria-label="选择文件夹">{['output','input'].map(value=><Button key={value} variant={root===value?'secondary':'outline'} onClick={()=>{setRoot(value);setPath('');setSearch('');setSelected(null)}}>{value==='output'?'output · 生成作品':'input · 输入素材'}</Button>)}</div>
    <div className="file-toolbar"><Input aria-label="搜索当前文件夹" placeholder="搜索当前文件夹…" value={search} onChange={e=>setSearch(e.target.value)}/><NativeSelect aria-label="文件类型" value={kind} onChange={e=>setKind(e.target.value)}>{[['all','全部类型'],['image','图片'],['video','视频'],['audio','音频'],['file','其他文件']].map(([value,label])=><NativeSelectOption key={value} value={value}>{label}</NativeSelectOption>)}</NativeSelect><Button variant="outline" size="icon" aria-label="刷新文件" disabled={busy} onClick={()=>setRevision(v=>v+1)}><RefreshCw className={busy?'animate-spin':''}/></Button></div>
    <nav className="file-breadcrumbs" aria-label="文件路径"><Button size="sm" variant="ghost" disabled={!path} onClick={()=>{setPath(path.split('/').slice(0,-1).join('/'));setSearch('')}}><ArrowLeft/>上一级</Button><button onClick={()=>{setPath('');setSearch('')}}>{root}</button>{path.split('/').filter(Boolean).map((part,index,parts)=><span key={index}> / <button onClick={()=>{setPath(parts.slice(0,index+1).join('/'));setSearch('')}}>{part}</button></span>)}</nav>
    {error&&<p role="alert" className="file-error">{error}</p>}
    <p className="quiet" role="status">{busy?'正在读取电脑文件…':`${data.total} 项 · 文件夹优先，文件按最新排序`}</p>
    <div className="file-grid">{data.entries.map(entry=><article className="file-card" key={entry.path}><button className="file-open" onClick={()=>entry.kind==='folder'?(setPath(entry.path),setSearch('')):setSelected(entry)} aria-label={(entry.kind==='folder'?'打开文件夹 ':'查看 ')+entry.name}><div className="file-art">{entry.kind==='image'?<img src={url(entry,{preview:'1'})} alt="" loading="lazy" decoding="async"/>:entry.kind==='folder'?<Folder/>:entry.kind==='video'?<Film/>:entry.kind==='audio'?<Music/>:<File/>}</div><strong>{entry.name}</strong><small>{entry.kind==='folder'?'文件夹':size(entry.size)} · {new Date(entry.modified*1000).toLocaleDateString('zh-CN')}</small></button>{entry.kind!=='folder'&&<a className="file-download" href={url(entry,{download:'1'})} download aria-label={'下载 '+entry.name}><ArrowDownToLine/></a>}</article>)}</div>
    {!busy&&!error&&!data.total&&<p className="file-empty">{search?'当前文件夹没有匹配的文件。':'当前文件夹没有此类型的文件。'}</p>}
    {data.next_offset!==null&&<Button variant="outline" disabled={busy} onClick={()=>void load(data.next_offset!)}>加载更多</Button>}
    {selected&&<div className="file-modal" role="dialog" aria-modal="true" aria-label={'预览 '+selected.name} onKeyDown={e=>{if(e.key==='Tab'){const elements=e.currentTarget.querySelectorAll<HTMLElement>('button,a,[controls]');const first=elements[0],last=elements[elements.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}}}}><header><strong>{selected.name}</strong><a href={url(selected,{download:'1'})} download aria-label="下载当前文件"><ArrowDownToLine/></a><Button ref={close} size="icon" variant="ghost" aria-label="关闭预览" onClick={()=>setSelected(null)}><X/></Button></header><div className="file-modal-body">{selected.kind==='image'?<img src={url(selected)} alt={selected.name}/>:selected.kind==='video'?<video src={url(selected)} controls playsInline preload="metadata"/>:selected.kind==='audio'?<audio src={url(selected)} controls preload="metadata"/>:<p>此类型请下载后打开。</p>}</div></div>}
  </section>
}
