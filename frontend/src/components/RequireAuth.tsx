import type { ReactElement } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuthStore } from '../store/authStore'

export function RequireAuth({ children }: { children: ReactElement }) {
  const token = useAuthStore((state) => state.token)
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}
