"""Small, task-scoped reducer for official ComfyUI execution messages."""
import math

def apply_event(jobs,event):
    data=event.get('data',{})
    if not isinstance(data,dict):return False
    job=jobs.get(data.get('prompt_id'))
    if not job or job.get('status') not in ('queued','running'):return False
    kind=event.get('type');node=data.get('node')
    if kind=='execution_start':
        job['status']='running';job['phase']='executing';job.pop('progress',None)
    elif kind=='executing':
        job['status']='running'
        if node is None:
            job['phase']='finishing';job.pop('progress',None)
        else:
            node=str(node);job['phase']='executing'
            job['progress']={'node':node,'label':job.get('node_labels',{}).get(node,node),'value':0,'max':0}
    elif kind=='progress':
        value=data.get('value');maximum=data.get('max')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (value,maximum)) or maximum<=0:return False
        node=str(node) if node is not None else job.get('progress',{}).get('node')
        if node is None:return False
        job['status']='running';job['phase']='executing'
        job['progress']={'node':node,'label':job.get('node_labels',{}).get(node,node),'value':max(0,min(value,maximum)),'max':maximum}
    elif kind in ('execution_success','execution_error','execution_interrupted'):
        job['phase']='finishing';job.pop('progress',None)
    elif kind=='executed':
        return record_text(job,node,data.get('output',{}))
    else:return False
    return True


def record_text(job,node,output):
    if not isinstance(output,dict):return False
    texts=output.get('text',[])
    if isinstance(texts,str):texts=[texts]
    if not isinstance(texts,(list,tuple)):return False
    text='\n'.join(t for t in texts if isinstance(t,str))[:30000]
    if not text:return False
    node=str(node);items=job.setdefault('texts',[])
    items[:]=[t for t in items if t['node']!=node]
    items.append({'node':node,'label':job.get('node_labels',{}).get(node,'文本输出'),'text':text})
    return True
