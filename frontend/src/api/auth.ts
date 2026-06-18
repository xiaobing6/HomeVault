import { apiClient } from './client'

export interface CurrentUser {
  id: number
  username: string
  display_name: string
  roles: string[]
  permissions: string[]
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  user: CurrentUser
}

export async function loginApi(username: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', { username, password })
  return response.data
}

export async function fetchCurrentUserApi(): Promise<CurrentUser> {
  const response = await apiClient.get<CurrentUser>('/auth/me')
  return response.data
}

export async function logoutApi(): Promise<void> {
  await apiClient.post('/auth/logout')
}
