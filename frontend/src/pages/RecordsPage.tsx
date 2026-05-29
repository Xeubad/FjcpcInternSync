import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import { Button, DatePicker, Select, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'

import { api } from '../services/api'

interface TaskRow {
  id: string
  type: string
  status: string
  created_at: string
  created_by: string
  error_code?: string | null
}

export function RecordsPage() {
  const [tasks, setTasks] = useState<TaskRow[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string | undefined>()
  const [date, setDate] = useState<Dayjs | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/tasks', { params: { limit: 200 } })
      if (data.success) {
        setTasks((data.data.tasks as TaskRow[]) ?? [])
      }
    } catch {
      message.error('加载记录失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const filtered = useMemo(() => {
    return tasks.filter((row) => {
      if (status && row.status !== status) return false
      if (date) {
        const rowDay = dayjs(row.created_at.slice(0, 10))
        if (!rowDay.isSame(date, 'day')) return false
      }
      return true
    })
  }, [tasks, status, date])

  const columns: ColumnsType<TaskRow> = [
    { title: '任务 ID', dataIndex: 'id', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'type',
      render: (value: string) =>
        ({ day: '日报', week: '周报', month: '月报' }[value] ?? value),
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (value: string) => {
        const color =
          value === 'success' ? 'green' : value === 'failed' ? 'red' : value === 'running' ? 'blue' : 'gold'
        return <Tag color={color}>{value}</Tag>
      },
    },
    { title: '创建人', dataIndex: 'created_by' },
    { title: '创建时间', dataIndex: 'created_at', width: 200 },
    {
      title: '错误码',
      dataIndex: 'error_code',
      render: (value: string | null | undefined) => value ?? '-',
    },
  ]

  const exportCsv = () => {
    const header = ['id', 'type', 'status', 'created_by', 'created_at', 'error_code']
    const lines = [
      header.join(','),
      ...filtered.map((row) =>
        [row.id, row.type, row.status, row.created_by, row.created_at, row.error_code ?? ''].join(','),
      ),
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `upload-records-${dayjs().format('YYYYMMDD-HHmm')}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <Typography.Title level={4}>上传记录</Typography.Title>
      <Typography.Paragraph type="secondary">
        按状态 / 日期筛选任务记录，并导出 CSV。
      </Typography.Paragraph>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          allowClear
          placeholder="状态"
          style={{ width: 160 }}
          value={status}
          onChange={setStatus}
          options={[
            { label: 'pending', value: 'pending' },
            { label: 'running', value: 'running' },
            { label: 'success', value: 'success' },
            { label: 'failed', value: 'failed' },
          ]}
        />
        <DatePicker value={date} onChange={setDate} placeholder="创建日期" />
        <Button icon={<ReloadOutlined />} onClick={() => void load()}>
          刷新
        </Button>
        <Button icon={<DownloadOutlined />} onClick={exportCsv}>
          导出 CSV
        </Button>
      </Space>
      <Table<TaskRow>
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={filtered}
        pagination={{ pageSize: 10 }}
      />
    </div>
  )
}
