'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { CheckCircle2, XCircle, Clock, RefreshCw, ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin-secret-key'

interface ApprovalRequest {
  approval_id: string
  agent_id: string
  agent_name: string | null
  status: 'pending' | 'approved' | 'denied'
  action: string
  resource: string | null
  context: Record<string, unknown> | null
  created_at: string
  decision_at: string | null
  decision_by: string | null
  decision_reason: string | null
}

interface ApprovalListResponse {
  items: ApprovalRequest[]
  total: number
  pending_count: number
}

type StatusFilter = 'all' | 'pending' | 'approved' | 'denied'

export default function ApprovalsPage() {
  const [data, setData] = useState<ApprovalListResponse>({ items: [], total: 0, pending_count: 0 })
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending')
  const [agentFilter, setAgentFilter] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Decision dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogApproval, setDialogApproval] = useState<ApprovalRequest | null>(null)
  const [dialogAction, setDialogAction] = useState<'approve' | 'deny'>('approve')
  const [dialogReason, setDialogReason] = useState('')
  const [dialogLoading, setDialogLoading] = useState(false)

  const fetchApprovals = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.set('status', statusFilter)
      if (agentFilter.trim()) params.set('agent_id', agentFilter.trim())
      params.set('limit', '100')

      const res = await fetch(`${API_URL}/approvals?${params}`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY },
      })
      if (res.ok) {
        setData(await res.json())
      }
    } catch {
      // silently ignore during auto-refresh
    } finally {
      setLoading(false)
    }
  }, [statusFilter, agentFilter])

  useEffect(() => {
    setLoading(true)
    fetchApprovals()
  }, [fetchApprovals])

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    if (autoRefresh) {
      timerRef.current = setInterval(fetchApprovals, 3000)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [autoRefresh, fetchApprovals])

  const openDecisionDialog = (approval: ApprovalRequest, action: 'approve' | 'deny') => {
    setDialogApproval(approval)
    setDialogAction(action)
    setDialogReason('')
    setDialogOpen(true)
  }

  const submitDecision = async () => {
    if (!dialogApproval) return
    setDialogLoading(true)

    try {
      const res = await fetch(`${API_URL}/approvals/${dialogApproval.approval_id}/${dialogAction}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-ADMIN-KEY': ADMIN_API_KEY },
        body: JSON.stringify({ reason: dialogReason }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Failed')
      }

      toast.success(
        dialogAction === 'approve' ? 'Request approved' : 'Request denied',
        { description: `${dialogApproval.action} — the agent will be notified on next poll.` }
      )
      setDialogOpen(false)
      fetchApprovals()
    } catch (err) {
      toast.error('Decision failed', { description: err instanceof Error ? err.message : String(err) })
    } finally {
      setDialogLoading(false)
    }
  }

  const statusBadge = (s: string) => {
    if (s === 'pending') return <Badge className="bg-amber-100 text-amber-800 border border-amber-300 text-xs"><Clock className="h-3 w-3 mr-1" />PENDING</Badge>
    if (s === 'approved') return <Badge variant="success" className="text-xs"><CheckCircle2 className="h-3 w-3 mr-1" />APPROVED</Badge>
    return <Badge variant="destructive" className="text-xs"><XCircle className="h-3 w-3 mr-1" />DENIED</Badge>
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const timeSince = (iso: string) => {
    const secs = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
    if (secs < 60) return `${secs}s ago`
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
    return `${Math.floor(secs / 3600)}h ago`
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">Approvals</h1>
            {data.pending_count > 0 && (
              <span className="inline-flex items-center justify-center w-7 h-7 text-sm font-bold bg-amber-500 text-white rounded-full animate-pulse">
                {data.pending_count}
              </span>
            )}
          </div>
          <p className="text-gray-600 mt-1">Human-in-the-loop review queue for agent actions</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-full border transition-colors ${
              autoRefresh
                ? 'bg-green-50 border-green-300 text-green-700'
                : 'bg-gray-50 border-gray-300 text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
            {autoRefresh ? 'Live' : 'Paused'}
          </button>
          <Button variant="outline" onClick={fetchApprovals}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pending</p>
                <p className="text-2xl font-bold text-amber-600">{data.pending_count}</p>
              </div>
              <Clock className="h-8 w-8 text-amber-400" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total shown</p>
                <p className="text-2xl font-bold text-gray-900">{data.total}</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-gray-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Filter</p>
                <p className="text-sm font-medium text-gray-700 capitalize mt-1">{statusFilter === 'all' ? 'All statuses' : statusFilter}</p>
              </div>
              <AlertTriangle className="h-8 w-8 text-gray-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
          {(['pending', 'approved', 'denied', 'all'] as StatusFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-4 py-2 capitalize transition-colors ${
                statusFilter === s ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <Input
          placeholder="Filter by Agent ID..."
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="max-w-xs text-sm"
        />
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading approvals...</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && data.items.length === 0 && (
        <Card>
          <CardContent className="text-center py-16">
            <CheckCircle2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 font-medium mb-1">
              {statusFilter === 'pending' ? 'No pending approvals' : 'No approvals found'}
            </p>
            <p className="text-sm text-gray-400">
              {statusFilter === 'pending'
                ? 'Agents will appear here when they try an action marked require_approval in their policy.'
                : 'Try changing the filter above.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Approvals list */}
      {!loading && data.items.length > 0 && (
        <div className="space-y-2">
          {data.items.map((approval) => {
            const isExpanded = expandedId === approval.approval_id
            const isPending = approval.status === 'pending'

            return (
              <Card
                key={approval.approval_id}
                className={isPending ? 'border-amber-300 bg-amber-50/30' : ''}
              >
                <CardContent className="p-0">
                  {/* Main row */}
                  <div className="flex items-center gap-4 p-4">
                    {/* Expand toggle */}
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : approval.approval_id)}
                      className="text-gray-400 hover:text-gray-600 shrink-0"
                    >
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>

                    {/* Status badge */}
                    <div className="shrink-0">{statusBadge(approval.status)}</div>

                    {/* Agent */}
                    <div className="min-w-0 w-40 shrink-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{approval.agent_name ?? approval.agent_id}</p>
                      <p className="text-xs text-gray-400 truncate font-mono">{approval.agent_id}</p>
                    </div>

                    {/* Action + Resource */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <code className="text-sm bg-gray-100 px-2 py-0.5 rounded text-gray-800">{approval.action}</code>
                        {approval.resource && (
                          <>
                            <span className="text-gray-400 text-xs">on</span>
                            <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-600 max-w-xs truncate">{approval.resource}</code>
                          </>
                        )}
                      </div>
                      {!isPending && approval.decision_reason && (
                        <p className="text-xs text-gray-500 mt-0.5">Reason: {approval.decision_reason}</p>
                      )}
                    </div>

                    {/* Time */}
                    <div className="shrink-0 text-right">
                      <p className="text-xs text-gray-500">{timeSince(approval.created_at)}</p>
                      {approval.decision_at && (
                        <p className="text-xs text-gray-400">decided {timeSince(approval.decision_at)}</p>
                      )}
                    </div>

                    {/* Action buttons (pending only) */}
                    {isPending && (
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          size="sm"
                          className="bg-green-600 hover:bg-green-700 text-white text-xs h-8"
                          onClick={() => openDecisionDialog(approval, 'approve')}
                        >
                          <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-red-300 text-red-700 hover:bg-red-50 text-xs h-8"
                          onClick={() => openDecisionDialog(approval, 'deny')}
                        >
                          <XCircle className="h-3.5 w-3.5 mr-1" />
                          Deny
                        </Button>
                      </div>
                    )}
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="border-t border-gray-200 px-4 py-4 bg-gray-50 space-y-3 text-sm">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs font-semibold text-gray-500 mb-1">APPROVAL ID</p>
                          <code className="text-xs text-gray-700">{approval.approval_id}</code>
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-gray-500 mb-1">REQUESTED AT</p>
                          <p className="text-xs text-gray-700">{formatTime(approval.created_at)}</p>
                        </div>
                        {approval.decision_at && (
                          <>
                            <div>
                              <p className="text-xs font-semibold text-gray-500 mb-1">DECIDED AT</p>
                              <p className="text-xs text-gray-700">{formatTime(approval.decision_at)}</p>
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-gray-500 mb-1">DECIDED BY</p>
                              <p className="text-xs text-gray-700">{approval.decision_by ?? '—'}</p>
                            </div>
                          </>
                        )}
                      </div>
                      {approval.context && Object.keys(approval.context).length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-gray-500 mb-1">CONTEXT</p>
                          <pre className="text-xs bg-white border border-gray-200 rounded p-2 overflow-x-auto text-gray-700">
                            {JSON.stringify(approval.context, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Decision Dialog */}
      <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) setDialogOpen(false) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {dialogAction === 'approve'
                ? <><CheckCircle2 className="h-5 w-5 text-green-600" /> Approve Request</>
                : <><XCircle className="h-5 w-5 text-red-600" /> Deny Request</>
              }
            </DialogTitle>
            <DialogDescription>
              {dialogApproval && (
                <>
                  Agent <strong>{dialogApproval.agent_name ?? dialogApproval.agent_id}</strong> wants to perform:
                  <br />
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm mt-1 inline-block">{dialogApproval?.action}</code>
                  {dialogApproval.resource && (
                    <> on <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm">{dialogApproval.resource}</code></>
                  )}
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="py-2">
            <label className="text-sm font-medium text-gray-700 block mb-1.5">
              Reason {dialogAction === 'deny' ? '(required)' : '(optional)'}
            </label>
            <textarea
              className="w-full min-h-[80px] rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder={dialogAction === 'approve'
                ? 'e.g. Reviewed and confirmed safe to proceed'
                : 'e.g. Operation not authorized in production environment'
              }
              value={dialogReason}
              onChange={(e) => setDialogReason(e.target.value)}
              disabled={dialogLoading}
            />
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)} disabled={dialogLoading}>
              Cancel
            </Button>
            <Button
              onClick={submitDecision}
              disabled={dialogLoading || (dialogAction === 'deny' && !dialogReason.trim())}
              className={dialogAction === 'approve'
                ? 'bg-green-600 hover:bg-green-700 text-white'
                : 'bg-red-600 hover:bg-red-700 text-white'
              }
            >
              {dialogLoading
                ? 'Processing...'
                : dialogAction === 'approve' ? 'Confirm Approve' : 'Confirm Deny'
              }
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
