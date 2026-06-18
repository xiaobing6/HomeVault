import axios, { AxiosError } from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export function setAccessToken(token: string | null) {
  if (token) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`
  } else {
    delete apiClient.defaults.headers.common.Authorization
  }
}

export function getChineseErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data as { message?: string; detail?: { message?: string } } | undefined
    return data?.message || data?.detail?.message || '操作失败，请稍后重试'
  }
  return '操作失败，请稍后重试'
}
