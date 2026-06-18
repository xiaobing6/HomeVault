import { defineStore } from 'pinia'

import { fetchCurrentUserApi, loginApi, logoutApi, type CurrentUser } from '../api/auth'
import { setAccessToken } from '../api/client'

const TOKEN_KEY = 'homevault_access_token'

interface AuthState {
  token: string | null
  user: CurrentUser | null
  initialized: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: sessionStorage.getItem(TOKEN_KEY),
    user: null,
    initialized: false
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
    permissions: (state) => new Set(state.user?.permissions ?? []),
    hasPermission: (state) => {
      const permissions = new Set(state.user?.permissions ?? [])
      return (permission: string) => permissions.has(permission)
    }
  },
  actions: {
    async initialize() {
      if (this.initialized) return
      if (!this.token) {
        this.initialized = true
        return
      }
      setAccessToken(this.token)
      try {
        this.user = await fetchCurrentUserApi()
      } catch {
        this.clearSession()
      } finally {
        this.initialized = true
      }
    },
    async login(username: string, password: string) {
      const result = await loginApi(username, password)
      this.token = result.access_token
      this.user = result.user
      sessionStorage.setItem(TOKEN_KEY, result.access_token)
      setAccessToken(result.access_token)
    },
    async logout() {
      try {
        if (this.token) await logoutApi()
      } finally {
        this.clearSession()
      }
    },
    clearSession() {
      this.token = null
      this.user = null
      sessionStorage.removeItem(TOKEN_KEY)
      setAccessToken(null)
    }
  }
})
