import axios from 'axios'

import { useAuthStore } from '../store/authStore'
import { getApiErrorMessage } from '../utils/apiError'

export const api = axios.create({
  baseURL: '/api',
  timeout: 60_000,
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 后端重启会清空内存会话，旧 Bearer token 失效 -> 401。
    // 此时清掉本地登录态并跳转登录页，避免一直刷 401。
    if (error?.response?.status === 401) {
      const { token, logout } = useAuthStore.getState()
      if (token) {
        logout()
        if (window.location.pathname !== '/login') {
          window.location.assign('/login')
        }
      }
    }
    const msg = getApiErrorMessage(error, '请求失败')
    ;(error as { friendlyMessage?: string }).friendlyMessage = msg
    return Promise.reject(error)
  },
)

export interface ApiSuccess<T> {
  success: true
  data?: T
  message?: string
}

export interface ApiFailure {
  success: false
  message: string
  error: { code: string; detail?: unknown }
}
