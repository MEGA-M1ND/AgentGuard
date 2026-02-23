'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RefreshCw, Download, Calendar as CalendarIcon, ChevronDown, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'
import { DateRange } from 'react-day-picker'
import { toast } from 'sonner'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin-secret-key'

interface AuditLog {
  log_id: string
  agent_id: string
  timestamp: string
  action: string
  resource: string | null
  allowed: boolean
  result: string
  context: any
  metadata: any
}

export default function LogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  // Filters
  const [agentId, setAgentId] = useState('')
  const [action, setAction] = useState('')
  const [allowed, setAllowed] = useState<string>('all')
  const [limit, setLimit] = useState(100)
  const [dateRange, setDateRange] = useState<DateRange | undefined>()

  const fetchLogs = async () => {
    try {
      setLoading(true)
      setError(null)

      // Build query parameters
      const params = new URLSearchParams()
      if (agentId) params.append('agent_id', agentId)
      if (action) params.append('action', action)
      if (allowed !== 'all') params.append('allowed', allowed)
      params.append('limit', limit.toString())

      const response = await fetch(`${API_URL}/logs?${params.toString()}`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch logs: ${response.statusText}`)
      }

      const data = await response.json()
      setLogs(data)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to fetch logs'
      setError(errorMsg)
      toast.error('Failed to load logs', { description: errorMsg })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  const handleApplyFilters = () => {
    fetchLogs()
  }

  const handleClearFilters = () => {
    setAgentId('')
    setAction('')
    setAllowed('all')
    setLimit(100)
    setDateRange(undefined)
  }

  const toggleExpandRow = (logId: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(logId)) {
      newExpanded.delete(logId)
    } else {
      newExpanded.add(logId)
    }
    setExpandedRows(newExpanded)
  }

  const exportToCSV = () => {
    try {
      const headers = ['Timestamp', 'Agent ID', 'Action', 'Resource', 'Allowed', 'Result', 'Log ID']
      const rows = logs.map(log => [
        log.timestamp,
        log.agent_id,
        log.action,
        log.resource || '',
        log.allowed ? 'ALLOWED' : 'DENIED',
        log.result,
        log.log_id
      ])

      const csv = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n')

      const blob = new Blob([csv], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `agentguard-logs-${new Date().toISOString()}.csv`
      a.click()
      window.URL.revokeObjectURL(url)

      toast.success('Logs exported to CSV', {
        description: `Exported ${logs.length} log entries`
      })
    } catch (err) {
      toast.error('Failed to export CSV', {
        description: err instanceof Error ? err.message : 'Unknown error'
      })
    }
  }

  const exportToJSON = () => {
    try {
      const json = JSON.stringify(logs, null, 2)
      const blob = new Blob([json], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `agentguard-logs-${new Date().toISOString()}.json`
      a.click()
      window.URL.revokeObjectURL(url)

      toast.success('Logs exported to JSON', {
        description: `Exported ${logs.length} log entries`
      })
    } catch (err) {
      toast.error('Failed to export JSON', {
        description: err instanceof Error ? err.message : 'Unknown error'
      })
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Audit Logs</h1>
          <p className="text-gray-600 mt-1">View and filter all agent activity logs</p>
        </div>
        <Button variant="outline" onClick={fetchLogs}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filters Card */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Filter logs by agent, action, date range, or status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="agent-id">Agent ID</Label>
              <Input
                id="agent-id"
                placeholder="e.g., agt_abc123"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="action">Action</Label>
              <Input
                id="action"
                placeholder="e.g., read:file"
                value={action}
                onChange={(e) => setAction(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={allowed}
                onChange={(e) => setAllowed(e.target.value)}
              >
                <option value="all">All</option>
                <option value="true">Allowed</option>
                <option value="false">Denied</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="limit">Limit</Label>
              <select
                id="limit"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label>Date Range</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {dateRange?.from ? (
                      dateRange.to ? (
                        <>
                          {format(dateRange.from, "LLL dd, y")} -{" "}
                          {format(dateRange.to, "LLL dd, y")}
                        </>
                      ) : (
                        format(dateRange.from, "LLL dd, y")
                      )
                    ) : (
                      <span>Pick a date range</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    initialFocus
                    mode="range"
                    defaultMonth={dateRange?.from}
                    selected={dateRange}
                    onSelect={setDateRange}
                    numberOfMonths={2}
                  />
                </PopoverContent>
              </Popover>
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <Button onClick={handleApplyFilters}>
              Apply Filters
            </Button>
            <Button variant="outline" onClick={handleClearFilters}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {/* Logs Card */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Logs ({logs.length})</CardTitle>
              <CardDescription className="mt-1">
                Showing {logs.length} audit log entries
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={exportToCSV} disabled={logs.length === 0}>
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
              <Button variant="outline" size="sm" onClick={exportToJSON} disabled={logs.length === 0}>
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="text-center py-12">
              <p className="text-gray-500">Loading logs...</p>
            </div>
          )}
          {!loading && logs.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No logs found. Try adjusting your filters or submit some logs first.
            </div>
          )}
          {!loading && logs.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b-2">
                    <th className="p-3 text-left font-semibold text-gray-700"></th>
                    <th className="p-3 text-left font-semibold text-gray-700">Timestamp</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Agent ID</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Action</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Resource</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Status</th>
                    <th className="p-3 text-left font-semibold text-gray-700">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => {
                    const isExpanded = expandedRows.has(log.log_id)
                    return (
                      <>
                        <tr
                          key={log.log_id}
                          className={`border-b hover:bg-gray-50 cursor-pointer ${
                            index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                          }`}
                          onClick={() => toggleExpandRow(log.log_id)}
                        >
                          <td className="p-3">
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4 text-gray-500" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-gray-500" />
                            )}
                          </td>
                          <td className="p-3 font-mono text-xs">{formatTimestamp(log.timestamp)}</td>
                          <td className="p-3 font-mono text-xs">{log.agent_id.substring(0, 12)}...</td>
                          <td className="p-3 font-mono text-xs font-medium">{log.action}</td>
                          <td className="p-3 font-mono text-xs max-w-xs truncate">
                            {log.resource || '-'}
                          </td>
                          <td className="p-3">
                            <Badge variant={log.allowed ? 'success' : 'destructive'} className="text-xs">
                              {log.allowed ? 'ALLOWED' : 'DENIED'}
                            </Badge>
                          </td>
                          <td className="p-3">
                            <Badge
                              variant={log.result === 'success' ? 'default' : 'secondary'}
                              className="text-xs"
                            >
                              {log.result.toUpperCase()}
                            </Badge>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="border-b bg-blue-50">
                            <td colSpan={7} className="p-4">
                              <div className="space-y-3">
                                <div>
                                  <p className="text-xs font-semibold text-gray-700 mb-1">Log ID</p>
                                  <code className="text-xs bg-white px-2 py-1 rounded border">
                                    {log.log_id}
                                  </code>
                                </div>
                                <div>
                                  <p className="text-xs font-semibold text-gray-700 mb-1">Full Agent ID</p>
                                  <code className="text-xs bg-white px-2 py-1 rounded border">
                                    {log.agent_id}
                                  </code>
                                </div>
                                {log.resource && (
                                  <div>
                                    <p className="text-xs font-semibold text-gray-700 mb-1">Full Resource</p>
                                    <code className="text-xs bg-white px-2 py-1 rounded border break-all">
                                      {log.resource}
                                    </code>
                                  </div>
                                )}
                                {log.context && Object.keys(log.context).length > 0 && (
                                  <div>
                                    <p className="text-xs font-semibold text-gray-700 mb-1">Context</p>
                                    <pre className="text-xs bg-white px-3 py-2 rounded border overflow-x-auto">
                                      {JSON.stringify(log.context, null, 2)}
                                    </pre>
                                  </div>
                                )}
                                {log.metadata && Object.keys(log.metadata).length > 0 && (
                                  <div>
                                    <p className="text-xs font-semibold text-gray-700 mb-1">Metadata</p>
                                    <pre className="text-xs bg-white px-3 py-2 rounded border overflow-x-auto">
                                      {JSON.stringify(log.metadata, null, 2)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
