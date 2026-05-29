import { InboxOutlined, PlusOutlined, ReloadOutlined, RocketOutlined, SaveOutlined } from '@ant-design/icons'
import { Button, Card, Collapse, Form, Input, Modal, Select, Space, Table, Tag, Typography, Upload, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadProps } from 'antd/es/upload/interface'
import { useEffect, useState } from 'react'

import { ExcelSyncCard } from '../components/ExcelSyncCard'
import { api } from '../services/api'
import { getApiErrorMessage } from '../utils/apiError'

interface TaskRow {
  id: string
  type: string
  status: string
  created_at: string
  updated_at: string
  created_by: string
  error_code?: string | null
}

export function TasksPage() {
  const [tasks, setTasks] = useState<TaskRow[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  // 页面级共享配置：学号 / 平台 Token / Cookie 仅此一份
  const [studentId, setStudentId] = useState('')
  const [platformToken, setPlatformToken] = useState('')
  const [cookieString, setCookieString] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/tasks')
      if (data.success) {
        setTasks((data.data.tasks as TaskRow[]) ?? [])
      }
    } catch {
      message.error('加载任务失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const saveCookie = async () => {
    if (!studentId.trim()) {
      message.warning('请先填写学号')
      return
    }
    if (!cookieString.trim()) {
      message.warning('请先粘贴浏览器 Cookie')
      return
    }
    try {
      const { data } = await api.post('/save_cookie', {
        student_id: studentId.trim(),
        cookie_string: cookieString.trim(),
        token: platformToken.trim(),
      })
      if (data.success) {
        message.success(data.message ?? '已保存')
      } else {
        message.error(data.message ?? '保存失败')
      }
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '保存失败'))
    }
  }

  const columns: ColumnsType<TaskRow> = [
    { title: '任务 ID', dataIndex: 'id', width: 280, ellipsis: true },
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
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            type="primary"
            icon={<RocketOutlined />}
            onClick={() => void runTask(record.id)}
          >
            执行
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => void retryTask(record.id)}>
            重试
          </Button>
        </Space>
      ),
    },
  ]

  const runTask = async (taskId: string) => {
    try {
      await api.post(`/tasks/${taskId}/run`)
      message.success('任务已排队执行')
      await load()
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '执行失败'))
    }
  }

  const retryTask = async (taskId: string) => {
    try {
      await api.post(`/tasks/${taskId}/retry`)
      message.success('已排队重试')
      await load()
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '重试失败'))
    }
  }

  const handleCreate = async () => {
    const values = await form.validateFields()
    const payload: Record<string, unknown> = {
      kind: 'single',
      note: (values.note as string) ?? '',
    }
    // 学号 / Token 复用页面共享配置
    if (studentId.trim()) payload.student_id = studentId.trim()
    if (platformToken.trim()) payload.fjcpc_token = platformToken.trim()
    if (values.report_date) payload.report_date = values.report_date as string
    const work = (values.work as string | undefined)?.trim()
    const achievement = (values.achievement as string | undefined)?.trim()
    const problem = (values.problem as string | undefined)?.trim()
    if (work || achievement || problem) {
      payload.report = { work: work ?? '', achievement: achievement ?? '', problem: problem ?? '' }
    }
    try {
      await api.post('/tasks', {
        report_type: values.report_type,
        payload,
      })
      message.success('任务已创建')
      setModalOpen(false)
      form.resetFields()
      await load()
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '创建失败'))
    }
  }

  const excelUploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    showUploadList: false,
    accept: '.xlsx,.xlsm,.xls',
    beforeUpload: (file) => {
      void (async () => {
        if (!studentId.trim() || !platformToken.trim()) {
          message.warning('请先在上方填写学号与平台 Token')
          return
        }
        const formData = new FormData()
        formData.append('file', file)
        formData.append('student_id', studentId.trim())
        formData.append('fjcpc_token', platformToken.trim())
        try {
          const { data } = await api.post('/uploads/excel-submit', formData)
          if (data.success) {
            const taskId = data.data?.task_id as string | undefined
            message.success(taskId ? `已创建批量任务 ${taskId}` : '已创建批量上传任务')
            await load()
          } else {
            message.error(data.message ?? '提交失败')
          }
        } catch (error: unknown) {
          message.error(getApiErrorMessage(error, 'Excel 提交失败'))
        }
      })()
      return false
    },
  }

  return (
    <div>
      <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
        <div>
          <Typography.Title level={4} style={{ marginTop: 0 }}>
            表格识别上传
          </Typography.Title>
          <Typography.Paragraph type="secondary">
            支持 Excel 文件分析、同步/异步批量上传至实习平台；亦可创建单条日报/周/月任务。学号与平台 token 留空则 dry-run。
          </Typography.Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void load()}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            新建任务
          </Button>
        </Space>
      </Space>

      <Card title="上传配置（学号 / 平台 Token / Cookie，全页共用）" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space wrap>
            <Input
              style={{ width: 220 }}
              placeholder="学号 student_id"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
            />
            <Input.Password
              style={{ width: 300 }}
              placeholder="平台 Token（fjcpc_token）"
              value={platformToken}
              onChange={(e) => setPlatformToken(e.target.value)}
            />
          </Space>
          <Collapse
            size="small"
            items={[
              {
                key: 'cookie',
                label: '浏览器 Cookie（上传前请先配置并保存，否则上游认证会失败）',
                children: (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Input.TextArea
                      rows={3}
                      placeholder="从浏览器开发者工具复制完整 Cookie（含 PHPSESSID、sdp_app_session 等）"
                      value={cookieString}
                      onChange={(e) => setCookieString(e.target.value)}
                    />
                    <Button icon={<SaveOutlined />} onClick={() => void saveCookie()}>
                      保存 Cookie 到服务端
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </Space>
      </Card>

      <ExcelSyncCard studentId={studentId} platformToken={platformToken} />

      <Typography.Title level={5}>Excel 批量上传（异步任务）</Typography.Title>
      <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }} size="middle">
        <Upload.Dragger {...excelUploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽 Excel 到此处</p>
          <p className="ant-upload-hint">使用上方共享配置的学号与 Token，提交后自动排队执行，可在下方列表查看结果</p>
        </Upload.Dragger>
      </Space>

      <Table<TaskRow>
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={tasks}
        pagination={{ pageSize: 8 }}
      />

      <Modal
        title="新建上传任务"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleCreate()}
        okText="创建"
        width={560}
      >
        <Typography.Paragraph type="secondary">
          学号与平台 Token 使用页面顶部的共享配置，此处只需填写报告内容。
        </Typography.Paragraph>
        <Form form={form} layout="vertical" initialValues={{ report_type: 'day' }}>
          <Form.Item label="报表类型" name="report_type" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '日报', value: 'day' },
                { label: '周报', value: 'week' },
                { label: '月报', value: 'month' },
              ]}
            />
          </Form.Item>
          <Form.Item label="报告日期（YYYY-MM-DD）" name="report_date">
            <Input placeholder="单条上传时填写，如 2025-01-13" />
          </Form.Item>
          <Form.Item label="实习工作具体情况" name="work">
            <Input.TextArea rows={2} placeholder="单条上传时填写（与 Excel 列一致）" />
          </Form.Item>
          <Form.Item label="主要收获及工作成绩" name="achievement">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="问题及需要老师指导" name="problem">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="备注" name="note">
            <Input.TextArea rows={2} placeholder="payload.note，可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
