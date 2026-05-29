import {
  CloudUploadOutlined,
  DashboardOutlined,
  FileTextOutlined,
  LogoutOutlined,
  MedicineBoxOutlined,
  ProfileOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Layout, Menu, Tag, Typography } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuthStore } from '../store/authStore'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/app/dashboard', icon: <DashboardOutlined />, label: '状态看板' },
  { key: '/app/text-upload', icon: <FileTextOutlined />, label: '文本上传' },
  { key: '/app/tasks', icon: <CloudUploadOutlined />, label: '表格识别上传' },
  { key: '/app/records', icon: <ProfileOutlined />, label: '上传记录' },
  { key: '/app/diagnostics', icon: <MedicineBoxOutlined />, label: '错误诊断' },
  { key: '/app/admin/tokens', icon: <SafetyCertificateOutlined />, label: '令牌管理' },
]

export function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { username, role, logout } = useAuthStore()

  const visibleItems = menuItems.filter((item) => {
    if (role !== 'admin' && (item.key === '/app/diagnostics' || item.key === '/app/admin/tokens')) {
      return false
    }
    return true
  })

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={64}>
        <div
          style={{
            height: 64,
            margin: 16,
            borderRadius: 8,
            background: 'rgba(255,255,255,0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 600,
            letterSpacing: 0.5,
          }}
        >
          InternSync
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={visibleItems.map(({ key, icon, label }) => ({
            key,
            icon,
            label,
            onClick: () => navigate(key),
          }))}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingInline: 24,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Typography.Title level={4} style={{ margin: 0 }}>
            船政实习上传控制台
          </Typography.Title>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Tag color={role === 'admin' ? 'blue' : 'green'} icon={<UserOutlined />}>
              {username} · {role === 'admin' ? '管理员' : '普通用户'}
            </Tag>
            <a
              onClick={() => {
                logout()
                navigate('/login')
              }}
              style={{ cursor: 'pointer' }}
            >
              <LogoutOutlined /> 退出
            </a>
          </div>
        </Header>
        <Content style={{ margin: 24 }}>
          <div
            style={{
              background: '#fff',
              padding: 24,
              borderRadius: 12,
              minHeight: 520,
              boxShadow: '0 8px 24px rgba(15,23,42,0.06)',
            }}
          >
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}
