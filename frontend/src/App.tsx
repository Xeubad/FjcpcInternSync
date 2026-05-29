import { ConfigProvider, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { RequireAdmin } from './components/RequireAdmin'
import { RequireAuth } from './components/RequireAuth'
import { AdminTokensPage } from './pages/AdminTokensPage'
import { DashboardPage } from './pages/Dashboard'
import { DiagnosticsPage } from './pages/DiagnosticsPage'
import { LoginPage } from './pages/Login'
import { RecordsPage } from './pages/RecordsPage'
import { TasksPage } from './pages/TasksPage'
import { TextUploadPage } from './pages/TextUploadPage'

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={{ algorithm: theme.defaultAlgorithm }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/app/dashboard" replace />} />
          <Route path="app/dashboard" element={<DashboardPage />} />
          <Route path="app/text-upload" element={<TextUploadPage />} />
          <Route path="app/tasks" element={<TasksPage />} />
          <Route path="app/records" element={<RecordsPage />} />
          <Route path="app/diagnostics" element={<DiagnosticsPage />} />
          <Route
            path="app/admin/tokens"
            element={
              <RequireAdmin>
                <AdminTokensPage />
              </RequireAdmin>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ConfigProvider>
  )
}
