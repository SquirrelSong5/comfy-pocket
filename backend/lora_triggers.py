"""Local trigger-word overrides; never infer triggers from training tag frequency."""
import json
import pathlib


def normalize_words(value):
    if isinstance(value, str):
        value=value.replace(',', '\n').splitlines()
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(word.strip() for word in value if isinstance(word,str) and 0<len(word.strip())<=500))[:100]


def metadata_words(metadata):
    if not isinstance(metadata,dict):return []
    for key in ('trainedWords','trigger_words','triggerWords','activation_text','ss_activation_text'):
        value=metadata.get(key)
        if isinstance(value,str):
            try:value=json.loads(value)
            except (ValueError,TypeError):pass
        words=normalize_words(value)
        if words:return words
    return []


class TriggerLibrary:
    def __init__(self,path):
        self.path=pathlib.Path(path)
        self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}

    def get(self,name):
        return self.data.get(name)

    def update(self,name,words):
        if words is not None and (not isinstance(words,list) or len(words)>100 or any(not isinstance(w,str) or not w.strip() or len(w)>500 for w in words)):
            raise ValueError('最多保存 100 条词语，每条不超过 500 字')
        candidate=dict(self.data)
        if words is None:candidate.pop(name,None)
        else:candidate[name]=normalize_words(words)
        temp=self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(candidate,ensure_ascii=False),encoding='utf-8');temp.replace(self.path)
        self.data=candidate
