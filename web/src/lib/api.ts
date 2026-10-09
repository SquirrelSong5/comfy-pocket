export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 90000)
  try {
    const response = await fetch('/api' + path, {
      ...options,
      headers: {
        'X-Requested-With': 'comfy-lite',
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...options.headers,
      },
      signal: controller.signal,
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || '请求失败')
    return data
  } finally {
    clearTimeout(timeout)
  }
}
