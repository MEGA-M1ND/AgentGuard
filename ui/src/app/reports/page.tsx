'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Download, BarChart3, ShieldCheck, ShieldX, Clock } from 'lucide-react'
import { toast } from 'sonner'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin-secret-key'

interface Overview {
  total_actions: number
  allowed: number
  denied: number
  allow_rate: number
  deny_rate: number
}

interface ApprovalsStats {
  total: number
  pending: number
  approved: number
  denied: number
  approval_rate: number
}

interface TopAgent {
  agent_id: string
  agent_name: string
  total_actions: number
  allowed: number
  denied: number
}

interface DeniedAction {
  action: string
  count: number
}

interface DailyPoint {
  date: string
  total: number
  allowed: number
  denied: number
}

interface Report {
  period_days: number
  generated_at: string
  overview: Overview
  approvals: ApprovalsStats
  top_agents: TopAgent[]
  top_denied_actions: DeniedAction[]
  daily_breakdown: DailyPoint[]
}

const PERIOD_OPTIONS = [
  { label: '7 days',  value: 7  },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
]

function StatCard({
  title, value, sub, icon: Icon, color,
}: {
  title: string
  value: string | number
  sub?: string
  icon: React.ElementType
  color: string
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
            {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
          </div>
          <div className={`p-3 rounded-lg bg-gray-50`}>
            <Icon className={`h-5 w-5 ${color}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function MiniBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-8 text-right">{value}</span>
    </div>
  )
}

function DailyChart({ data }: { data: DailyPoint[] }) {
  if (!data.length) return null
  const maxVal = Math.max(...data.map(d => d.total), 1)
  return (
    <div className="flex items-end gap-1 h-24">
      {data.map((d) => {
        const heightPct = d.total > 0 ? Math.round((d.total / maxVal) * 100) : 0
        const allowedPct = d.total > 0 ? Math.round((d.allowed / d.total) * 100) : 0
        const dateLabel = d.date.slice(5) // MM-DD
        return (
          <div
            key={d.date}
            className="flex-1 flex flex-col items-center group"
            title={`${d.date}: ${d.total} total, ${d.allowed} allowed, ${d.denied} denied`}
          >
            <div className="relative w-full flex flex-col justify-end" style={{ height: '80px' }}>
              {d.total > 0 && (
                <div
                  className="w-full rounded-sm overflow-hidden"
                  style={{ height: `${heightPct}%` }}
                >
                  <div
                    className="w-full bg-green-400"
                    style={{ height: `${allowedPct}%` }}
                  />
                  <div
                    className="w-full bg-red-400"
                    style={{ height: `${100 - allowedPct}%` }}
                  />
                </div>
              )}
              {d.total === 0 && (
                <div className="w-full bg-gray-100 rounded-sm" style={{ height: '4px' }} />
              )}
            </div>
            <span className="text-xs text-gray-400 mt-1 hidden md:block" style={{ fontSize: '9px' }}>
              {dateLabel}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function ReportsPage() {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  const fetchReport = async (periodDays = days) => {
    try {
      setLoading(true)
      setError(null)
      const res = await fetch(`${API_URL}/reports/summary?days=${periodDays}`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY },
      })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      setReport(await res.json())
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load report'
      setError(msg)
      toast.error('Failed to load report', { description: msg })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchReport(days) }, [])

  const handlePeriodChange = (newDays: number) => {
    setDays(newDays)
    fetchReport(newDays)
  }

  const exportJSON = () => {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `agentguard-compliance-report-${report.generated_at.slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Report exported', { description: `${report.period_days}-day compliance report saved.` })
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Compliance Reports</h1>
          <p className="text-gray-600 mt-1">Activity summary, policy effectiveness, and audit metrics</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Period selector */}
          <div className="flex bg-gray-100 rounded-lg p-1 gap-1">
            {PERIOD_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => handlePeriodChange(opt.value)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  days === opt.value
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <Button variant="outline" onClick={() => fetchReport(days)} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" onClick={exportJSON} disabled={!report}>
            <Download className="h-4 w-4 mr-2" />
            Export JSON
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-16">
          <p className="text-gray-500">Generating report…</p>
        </div>
      )}

      {!loading && report && (
        <div className="space-y-6">
          {/* Generated-at info */}
          <p className="text-xs text-gray-400">
            Report covers the last {report.period_days} days &middot; Generated{' '}
            {new Date(report.generated_at).toLocaleString()}
          </p>

          {/* Summary stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              title="Total Actions"
              value={report.overview.total_actions.toLocaleString()}
              sub={`Last ${report.period_days} days`}
              icon={BarChart3}
              color="text-blue-600"
            />
            <StatCard
              title="Allowed"
              value={`${report.overview.allow_rate}%`}
              sub={`${report.overview.allowed.toLocaleString()} actions`}
              icon={ShieldCheck}
              color="text-green-600"
            />
            <StatCard
              title="Denied"
              value={`${report.overview.deny_rate}%`}
              sub={`${report.overview.denied.toLocaleString()} actions`}
              icon={ShieldX}
              color="text-red-600"
            />
            <StatCard
              title="Pending Approvals"
              value={report.approvals.pending}
              sub={`${report.approvals.total} total requests`}
              icon={Clock}
              color={report.approvals.pending > 0 ? 'text-amber-600' : 'text-gray-500'}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Daily activity chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Daily Activity</CardTitle>
                <CardDescription>
                  Last {report.daily_breakdown.length} days — green = allowed, red = denied
                </CardDescription>
              </CardHeader>
              <CardContent>
                {report.daily_breakdown.every(d => d.total === 0) ? (
                  <p className="text-sm text-gray-400 text-center py-8">No activity in this period.</p>
                ) : (
                  <DailyChart data={report.daily_breakdown} />
                )}
              </CardContent>
            </Card>

            {/* Approvals funnel */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Approval Workflow</CardTitle>
                <CardDescription>Human-in-the-loop decision breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                {report.approvals.total === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-8">
                    No approval requests in this period.
                  </p>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-3 gap-3 text-center">
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                        <p className="text-2xl font-bold text-amber-700">{report.approvals.pending}</p>
                        <p className="text-xs text-amber-600 mt-1">Pending</p>
                      </div>
                      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                        <p className="text-2xl font-bold text-green-700">{report.approvals.approved}</p>
                        <p className="text-xs text-green-600 mt-1">Approved</p>
                      </div>
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <p className="text-2xl font-bold text-red-700">{report.approvals.denied}</p>
                        <p className="text-xs text-red-600 mt-1">Denied</p>
                      </div>
                    </div>
                    {(report.approvals.approved + report.approvals.denied) > 0 && (
                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-xs text-gray-500">Approval rate:</span>
                        <div className="flex-1 bg-gray-100 rounded-full h-2">
                          <div
                            className="h-2 rounded-full bg-green-500"
                            style={{ width: `${report.approvals.approval_rate}%` }}
                          />
                        </div>
                        <span className="text-xs font-semibold text-green-700">
                          {report.approvals.approval_rate}%
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Top agents */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Agents by Activity</CardTitle>
                <CardDescription>Most active agents and their allow/deny breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                {report.top_agents.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-6">No agent activity recorded.</p>
                ) : (
                  <div className="space-y-3">
                    {report.top_agents.map((agent) => (
                      <div key={agent.agent_id}>
                        <div className="flex justify-between items-center mb-1">
                          <div>
                            <span className="text-sm font-medium">{agent.agent_name}</span>
                            <code className="ml-2 text-xs text-gray-400">{agent.agent_id.slice(0, 12)}…</code>
                          </div>
                          <span className="text-xs text-gray-500">{agent.total_actions} actions</span>
                        </div>
                        <div className="flex gap-1 h-2">
                          {agent.total_actions > 0 && (
                            <>
                              <div
                                className="bg-green-400 rounded-l-full"
                                style={{ width: `${(agent.allowed / agent.total_actions) * 100}%` }}
                                title={`Allowed: ${agent.allowed}`}
                              />
                              <div
                                className="bg-red-400 rounded-r-full"
                                style={{ width: `${(agent.denied / agent.total_actions) * 100}%` }}
                                title={`Denied: ${agent.denied}`}
                              />
                            </>
                          )}
                        </div>
                        <div className="flex gap-3 mt-0.5">
                          <span className="text-xs text-green-600">{agent.allowed} allowed</span>
                          <span className="text-xs text-red-600">{agent.denied} denied</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top denied actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Denied Actions</CardTitle>
                <CardDescription>Most frequently blocked actions — review policy coverage</CardDescription>
              </CardHeader>
              <CardContent>
                {report.top_denied_actions.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-6">No denied actions in this period.</p>
                ) : (
                  <div className="space-y-2">
                    {report.top_denied_actions.map((item, idx) => {
                      const max = report.top_denied_actions[0]?.count ?? 1
                      return (
                        <div key={item.action} className="flex items-center gap-3">
                          <span className="text-xs text-gray-400 w-4">{idx + 1}</span>
                          <code className="text-xs font-mono text-red-700 w-36 truncate" title={item.action}>
                            {item.action}
                          </code>
                          <div className="flex-1">
                            <MiniBar value={item.count} max={max} color="bg-red-400" />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Compliance summary strip */}
          <Card className="bg-gray-50 border-gray-200">
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4 items-center">
                <span className="text-sm font-semibold text-gray-700">Compliance Summary:</span>
                <Badge variant={report.overview.allow_rate >= 80 ? 'success' : 'warning'}>
                  {report.overview.allow_rate}% Allow Rate
                </Badge>
                <Badge variant={report.approvals.pending === 0 ? 'success' : 'warning'}>
                  {report.approvals.pending === 0 ? '✓ No Pending Approvals' : `${report.approvals.pending} Pending`}
                </Badge>
                <Badge variant="default">
                  {report.top_agents.length} Active Agents
                </Badge>
                {report.top_denied_actions.length > 0 && (
                  <Badge variant="secondary">
                    Top Blocked: {report.top_denied_actions[0].action}
                  </Badge>
                )}
                <span className="ml-auto text-xs text-gray-400">
                  Exported: <button className="underline hover:text-gray-600" onClick={exportJSON}>Download JSON</button>
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
