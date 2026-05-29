import { DeleteOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { Button, Card, Input, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useState } from 'react'

import { api } from '../services/api'
import { getApiErrorMessage } from '../utils/apiError'

interface TokenRow {
  token?: string
  enabled?: boolean
  used?: boolean
  created_at?: string
}

export function AdminTokensPage() {
  const [adminKey, setAdminKey] = useState('')
  const [rows, setRows] = useState<TokenRow[]>([])
  const [loading, setLoading] = useState(false)

  const loadList = useCallback(async (opts?: { silent?: boolean }) => {
    if (!adminKey.trim()) {
      message.warning('请先填写管理员密钥')
      return
    }
    setLoading(true)
    try {
      const { data } = await api.get('/auth/tokens', { params: { admin_key: adminKey.trim() } })
      if (data.success) {
        const items = (data.tokens as TokenRow[]) ?? []
        setRows(items)
        if (!opts?.silent) {
          message.success(`共 ${data.total ?? items.length} 条`)
        }
      } else {
        message.error(data.message ?? '加载失败')
      }
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '加载失败'))
    } finally {
      setLoading(false)
    }
  }, [adminKey])

  const handleGenerate = async () => {
    if (!adminKey.trim()) {
      message.warning('请填写管理员密钥')
      return
    }
    setLoading(true)
    try {
      const { data } = await api.post('/auth/generate_token', { admin_key: adminKey.trim() })
      if (data.success && data.token) {
        message.success('已生成新令牌，请在下方表格中点击令牌列的复制图标保存完整内容')
        await loadList({ silent: true })
      } else {
        message.error(data.message ?? '生成失败')
      }
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '生成失败'))
    } finally {
      setLoading(false)
    }
  }

  const handleRevoke = async (rawToken: string) => {
    if (!adminKey.trim()) {
      message.warning('请填写管理员密钥')
      return
    }
    setLoading(true)
    try {
      const { data } = await api.post('/auth/revoke_token', {
        admin_key: adminKey.trim(),
        token: rawToken,
      })
      if (data.success) {
        message.success('已禁用')
        await loadList()
      } else {
        message.error(data.message ?? '操作失败')
      }
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '操作失败'))
    } finally {
      setLoading(false)
    }
  }

  const maskToken = (t: string | undefined) => {
    if (!t || t.length <= 12) return '***'
    return `${t.slice(0, 6)}…${t.slice(-4)}`
  }

  const columns: ColumnsType<TokenRow & { key: number }> = [
    {
      title: '令牌',
      dataIndex: 'token',
      ellipsis: true,
      render: (t: string | undefined) =>
        t ? (
          <Typography.Text copyable={{ text: t }} ellipsis={{ tooltip: maskToken(t) }} style={{ maxWidth: 320 }}>
            {maskToken(t)}
          </Typography.Text>
        ) : (
          '—'
        ),
    },
    { title: '创建时间', dataIndex: 'created_at', width: 200 },
    {
      title: '状态',
      dataIndex: 'used',
      width: 90,
      render: (used: boolean | undefined) => (
        <Tag color={used ? 'default' : 'green'}>{used ? '已使用' : '未使用'}</Tag>
      ),
    },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 72,
      render: (en: boolean | undefined) => <Tag color={en === false ? 'red' : 'green'}>{en === false ? '否' : '是'}</Tag>,
    },
    {
      title: '操作',
      key: 'op',
      width: 100,
      render: (_, record) =>
        record.token ? (
          <Button
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => void handleRevoke(record.token as string)}
          >
            禁用
          </Button>
        ) : null,
    },
  ]

  const tableData = rows.map((r, i) => ({ ...r, key: i }))

  return (
    <div>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        访问令牌管理
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        使用环境变量中的 ADMIN_KEY。生成后请在下方表格「令牌」列使用复制图标，仅复制完整令牌字符串；列表中为脱敏显示。
      </Typography.Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap align="center">
          <Input.Password
            style={{ width: 280 }}
            placeholder="管理员密钥 ADMIN_KEY"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
          />
          <Button type="primary" icon={<PlusOutlined />} loading={loading} onClick={() => void handleGenerate()}>
            生成新令牌
          </Button>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={() => void loadList()}>
            刷新列表
          </Button>
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={tableData}
        loading={loading}
        pagination={{ pageSize: 8 }}
      />
    </div>
  )
}
