import { Card, Col, Row, Statistic, Typography, message } from 'antd'
import ReactECharts from 'echarts-for-react'
import { useEffect, useState } from 'react'

import { api } from '../services/api'

interface Summary {
  total: number
  success: number
  failed: number
  pending: number
  success_rate: number
  top_errors: { code: string; count: number }[]
}

export function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null)

  const load = async () => {
    try {
      const { data } = await api.get('/monitor/summary')
      if (data.success) {
        setSummary(data.data as Summary)
      }
    } catch {
      message.error('加载看板数据失败')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const pieOption =
    summary && summary.total > 0
      ? {
          tooltip: { trigger: 'item' },
          legend: { bottom: 0 },
          series: [
            {
              type: 'pie',
              radius: ['42%', '68%'],
              data: [
                { value: summary.success, name: '成功' },
                { value: summary.failed, name: '失败' },
                { value: summary.pending, name: '进行中/排队' },
              ],
            },
          ],
        }
      : null

  return (
    <div>
      <Typography.Title level={4}>状态看板</Typography.Title>
      <Typography.Paragraph type="secondary">任务成功率与失败原因统计。</Typography.Paragraph>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="任务总数（窗口）" value={summary?.total ?? 0} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic
              title="成功率"
              value={(summary?.success_rate ?? 0) * 100}
              precision={1}
              suffix="%"
            />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="失败任务" value={summary?.failed ?? 0} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="进行中" value={summary?.pending ?? 0} />
          </Card>
        </Col>
      </Row>

      <Card title="任务结果分布" style={{ marginTop: 16 }}>
        {pieOption ? (
          <ReactECharts option={pieOption} style={{ height: 320 }} />
        ) : (
          <Typography.Text type="secondary">暂无任务数据</Typography.Text>
        )}
      </Card>

      <Card title="失败原因 TopN" style={{ marginTop: 16 }}>
        {(summary?.top_errors ?? []).length === 0 ? (
          <Typography.Text type="secondary">暂无失败统计</Typography.Text>
        ) : (
          <ul>
            {summary?.top_errors.map((item) => (
              <li key={item.code}>
                <Typography.Text code>{item.code}</Typography.Text> · {item.count} 次
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
