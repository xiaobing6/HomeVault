import { apiClient } from './client'

function mediaApiPath(url: string): string {
  if (url.startsWith('/api/')) return url.slice(4)
  if (url.startsWith('api/')) return `/${url.slice(4)}`
  return url
}

export async function createProtectedMediaObjectUrl(url: string): Promise<string> {
  const response = await apiClient.get<Blob>(mediaApiPath(url), {
    responseType: 'blob',
    timeout: 30000
  })
  return URL.createObjectURL(response.data)
}

export async function downloadProtectedMedia(url: string, filename: string): Promise<void> {
  const objectUrl = await createProtectedMediaObjectUrl(url)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename || 'download'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
}
