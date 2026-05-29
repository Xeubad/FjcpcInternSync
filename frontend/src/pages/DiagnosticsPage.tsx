import { Alert, Descriptions, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { api } from '../services/api'
import { useAuthStore } from '../store/authStore'

interface AuditRow {
  event?: string
  username?: string
  role?: string
  ts?: string
}

interface HintRow {
  code: string
  hint: string
}

export function DiagnosticsPage() {
  const role = useAuthStore((state) => state.role)
  const [audit, setAudit] = useState<AuditRow[]>([])
  const [hints, setHints] = useState<HintRow[]>([])
  const [summaryText, setSummaryText] = useState<string>('')

  const load = async () => {
    try {
      const { data } = await api.get('/monitor/diagnostics')
      if (data.success) {
        setAudit((data.data.recent_audit as AuditRow[]) ?? [])
        setHints((data.data.error_hints as HintRow[]) ?? [])
        const summary = data.data.task_summary as {
          total?: number
          success_rate?: number
        }
        setSummaryText(
          `窗口任务 ${summary.total ?? 0}，成功率 ${((summary.success_rate ?? 0) * 100).toFixed(1)}%`,
        )
      }
    } catch {
      message.error('加载诊断数据失败（需管理员权限）')
    }
  }

  useEffect(() => {
    if (role === 'admin') void load()
  }, [role])

  if (role !== 'admin') {
    return <Navigate to="/app/dashboard" replace />
  }

  const columns: ColumnsType<AuditRow> = [
    { title: '时间', dataIndex: 'ts', width: 220 },
    { title: '事件', dataIndex: 'event' },
    { title: '用户', dataIndex: 'username' },
    { title: '角色', dataIndex: 'role' },
  ]

  return (
    <div>
      <Typography.Title level={4}>错误诊断</Typography.Title>
      <Alert
        type="info"
        showIcon
        message="管理员视图"
        description="聚合审计日志与错误码建议；业务日志可在后端 data/logs 目录查看。"
        style={{ marginBottom: 16 }}
      />
      <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="任务概览">{summaryText}</Descriptions.Item>
      </Descriptions>
      <Typography.Title level={5}>最近审计</Typography.Title>
      <Table<AuditRow> rowKey={(row) => `${row.ts}-${row.username}`} columns={columns} dataSource={audit} pagination={false} />
      <Typography.Title level={5} style={{ marginTop: 24 }}>
        错误码建议
      </Typography.Title>
      <Table<HintRow>
        rowKey="code"
        pagination={false}
        columns={[
          { title: '错误码', dataIndex: 'code', width: 220, render: (text) => <Typography.Text code>{text}</Typography.Text> },
          { title: '建议动作', dataIndex: 'hint' },
        ]}
        dataSource={hints}
      />
    </div>
  )
}
