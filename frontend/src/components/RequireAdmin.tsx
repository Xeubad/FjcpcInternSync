import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuthStore } from '../store/authStore'

export function RequireAdmin({ children }: { children: ReactNode }) {
  const role = useAuthStore((s) => s.role)
  if (role !== 'admin') {
    return <Navigate to="/app/dashboard" replace />
  }
  return <>{children}</>
}
