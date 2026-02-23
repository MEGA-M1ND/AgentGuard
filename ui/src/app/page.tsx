'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Users, Shield, CheckCircle2, XCircle, Activity, TrendingUp, Plus, RefreshCw } from 'lucide-react'
import Link from 'next/link'
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin-secret-key'

interface Agent {
  agent_id: string
  name: string
  is_active: boolean
}

interface AuditLog {
  log_id: string
  agent_id: string
  timestamp: string
  action: string
  allowed: boolean
  result: string
}

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [allLogs, setAllLogs] = useState<AuditLog[]>([])
  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      // Fetch agents
      const agentsRes = await fetch(`${API_URL}/agents`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY }
      })
      if (agentsRes.ok) {
        const agentsData = await agentsRes.json()
        setAgents(agentsData)
      }

      // Fetch more logs for charts (500 for analysis)
      const allLogsRes = await fetch(`${API_URL}/logs?limit=500`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY }
      })
      if (allLogsRes.ok) {
        const logsData = await allLogsRes.json()
        setAllLogs(logsData)
        setRecentLogs(logsData.slice(0, 10))
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const totalAgents = agents.length
  const activeAgents = agents.filter(a => a.is_active).length
  const totalLogs = allLogs.length
  const allowedLogs = allLogs.filter(l => l.allowed).length
  const deniedLogs = allLogs.filter(l => !l.allowed).length
  const allowedRatio = totalLogs > 0 ? Math.round((allowedLogs / totalLogs) * 100) : 0

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  // Prepare timeline data (actions over time)
  const getTimelineData = () => {
    const timelineMap: Record<string, { allowed: number; denied: number }> = {}

    allLogs.forEach(log => {
      const date = new Date(log.timestamp)
      const hourKey = `${date.getMonth()+1}/${date.getDate()} ${date.getHours()}:00`

      if (!timelineMap[hourKey]) {
        timelineMap[hourKey] = { allowed: 0, denied: 0 }
      }

      if (log.allowed) {
        timelineMap[hourKey].allowed++
      } else {
        timelineMap[hourKey].denied++
      }
    })

    return Object.entries(timelineMap)
      .map(([time, data]) => ({ time, ...data }))
      .slice(-24) // Last 24 time periods
  }

  // Prepare top actions data
  const getTopActionsData = () => {
    const actionMap: Record<string, number> = {}

    allLogs.forEach(log => {
      actionMap[log.action] = (actionMap[log.action] || 0) + 1
    })

    return Object.entries(actionMap)
      .map(([action, count]) => ({ action, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10) // Top 10 actions
  }

  // Prepare agent activity data (pie chart)
  const getAgentActivityData = () => {
    const agentMap: Record<string, number> = {}

    allLogs.forEach(log => {
      const agent = agents.find(a => a.agent_id === log.agent_id)
      const agentName = agent ? agent.name : log.agent_id.substring(0, 8)
      agentMap[agentName] = (agentMap[agentName] || 0) + 1
    })

    return Object.entries(agentMap)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6) // Top 6 agents
  }

  const timelineData = getTimelineData()
  const topActionsData = getTopActionsData()
  const agentActivityData = getAgentActivityData()

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Overview of your AI agent governance platform</p>
        </div>
        <Button variant="outline" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalAgents}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {activeAgents} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Logs</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalLogs}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Recent activity
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Allowed Actions</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{allowedLogs}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {allowedRatio}% success rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Denied Actions</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{deniedLogs}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Policy blocks
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks to manage your AI agents</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Link href="/agents">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Agent
              </Button>
            </Link>
            <Link href="/policies">
              <Button variant="outline">
                <Shield className="h-4 w-4 mr-2" />
                Manage Policies
              </Button>
            </Link>
            <Link href="/logs">
              <Button variant="outline">
                <Activity className="h-4 w-4 mr-2" />
                View Logs
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Charts Section */}
      {!loading && totalLogs > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Activity Timeline */}
          <Card>
            <CardHeader>
              <CardTitle>Activity Timeline</CardTitle>
              <CardDescription>Actions over time (last 24 periods)</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={timelineData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" style={{ fontSize: '12px' }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="allowed" stroke="#10b981" strokeWidth={2} name="Allowed" />
                  <Line type="monotone" dataKey="denied" stroke="#ef4444" strokeWidth={2} name="Denied" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Top Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Top Actions</CardTitle>
              <CardDescription>Most frequently used actions</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topActionsData} layout="horizontal">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="action" type="category" width={120} style={{ fontSize: '11px' }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" name="Count" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Agent Activity Distribution */}
          <Card>
            <CardHeader>
              <CardTitle>Agent Activity Distribution</CardTitle>
              <CardDescription>Actions by agent</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={agentActivityData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {agentActivityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Success Rate Over Time */}
          <Card>
            <CardHeader>
              <CardTitle>Success Metrics</CardTitle>
              <CardDescription>Overall system performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm font-medium">Allow Rate</span>
                    <span className="text-sm font-medium">{allowedRatio}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-green-500 h-3 rounded-full transition-all"
                      style={{ width: `${allowedRatio}%` }}
                    ></div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-4">
                  <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                    <p className="text-xs text-green-700 font-medium mb-1">Total Allowed</p>
                    <p className="text-2xl font-bold text-green-700">{allowedLogs}</p>
                  </div>
                  <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                    <p className="text-xs text-red-700 font-medium mb-1">Total Denied</p>
                    <p className="text-2xl font-bold text-red-700">{deniedLogs}</p>
                  </div>
                </div>
                <div className="pt-4 border-t">
                  <p className="text-xs text-gray-500 mb-3 font-medium">Active Agents</p>
                  <div className="flex gap-2">
                    {agents.slice(0, 5).map((agent) => (
                      <div
                        key={agent.agent_id}
                        className="flex-1 bg-blue-50 p-2 rounded text-center border border-blue-200"
                      >
                        <p className="text-xs font-medium text-blue-900 truncate">{agent.name}</p>
                        <Badge
                          variant={agent.is_active ? 'success' : 'secondary'}
                          className="text-xs mt-1"
                        >
                          {agent.is_active ? '●' : '○'}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Agents</CardTitle>
            <CardDescription>Your latest AI agents</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-gray-500">Loading...</p>
            ) : agents.length === 0 ? (
              <div className="text-center py-6">
                <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500 mb-3">No agents yet</p>
                <Link href="/agents">
                  <Button size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Your First Agent
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {agents.slice(0, 5).map((agent) => (
                  <div key={agent.agent_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Users className="h-5 w-5 text-gray-400" />
                      <div>
                        <p className="font-medium text-sm">{agent.name}</p>
                        <p className="text-xs text-gray-500">{agent.agent_id}</p>
                      </div>
                    </div>
                    <Badge variant={agent.is_active ? 'success' : 'secondary'}>
                      {agent.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest audit log entries</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-gray-500">Loading...</p>
            ) : recentLogs.length === 0 ? (
              <div className="text-center py-6">
                <Activity className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">No activity yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentLogs.slice(0, 5).map((log) => (
                  <div key={log.log_id} className="flex items-start justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <code className="text-xs bg-white px-2 py-0.5 rounded border">
                          {log.action}
                        </code>
                        <Badge variant={log.allowed ? 'success' : 'destructive'} className="text-xs">
                          {log.allowed ? 'ALLOWED' : 'DENIED'}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500">
                        {formatTimestamp(log.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
