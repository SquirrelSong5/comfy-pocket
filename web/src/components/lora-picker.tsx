import { useState } from 'react'
import { ChevronDown, Folder, Layers3, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'

export interface LoraChoice { name: string; strength: number }
interface FolderNode { path: string; label: string; files: string[]; folders: FolderNode[] }

function modelLabel(name: string) { return name.replace(/\\/g, '/').split('/').pop()!.replace(/\.(safetensors|ckpt|pt)$/i, '') }
function folderLabel(name: string) { const parts = name.replace(/\\/g, '/').split('/'); parts.pop(); return parts.join(' / ') || '根目录' }
function folderTree(names: string[]): FolderNode {
  const root: FolderNode = { path: '', label: '根目录', files: [], folders: [] }
  for (const name of names) {
    const parts = name.replace(/\\/g, '/').split('/'); parts.pop()
    let node = root
    for (const label of parts) {
      const path = node.path ? node.path + '/' + label : label
      let child = node.folders.find(folder => folder.path === path)
      if (!child) { child = { path, label, files: [], folders: [] }; node.folders.push(child) }
      node = child
    }
    node.files.push(name)
  }
  function sort(node: FolderNode) {
    node.files.sort((a, b) => a.localeCompare(b, 'zh-CN', { numeric: true }))
    node.folders.sort((a, b) => a.label.localeCompare(b.label, 'zh-CN', { numeric: true }))
    node.folders.forEach(sort)
  }
  sort(root); return root
}
function allFiles(node: FolderNode): string[] { return [...node.files, ...node.folders.flatMap(allFiles)] }
function folderPaths(node: FolderNode): string[] { return [node.path, ...node.folders.flatMap(folderPaths)] }

export function LoraPicker({ id, options, value, min, max, onChange }: {
  id: string; options: string[]; value: LoraChoice[]; min: number; max: number; onChange: (value: LoraChoice[]) => void
}) {
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set())
  const query = search.trim().toLocaleLowerCase()
  const tree = folderTree(options.filter(name => name.toLocaleLowerCase().includes(query)))
  function toggle(name: string, checked: boolean) {
    if (checked && value.length >= 8) return
    onChange(checked ? [...value, { name, strength: 0.8 }] : value.filter(item => item.name !== name))
  }
  function setOpen(path: string, open: boolean) {
    if (query) return
    setExpanded(previous => {
      if (previous.has(path) === open) return previous
      const next = new Set(previous); if (open) next.add(path); else next.delete(path); return next
    })
  }
  function renderFolder(node: FolderNode) {
    const files = allFiles(node), chosen = files.filter(name => value.some(item => item.name === name)).length
    return <details key={node.path} className="lora-folder" open={!!query || expanded.has(node.path)} onToggle={e => setOpen(node.path, e.currentTarget.open)}>
      <summary aria-label={'文件夹 ' + (node.path || '根目录')}>
        <ChevronDown className="lora-folder-chevron" aria-hidden="true" /><Folder className="lora-folder-icon" aria-hidden="true" />
        <span className="lora-folder-title">{node.label}</span>
        {chosen > 0 && <Badge variant="secondary">已选 {chosen}</Badge>}
        <span className="lora-folder-count">{files.length}</span>
      </summary>
      <div className="lora-folder-content">
        {!node.path && !node.files.length && !node.folders.length && <p className="lora-library-empty">根目录暂无模型</p>}
        {node.folders.map(renderFolder)}
        {node.files.length > 0 && <FieldGroup className="lora-folder-files">
          {node.files.map(name => {
            const checked = value.some(item => item.name === name), inputId = id + '-option-' + encodeURIComponent(name)
            return <Field key={name} orientation="horizontal" className="lora-picker-option" data-selected={checked || undefined}>
              <FieldLabel htmlFor={inputId} title={name}>{modelLabel(name)}</FieldLabel>
              <Switch id={inputId} aria-label={name} checked={checked} disabled={!checked && value.length >= 8} onCheckedChange={enabled => toggle(name, enabled)} />
            </Field>
          })}
        </FieldGroup>}
      </div>
    </details>
  }
  const active = value.filter(item => item.strength !== 0).length
  return <Field className="lora-picker">
    <div className="lora-picker-heading">
      <FieldLabel><Layers3 aria-hidden="true" />LoRA 模型</FieldLabel>
      <Badge variant={active ? 'secondary' : 'outline'}>{active ? '已启用 ' + active : '未启用'}</Badge>
    </div>
    <div className="lora-library">
      <Input aria-label="搜索 LoRA" placeholder="搜索模型名称或文件夹…" value={search} onChange={e => setSearch(e.target.value)} />
      <div className="lora-library-toolbar">
        <span>{query ? '匹配 ' + allFiles(tree).length + ' 个' : options.length + ' 个模型 · 按底模分类'}</span>
        <div>
          <Button type="button" variant="ghost" size="sm" aria-label="展开全部 LoRA 文件夹" disabled={!!query} onClick={() => setExpanded(new Set(folderPaths(tree)))}>展开</Button>
          <Button type="button" variant="ghost" size="sm" aria-label="收起全部 LoRA 文件夹" disabled={!!query} onClick={() => setExpanded(new Set())}>收起</Button>
        </div>
      </div>
      <div className="lora-picker-list" role="group" aria-label="可选 LoRA">
        {renderFolder({ ...tree, folders: [] })}
        {tree.folders.map(renderFolder)}
        {!allFiles(tree).length && <p className="lora-library-empty">没有匹配的模型，试试其他名称。</p>}
      </div>
    </div>
    {value.length > 0 && <FieldGroup className="lora-selected-models">
      <p className="lora-selected-heading">已选模型 <span>{value.length} / 8</span></p>
      {value.map(item => <Field key={item.name} orientation="horizontal" className="lora-picker-selected" data-inactive={item.strength === 0 || undefined}>
        <FieldLabel htmlFor={id + '-strength-' + encodeURIComponent(item.name)} title={item.name}>
          <span>{modelLabel(item.name)}</span><small>{folderLabel(item.name)}{item.strength === 0 ? ' · 已关闭' : ''}</small>
        </FieldLabel>
        <Input id={id + '-strength-' + encodeURIComponent(item.name)} type="number" aria-label={item.name + ' 强度'} min={min} max={max} step={0.05} value={item.strength} onChange={e => {
          if (!e.target.value) return
          const strength = Number(e.target.value)
          if (Number.isFinite(strength) && strength >= min && strength <= max) onChange(value.map(chosen => chosen.name === item.name ? { ...chosen, strength } : chosen))
        }} />
        <Button type="button" variant="ghost" size="icon-sm" aria-label={'移除 ' + item.name} onClick={() => toggle(item.name, false)}><X /></Button>
      </Field>)}
    </FieldGroup>}
    <FieldDescription>最多选 8 个；强度 0 为关闭。仅启用项显示触发词，模型需与底模兼容。</FieldDescription>
  </Field>
}
