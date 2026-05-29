import { SendOutlined } from '@ant-design/icons'
import { Button, Card, Collapse, Form, Input, Segmented, Space, Typography, message } from 'antd'
import { useState } from 'react'

import { api } from '../services/api'
import { getApiErrorMessage } from '../utils/apiError'

type ReportKind = 'day' | 'week' | 'month'

const uploadPath: Record<ReportKind, string> = {
  day: '/upload/day',
  week: '/upload/week',
  month: '/upload/month',
}

export function TextUploadPage() {
  const [kind, setKind] = useState<ReportKind>('day')
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [cookieForm] = Form.useForm()

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const content = String(values.content ?? '').trim()
    const start_date = String(values.start_date ?? '').trim()
    const student_id = String(values.student_id ?? '').trim()
    const token = String(values.token ?? '').trim()
    if (!content || !start_date) {
      message.warning('请填写正文与起始日期')
      return
    }
    setLoading(true)
    try {
      const { data, status } = await api.post(uploadPath[kind], {
        content,
        start_date,
        student_id,
        token,
      })
      if (data.success === false || (typeof data.message === 'string' && status >= 400)) {
        message.error(data.message ?? '上传失败')
        return
      }
      message.success(typeof data.message === 'string' ? data.message : '已提交')
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, '上传失败'))
    } finally {
      setLoading(false)
    }
  }

  const saveCookie = async () => {
    const v = await cookieForm.validateFields()
    try {
      const { data } = await api.post('/save_cookie', {
        student_id: String(v.student_id).trim(),
        cookie_string: String(v.cookie_string ?? ''),
        token: String(v.token ?? ''),
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

  return (
    <div>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        文本批量上传
      </Typography.Title>
      <Typography.Paragraph type="secondary">
        对应旧版 TXT 页面：按三行一组解析实习报告正文，与兼容接口{' '}
        <Typography.Text code>/api/upload/day|week|month</Typography.Text> 一致。
      </Typography.Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Typography.Text strong>报表类型</Typography.Text>
            <div style={{ marginTop: 8 }}>
              <Segmented
                value={kind}
                onChange={(v) => setKind(v as ReportKind)}
                options={[
                  { label: '日报', value: 'day' },
                  { label: '周报', value: 'week' },
                  { label: '月报', value: 'month' },
                ]}
              />
            </div>
          </div>
          <Form form={form} layout="vertical" style={{ maxWidth: 960 }}>
            <Form.Item
              label="学号（student_id）"
              name="student_id"
              rules={[{ required: true, message: '请填写学号' }]}
            >
              <Input placeholder="实习平台学号" />
            </Form.Item>
            <Form.Item
              label="平台 Token"
              name="token"
              rules={[{ required: true, message: '请填写平台 API Token' }]}
            >
              <Input.Password placeholder="与旧版一致，用于 Cookie/Authorization" />
            </Form.Item>
            <Form.Item
              label="起始日期（start_date）"
              name="start_date"
              rules={[{ required: true, message: '请填写起始日期' }]}
              extra="格式与旧版一致，如 2025-01-01"
            >
              <Input placeholder="YYYY-MM-DD" />
            </Form.Item>
            <Form.Item
              label="正文（多行，三行一组为一条报告）"
              name="content"
              rules={[{ required: true, message: '请粘贴正文' }]}
            >
              <Input.TextArea rows={14} placeholder="粘贴实习报告文本…" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" icon={<SendOutlined />} loading={loading} onClick={() => void handleSubmit()}>
                提交上传
              </Button>
            </Form.Item>
          </Form>
        </Space>
      </Card>

      <Collapse
        items={[
          {
            key: 'cookie',
            label: '保存浏览器 Cookie（可选，与旧版 save_cookie 一致）',
            children: (
              <Form form={cookieForm} layout="vertical" style={{ maxWidth: 640 }}>
                <Form.Item label="学号" name="student_id" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item label="Cookie 字符串" name="cookie_string">
                  <Input.TextArea rows={3} placeholder="从浏览器开发者工具复制完整 Cookie" />
                </Form.Item>
                <Form.Item label="关联 Token" name="token">
                  <Input.Password placeholder="可与上方平台 Token 相同" />
                </Form.Item>
                <Button type="default" onClick={() => void saveCookie()}>
                  保存到服务端
                </Button>
              </Form>
            ),
          },
        ]}
      />
    </div>
  )
}
