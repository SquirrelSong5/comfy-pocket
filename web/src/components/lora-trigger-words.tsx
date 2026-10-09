import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'

interface Triggers { name: string; words: string[]; source: string }

export function LoraTriggerWords({ id, names, onInsert }: { id: string; names: string[]; onInsert: (word: string) => void }) {
  const active = [...new Set(names)]
  if (!active.length) return null
  return <details className="lora-triggers">
    <summary>已启用 LoRA 的触发词 · 点击填入提示词</summary>
    {active.map(name => <section key={name} className="lora-trigger-group" aria-label={name}>
      <p className="lora-trigger-name">{name}</p>
      <TriggerEditor id={id + '-' + encodeURIComponent(name)} name={name} onInsert={onInsert} />
    </section>)}
  </details>
}

function TriggerEditor({ id, name, onInsert }: { id: string; name: string; onInsert: (word: string) => void }) {
  const [data, setData] = useState<Triggers | null>(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(true)
  const [status, setStatus] = useState('读取触发词…')
  const [error, setError] = useState('')
  useEffect(() => {
    let stopped = false
    void api<Triggers>('/lora-triggers?name=' + encodeURIComponent(name)).then(value => {
      if (!stopped) { setData(value); setDraft(value.words.join('\n')); setStatus(value.source === 'manual' ? '已读取电脑上保存的词库' : value.words.length ? '来自模型元数据' : '模型未附触发词，可补充常用词或编辑指令') }
    }).catch(e => { if (!stopped) { setError(e.message); setStatus('读取失败') } }).finally(() => { if (!stopped) setBusy(false) })
    return () => { stopped = true }
  }, [name])
  async function save(reset = false) {
    setBusy(true); setError('')
    try {
      const words = [...new Set(draft.split(/\r?\n/).map(w => w.trim()).filter(Boolean))]
      const value = await api<Triggers>('/lora-triggers', { method: 'POST', body: JSON.stringify(reset ? { name, reset: true } : { name, words }) })
      setData(value); setDraft(value.words.join('\n')); setStatus(reset ? '已恢复模型元数据' : '词库已保存到电脑，其他设备也可使用')
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <div className="lora-trigger-editor">
    <p role="status" className="lora-trigger-status">{status}</p>
    {!!data?.words.length && <div className="lora-trigger-buttons" aria-label="可插入的触发词">
      {data.words.map(word => <Button key={word} type="button" variant="outline" size="sm" disabled={busy} onClick={() => onInsert(word)}>{word}</Button>)}
    </div>}
    <details className="lora-trigger-settings">
      <summary>编辑词库</summary>
      <Field>
        <FieldLabel htmlFor={id + '-trigger-words'}>触发词 / 常用编辑指令</FieldLabel>
        <Textarea id={id + '-trigger-words'} value={draft} onChange={e => setDraft(e.target.value)} disabled={busy || !data} rows={3} maxLength={50000} placeholder="每行一条，点击上方按钮即可填入" />
        <FieldDescription>每行一条，最多 100 条，每条最多 500 字。优先填写作者提供的词。</FieldDescription>
      </Field>
      <div className="lora-trigger-actions">
        <Button type="button" size="sm" disabled={busy || !data} onClick={() => void save()}>保存词库到电脑</Button>
        <Button type="button" size="sm" variant="ghost" disabled={busy || !data} onClick={() => void save(true)}>恢复模型词库</Button>
      </div>
    </details>
    {error && <p role="alert" className="lora-trigger-error">{error}</p>}
  </div>
}
