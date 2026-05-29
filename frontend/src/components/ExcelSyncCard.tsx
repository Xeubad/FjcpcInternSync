import { CloudUploadOutlined, FileSearchOutlined } from '@ant-design/icons'
import { Button, Card, Space, Typography, Upload, message } from 'antd'
import type { UploadProps } from 'antd/es/upload/interface'
import { useState } from 'react'

import { api } from '../services/api'
import { getApiErrorMessage } from '../utils/apiError'

interface AnalyzeSuccess {
  success: boolean
  total?: number
  day_count?: number
  week_count?: number
  month_count?: number
  full_data?: { day: unknown[]; week: unknown[]; month: unknown[] }
  message?: string
}

interface ExcelSyncCardProps {
  studentId: string
  platformToken: string
}

/** 旧版「分析 Excel → 同步 /api/upload/excel」流程（学号/Token 由页面共享配置传入） */
export function ExcelSyncCard({ studentId, platformToken }: ExcelSyncCardProps) {
  const [analyzeSummary, setAnalyzeSummary] = useState<string | null>(null)
  const [cachedFullData, setCachedFullData] = useState<AnalyzeSuccess['full_data'] | null>(null)
  const [totalRecords, setTotalRecords] = useState(0)
  const [syncing, setSyncing] = useState(false)

  const analyzeProps: UploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    accept: '.xlsx,.xls,.xlsm',
    beforeUpload: (file) => {
      void (async () => {
        const fd = new FormData()
        fd.append('file', file)
        try {
          const { data } = await api.post<AnalyzeSuccess>('/excel/analyze', fd)
          if (!data.success) {
            message.error(data.message ?? '分析失败')
            setCachedFullData(null)
            setAnalyzeSummary(null)
            return
          }
          const total = data.total ?? 0
          setTotalRecords(total)
          setCachedFullData(data.full_data ?? { day: [], week: [], month: [] })
          const parts: string[] = []
          if (data.day_count) parts.push(`日报 ${data.day_count} 条`)
          if (data.week_count) parts.push(`周报 ${data.week_count} 条`)
          if (data.month_count) parts.push(`月报 ${data.month_count} 条`)
          setAnalyzeSummary(total > 0 ? `${parts.join('，')}，共 ${total} 条待上传` : '未检测到有效数据')
          message.success('分析完成')
        } catch (error: unknown) {
          message.error(getApiErrorMessage(error, '分析失败'))
          setCachedFullData(null)
          setAnalyzeSummary(null)
        }
      })()
      return false
    },
  }

  const syncUpload = async () => {
    if (!studentId.trim() || !platformToken.trim()) {
      message.warning('请先在上方填写学号与平台 Token')
      return
    }
    if (!cachedFullData || totalRecords === 0) {
      message.warning('请先分析 Excel 且至少有一条有效记录')
      return
    }
    setSyncing(true)
    try {
      const { data, status } = await api.post(
        '/upload/excel',
        {
          student_id: studentId.trim(),
          token: platformToken.trim(),
          cached_data: { full_data: cachedFullData },
        },
        { validateStatus: () => true },
      )
      const msg = typeof data.message === 'string' ? data.message : '上传结束'
      if (data.success && status < 400) {
        message.success(msg)
      } else {
        message.error(msg)
      }
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '上传失败'))
    } finally {
      setSyncing(false)
    }
  }

  return (
    <Card
      title={
        <Space>
          <FileSearchOutlined />
          Excel：分析后同步上传（旧版接口）
        </Space>
      }
      style={{ marginBottom: 24 }}
    >
      <Typography.Paragraph type="secondary">
        等价旧版「分析文件 → 上传」：先调用 <Typography.Text code>/api/excel/analyze</Typography.Text>，
        再调用 <Typography.Text code>POST /api/upload/excel</Typography.Text> 同步返回每条结果（不等任务队列）。
        学号与平台 Token 使用页面顶部的共享配置。
      </Typography.Paragraph>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Upload {...analyzeProps}>
          <Button icon={<FileSearchOutlined />}>选择 Excel 并分析</Button>
        </Upload>
        {analyzeSummary ? (
          <Typography.Text type={totalRecords > 0 ? 'success' : 'warning'}>{analyzeSummary}</Typography.Text>
        ) : null}
        <Button
          type="primary"
          icon={<CloudUploadOutlined />}
          loading={syncing}
          disabled={totalRecords === 0}
          onClick={() => void syncUpload()}
        >
          同步上传（阻塞至完成）
        </Button>
        <Typography.Link href="/api/excel/template" target="_blank" rel="noreferrer">
          下载 Excel 模板
        </Typography.Link>
      </Space>
    </Card>
  )
}
