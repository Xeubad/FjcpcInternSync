import { KeyOutlined, LockOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Card, Form, Input, Tabs, Typography, message } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'

import { api } from '../services/api'
import { useAuthStore } from '../store/authStore'
import { getApiErrorMessage } from '../utils/apiError'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useAuthStore((state) => state.setAuth)

  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ??
    '/app/dashboard'

  const onPasswordLogin = async (values: { username: string; password: string }) => {
    try {
      const { data } = await api.post('/auth/login', {
        username: values.username,
        password: values.password,
      })
      if (!data.success) {
        message.error(data.message ?? '登录失败')
        return
      }
      const payload = data.data as { token: string; username: string; role: string }
      setAuth(payload.token, payload.username, payload.role)
      message.success('登录成功')
      navigate(from, { replace: true })
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '登录请求失败'))
    }
  }

  const onTokenLogin = async (values: { access_token: string }) => {
    const accessToken = values.access_token?.trim()
    if (!accessToken) {
      message.warning('请输入访问令牌')
      return
    }
    try {
      const { data } = await api.post('/auth/login', { token: accessToken })
      if (!data.success) {
        message.error(data.message ?? '登录失败')
        return
      }
      const payload = data.data as { token: string; username: string; role: string }
      setAuth(payload.token, payload.username, payload.role)
      message.success('登录成功（访问令牌）')
      navigate(from, { replace: true })
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '令牌登录失败'))
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0f172a',
        padding: 24,
      }}
    >
      <Card style={{ width: 440, borderRadius: 16 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>
          FjcpcInternSync
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          管理台账号或旧版一次性访问令牌 · 登录后请使用 Bearer 调用接口
        </Typography.Paragraph>
        <Tabs
          defaultActiveKey="password"
          items={[
            {
              key: 'password',
              label: '账号密码',
              children: (
                <Form layout="vertical" onFinish={onPasswordLogin} initialValues={{ username: 'admin' }}>
                  <Form.Item
                    label="用户名"
                    name="username"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input prefix={<UserOutlined />} placeholder="admin / user" />
                  </Form.Item>
                  <Form.Item
                    label="密码"
                    name="password"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password prefix={<LockOutlined />} placeholder="见后端 .env.example" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block size="large">
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: 'token',
              label: '访问令牌',
              children: (
                <Form layout="vertical" onFinish={onTokenLogin}>
                  <Form.Item
                    label="一次性 Token"
                    name="access_token"
                    rules={[{ required: true, message: '请输入管理员发放的访问令牌' }]}
                  >
                    <Input.Password prefix={<KeyOutlined />} placeholder="粘贴 auth_tokens 中的令牌" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block size="large">
                    使用令牌登录
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
