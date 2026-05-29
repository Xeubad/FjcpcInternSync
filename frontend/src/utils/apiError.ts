/** 从 Axios / FastAPI 响应体解析可读错误信息 */
export function getApiErrorMessage(error: unknown, fallback = '请求失败'): string {
  const err = error as {
    response?: { data?: Record<string, unknown> }
    message?: string
  }
  const data = err.response?.data
  if (data && typeof data === 'object') {
    if (typeof data.message === 'string' && data.message) return data.message
    const detail = data.detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const msg = (detail as { message?: string }).message
      if (typeof msg === 'string' && msg) return msg
    }
    if (typeof detail === 'string' && detail) return detail
  }
  if (typeof err.message === 'string' && err.message && !err.message.startsWith('Request failed')) {
    return err.message
  }
  return fallback
}
