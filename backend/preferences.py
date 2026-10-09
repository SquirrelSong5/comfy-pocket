"""Last-used application parameters shared by clients of this Pocket service."""
import copy
import json
import math
import pathlib


def valid_value(field, value):
    kind=field['kind']
    if kind=='text':return isinstance(value,str) and len(value)<=12000
    if kind=='bool':return type(value) is bool
    if kind=='lora_multi':
        if not isinstance(value,list) or len(value)>8:return False
        names=set()
        for item in value:
            if not isinstance(item,dict) or set(item)!={'name','strength'}:return False
            name=item['name'];strength=item['strength']
            if not isinstance(name,str) or name not in field['options'] or name in names or type(strength) not in (int,float) or not math.isfinite(strength) or not field.get('min',-2)<=strength<=field.get('max',2):return False
            names.add(name)
        return True
    if kind=='select':return any(type(value) is type(option) and value==option for option in field['options'])
    if kind not in ('int','float') or type(value) not in (int,float):return False
    return math.isfinite(value) and (kind!='int' or value==int(value)) and field.get('min',-math.inf)<=value<=field.get('max',math.inf)


class Preferences:
    def __init__(self,path):
        self.path=pathlib.Path(path)
        self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'selected':'','drafts':{}}

    def snapshot(self,catalog):
        if not catalog:return copy.deepcopy(self.data)
        drafts={}
        for ident,app in catalog.items():
            saved=self.data['drafts'].get(ident,{})
            drafts[ident]={f['key']:saved[f['key']] if f['key'] in saved and valid_value(f,saved[f['key']]) else f['default'] for f in app['fields'] if f['kind']!='image'}
        selected=self.data['selected']
        return {'selected':selected if selected in catalog else next(iter(catalog),''),'drafts':drafts}

    def update(self,app,values=None,reset=False):
        if values is not None and (not isinstance(values,dict) or reset):raise ValueError('参数保存格式不正确')
        fields={f['key']:f for f in app['fields']}
        for key,value in (values or {}).items():
            if key not in fields or not valid_value(fields[key],value):raise ValueError('无法保存无效参数：'+str(key))
        candidate=copy.deepcopy(self.data);candidate['selected']=app['id']
        if reset:candidate['drafts'].pop(app['id'],None)
        elif values is not None:candidate['drafts'].setdefault(app['id'],{}).update(values)
        temp=self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(candidate,ensure_ascii=False),encoding='utf-8');temp.replace(self.path)
        self.data=candidate
