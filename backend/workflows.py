"""Dynamic adapter for official ComfyUI apps and live node definitions."""
import copy
import hashlib
import math
import pathlib
import secrets

SCALARS = {'STRING':'text','INT':'int','FLOAT':'float','BOOLEAN':'bool','COMBO':'select'}
CONTROL = {'fixed','randomize','increment','decrement'}

def widget_values(node, schema):
    values=node.get('widgets_values',[])
    if not isinstance(values,list):raise ValueError(f"节点 {node['type']} 使用特殊控件格式，暂不支持")
    index=0; result={}; specs={}
    def walk(groups,prefix=''):
        nonlocal index
        for group in ('required','optional'):
            for name,spec in groups.get(group,{}).items():
                kind=spec[0];opts=spec[1] if len(spec)>1 else {};key=prefix+name
                widget=isinstance(kind,list) or (isinstance(kind,str) and (kind in SCALARS or kind=='COMFY_DYNAMICCOMBO_V3'))
                if not widget or opts.get('forceInput'):continue
                if index>=len(values):
                    if 'default' in opts:result[key]=opts['default'];specs[key]=spec
                    continue
                value=values[index];index+=1;result[key]=value;specs[key]=spec
                if kind=='COMFY_DYNAMICCOMBO_V3':
                    option=next((x for x in opts.get('options',[]) if x['key']==value),None)
                    if option is None:raise ValueError(f'不支持的动态选项 {key}')
                    walk(option.get('inputs',{}),key+'.')
                if (name in ('seed','noise_seed') or node['type']=='PrimitiveInt') and index<len(values) and isinstance(values[index],str) and values[index] in CONTROL:index+=1
    walk(schema['input'])
    return result,specs

def compile_app(path, workflow, object_info):
    d=copy.deepcopy(workflow);linear=d.get('extra',{}).get('linearData')
    if not linear or not linear.get('outputs'):raise ValueError('请在官方应用构建器中选择输出并保存')
    nodes={str(n['id']):n for n in d.get('nodes',[])};links={}
    for link in d.get('links',[]):
        if isinstance(link,dict):link=[link['id'],link['origin_id'],link['origin_slot'],link['target_id'],link['target_slot'],link['type']]
        links[link[0]]=link
    def resolve(ident,slot,seen=None):
        seen=set() if seen is None else seen
        if ident in seen:raise ValueError('节点旁路包含循环')
        seen.add(ident);n=nodes[ident]
        if n.get('mode',0)==2:raise ValueError('所选输出依赖已禁用节点')
        if n.get('mode',0)!=4 and n['type']!='Reroute':return [ident,slot]
        typ=n.get('outputs',[{}])[slot].get('type')
        inputs=[i for i in n.get('inputs',[]) if i.get('link') is not None and (i.get('type')==typ or n['type']=='Reroute')]
        if len(inputs)!=1:raise ValueError(f'无法确定旁路节点 {ident} 的输入')
        l=links[inputs[0]['link']];return resolve(str(l[1]),l[2],seen)
    graph={};all_specs={}
    for ident,n in nodes.items():
        if n.get('mode',0) in (2,4) or n['type'] in ('Note','MarkdownNote','Reroute'):continue
        if n['type'] not in object_info:continue
        inputs,specs=widget_values(n,object_info[n['type']]);all_specs[ident]=specs
        for inp in n.get('inputs',[]):
            if inp.get('link') is not None:
                l=links[inp['link']];inputs[inp['name']]=resolve(str(l[1]),l[2])
        graph[ident]={'class_type':n['type'],'inputs':inputs,'_meta':{'title':n.get('title',n['type'])}}
    outputs=[str(x) for x in linear['outputs']];reachable=set()
    def visit(ident):
        if ident in reachable:return
        if ident not in graph:raise ValueError(f'节点 {ident} 缺失或使用暂不支持的子图/前端专用节点')
        reachable.add(ident)
        for v in graph[ident]['inputs'].values():
            if isinstance(v,list) and len(v)==2 and isinstance(v[0],str):visit(v[0])
    for ident in outputs:visit(ident)
    graph={k:v for k,v in graph.items() if k in reachable}
    meta=d.get('extra',{}).get('comfyLite',{});overrides=meta.get('fields',{});fields=[]
    for entry in linear.get('inputs',[]):
        ref,label=entry if isinstance(entry,list) else (entry,'');parts=ref.rsplit(':',2)
        if len(parts)!=3:raise ValueError('无法识别应用参数引用')
        _,ident,name=parts;key=f'{ident}.{name}'
        if ident not in graph:raise ValueError(f'公开参数 {label or key} 不在所选输出的执行路径中')
        spec=all_specs.get(ident,{}).get(name)
        if spec is None:raise ValueError(f'参数 {label or key} 使用暂不支持的控件')
        kind=spec[0];opts=spec[1] if len(spec)>1 else {}
        image=graph[ident]['class_type'] in ('LoadImage','LoadImageOutput') and name=='image'
        typ='image' if image else ('select' if isinstance(kind,list) or kind=='COMFY_DYNAMICCOMBO_V3' else SCALARS[kind])
        default=graph[ident]['inputs'].get(name)
        if isinstance(default,list):raise ValueError(f'参数 {label or key} 已连接，请公开源节点控件')
        f=dict(key=key,label=label or name,kind=typ,default=default,node=ident,widget=name)
        if typ=='select':f['options']=kind if isinstance(kind,list) else ([x['key'] for x in opts['options']] if kind=='COMFY_DYNAMICCOMBO_V3' else opts.get('options',[]))
        for attr in ('min','max','step','multiline'):
            if attr in opts:f[attr]=opts[attr]
        f['advanced']=name in ('seed','noise_seed','steps','cfg','strength_model')
        if name in ('seed','noise_seed'):f.update(default=-1,min=-1,max=4294967295,random_seed=True)
        f.update({k:v for k,v in overrides.get(key,{}).items() if k in ('label','advanced','min','max','step','default')})
        fields.append(f)
    # Replace an explicitly exposed model-only LoRA selector + strength with a stack.
    # Hidden and fixed workflow LoRAs retain their existing behavior.
    for ident,node in graph.items():
        if node['class_type']!='LoraLoaderModelOnly':continue
        name_field=next((f for f in fields if f['key']==ident+'.lora_name'),None)
        strength_field=next((f for f in fields if f['key']==ident+'.strength_model'),None)
        if not name_field or not strength_field:continue
        stack=dict(key=ident+'.loras',label='LoRA',kind='lora_multi',node=ident,widget='loras',options=name_field['options'],min=strength_field.get('min',-2),max=strength_field.get('max',2),advanced=False,default=[{'name':name_field['default'],'strength':strength_field['default']}] if strength_field['default'] else [])
        index=fields.index(name_field);fields.remove(name_field);fields.remove(strength_field);fields.insert(index,stack)
    groups=meta.get('imageGroups',[]);fieldmap={f['key']:f for f in fields}
    for g in groups:
        if not g.get('fields') or any(k not in fieldmap or fieldmap[k]['kind']!='image' for k in g['fields']):raise ValueError('图片分组配置无效')
        for k in (g.get('count'),g.get('toggle')):
            if k and k not in fieldmap:raise ValueError('图片分组控制参数未公开')
    title=pathlib.PurePosixPath(path).name.removesuffix('.app.json').removesuffix('.json');parts=title.split(' · ',1)
    purpose='video' if any('Video' in graph[k]['class_type'] for k in outputs) else 'image'
    return dict(id=hashlib.sha256(path.encode()).hexdigest()[:16],path=path,name=parts[-1],model=parts[0] if len(parts)>1 else '',title=title,purpose=purpose,description=meta.get('description',''),fields=fields,imageGroups=groups,graph=graph,revision=hashlib.sha256(repr(d).encode()).hexdigest()[:16])

def public_app(a):
    return {k:([{x:y for x,y in f.items() if x not in ('node','widget')} for f in v] if k=='fields' else v) for k,v in a.items() if k not in ('graph','path')}

def build_prompt(a, values, images):
    if not isinstance(values,dict) or not isinstance(images,dict):raise ValueError('参数格式不正确')
    fields={f['key']:f for f in a['fields']}
    if set(values)-set(fields) or set(images)-set(fields):raise ValueError('包含未公开的参数')
    if any(fields[k]['kind']!='image' or not isinstance(v,str) or not v for k,v in images.items()):raise ValueError('图片输入无效')
    p=copy.deepcopy(a['graph']);normalized={};auto={};grouped=set()
    for g in a['imageGroups']:
        selected=[images[k] for k in g['fields'] if k in images]
        if not g.get('min',0)<=len(selected)<=len(g['fields']):raise ValueError(f"请至少上传 {g['min']} 张图片")
        for index,k in enumerate(g['fields']):auto[k]=selected[index] if index<len(selected) else ''
        grouped.update(g['fields'])
        if g.get('count'):auto[g['count']]=len(selected)
        if g.get('toggle'):auto[g['toggle']]=len(selected)>1
    for key,f in fields.items():
        kind=f['kind'];v=auto.get(key,values.get(key,f['default']))
        if kind=='image':
            v=auto[key] if key in grouped else images.get(key,f['default'])
            if key not in grouped and not v:raise ValueError(f"请上传 {f['label']}")
        elif kind=='text':
            if not isinstance(v,str) or len(v)>12000:raise ValueError('文本参数最多 12000 字符')
        elif kind=='bool':
            if type(v) is not bool:raise ValueError(f"{f['label']} 必须为开关值")
        elif kind=='lora_multi':
            from .preferences import valid_value
            if not valid_value(f,v):raise ValueError('LoRA 选择无效，最多启用 8 个，请检查模型和强度')
            normalized[key]=copy.deepcopy(v)
            apply_lora_stack(p,f['node'],v)
            continue
        elif kind=='select':
            if v not in f['options']:raise ValueError(f"{f['label']} 选项无效")
        else:
            if type(v) not in (int,float) or not math.isfinite(v):raise ValueError(f"{f['label']} 必须为有效数字")
            if not f.get('min',-math.inf)<=v<=f.get('max',math.inf):raise ValueError(f"{f['label']} 超出范围")
            if kind=='int' and v!=int(v):raise ValueError(f"{f['label']} 必须为整数")
            if kind=='int':v=int(v)
        normalized[key]=v
        if f.get('random_seed') and v==-1:v=secrets.randbelow(4294967296)
        p[f['node']]['inputs'][f['widget']]=v
    return p,normalized


def apply_lora_stack(graph,ident,choices):
    source=graph[ident]['inputs']['model']
    consumers=[(node,widget) for node,data in graph.items() for widget,value in data['inputs'].items() if value==[ident,0]]
    del graph[ident]
    current=source
    for index,item in enumerate(choices):
        if item['strength']==0:continue
        node_id=f'{ident}_pocket_lora_{index}'
        while node_id in graph:node_id+='_'  # avoid collisions with exported node IDs
        graph[node_id]={'class_type':'LoraLoaderModelOnly','inputs':{'model':current,'lora_name':item['name'],'strength_model':item['strength']},'_meta':{'title':'LoRA: '+item['name']}}
        current=[node_id,0]
    for node,widget in consumers:graph[node]['inputs'][widget]=current
