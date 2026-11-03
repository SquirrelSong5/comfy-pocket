import { useEffect, useRef, useState } from 'react'
import { Input } from '@/components/ui/input'

interface NumericInputProps {
  id: string
  value: string | number
  integer?: boolean
  min?: number
  max?: number
  step?: number
  onValueChange: (value: string | number) => void
}

// Keep the text being edited separate from the validated numeric parameter.
// In particular, deleting the last digit must not turn an empty string into 0.
export function NumericInput({ id, value, integer, min, max, step, onValueChange }: NumericInputProps) {
  const [draft, setDraft] = useState(String(value ?? ''))
  const editing = useRef(false)
  const valid = (text: string | number) => String(text).trim() !== '' &&
    Number.isFinite(Number(text)) && (!integer || Number.isInteger(Number(text))) &&
    Number(text) >= (min ?? -Infinity) && Number(text) <= (max ?? Infinity)
  const lastValid = useRef(valid(value) ? Number(value) : undefined)

  useEffect(() => {
    if (!editing.current) setDraft(String(value ?? ''))
    if (valid(value)) lastValid.current = Number(value)
  }, [value, integer, min, max]) // eslint-disable-line react-hooks/exhaustive-deps

  return <Input id={id} type="text" inputMode={integer ? 'numeric' : 'decimal'}
    value={draft} min={min} max={max} step={step}
    aria-invalid={draft !== '' && !valid(draft)}
    onFocus={() => { editing.current = true }}
    onChange={event => {
      const text = event.target.value
      setDraft(text)
      if (valid(text)) lastValid.current = Number(text)
      onValueChange(text.trim() === '' ? '' : Number.isFinite(Number(text)) ? Number(text) : text)
    }}
    onBlur={() => {
      editing.current = false
      const number = valid(draft) ? Number(draft) : lastValid.current
      if (number !== undefined) {
        setDraft(String(number))
        onValueChange(number)
      }
    }}/>
}
