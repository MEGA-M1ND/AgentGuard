'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  Globe,
  Loader2,
  Lock,
  RefreshCw,
  Shield,
  Terminal,
  Unlock,
  XCircle,
  Zap,
} from 'lucide-react'
import { toast } from 'sonner'

// ─── config ──────────────────────────────────────────────────────────────────

const API_URL       = process.env.NEXT_PUBLIC_API_URL       || 'http://localhost:8000'
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin123'

// ─── types ────────────────────────────────────────────────────────────────────

interface Agent {
  agent_id:    string
  name:        string
  owner_team:  string
  environment: string
  is_active:   boolean
}

interface PolicyRule {
  action:   string
  resource: string
}

interface Policy {
  agent_id: string
  allow:    PolicyRule[]
  deny:     PolicyRule[]
}

interface AuditLog {
  log_id:    string
  agent_id:  string
  timestamp: string
  action:    string
  resource:  string | null
  allowed:   boolean
  result:    string
  context:   Record<string, unknown> | null
  metadata:  Record<string, unknown> | null
}

// ─── constants ────────────────────────────────────────────────────────────────

const DEMO_AGENT_NAME = 'WebResearchBot'

// Base allow rules (always present)
const BASE_ALLOW: PolicyRule[] = [
  { action: 'search:web',     resource: '*'                  },
  { action: 'write:database', resource: 'research_findings'  },
]

// Base deny rules (always present)
const BASE_DENY: PolicyRule[] = [
  { action: 'delete:*',        resource: '*'        },
  { action: 'write:database',  resource: 'users'    },
  { action: 'write:database',  resource: 'payments' },
  { action: 'write:database',  resource: 'logs'     },
]

// Extra deny rule added when "Block DB Writes" is toggled on
const BLOCK_DB_RULE: PolicyRule = { action: 'write:database', resource: '*' }

// ─── helpers ──────────────────────────────────────────────────────────────────

const adminHeaders = {
  'Content-Type': 'application/json',
  'X-Admin-Key':  ADMIN_API_KEY,
}

function fmt(ts: string) {
  return new Date(ts).toLocaleTimeString()
}

function isBlockingRule(rule: PolicyRule) {
  return rule.action === BLOCK_DB_RULE.action && rule.resource === BLOCK_DB_RULE.resource
}

// ─── sub-components ───────────────────────────────────────────────────────────

function StepBadge({ step, icon: Icon, label, sub }: {
  step: number; icon: React.ElementType; label: string; sub: string
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm">
        {step}
      </div>
      <div className="flex-shrink-0">
        <Icon className="h-5 w-5 text-gray-500" />
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-800">{label}</p>
        <p className="text-xs text-gray-500 font-mono">{sub}</p>
      </div>
    </div>
  )
}

function Arrow({ blocked }: { blocked?: boolean }) {
  return (
    <div className={`ml-4 pl-8 border-l-2 py-1 ${blocked ? 'border-red-300' : 'border-blue-200'}`}>
      <div className={`text-xs font-mono px-2 py-0.5 rounded inline-block ${
        blocked ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'
      }`}>
        {blocked ? '✗ BLOCKED' : '✓ continues'}
      </div>
    </div>
  )
}

function LogRow({ log, expanded, onToggle }: {
  log: AuditLog; expanded: boolean; onToggle: () => void
}) {
  const runId = (log.metadata as Record<string, string> | null)?.run_id

  return (
    <>
      <tr
        className={`border-b cursor-pointer transition-colors ${
          log.allowed ? 'hover:bg-green-50' : 'hover:bg-red-50'
        }`}
        onClick={onToggle}
      >
        <td className="p-2 text-gray-400">
          {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        </td>
        <td className="p-2 font-mono text-xs text-gray-500">{fmt(log.timestamp)}</td>
        <td className="p-2 font-mono text-xs font-medium text-gray-800">{log.action}</td>
        <td className="p-2 font-mono text-xs text-gray-600 max-w-[160px] truncate">
          {log.resource || '—'}
        </td>
        <td className="p-2">
          <Badge
            variant={log.allowed ? 'success' : 'destructive'}
            className="text-xs"
          >
            {log.allowed ? 'ALLOWED' : 'DENIED'}
          </Badge>
        </td>
        <td className="p-2">
          {runId && (
            <span className="text-xs font-mono text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
              {String(runId)}
            </span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className={log.allowed ? 'bg-green-50' : 'bg-red-50'}>
          <td colSpan={6} className="px-6 py-3">
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="font-semibold text-gray-600">Log ID</span>
                <p className="font-mono text-gray-500 mt-0.5">{log.log_id}</p>
              </div>
              {log.context && Object.keys(log.context).length > 0 && (
                <div>
                  <span className="font-semibold text-gray-600">Context</span>
                  <pre className="font-mono text-gray-500 mt-0.5 whitespace-pre-wrap">
                    {JSON.stringify(log.context, null, 2)}
                  </pre>
                </div>
              )}
              {log.metadata && Object.keys(log.metadata).length > 0 && (
                <div>
                  <span className="font-semibold text-gray-600">Metadata</span>
                  <pre className="font-mono text-gray-500 mt-0.5 whitespace-pre-wrap">
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
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function DemoPage() {
  const [agent,       setAgent]       = useState<Agent | null>(null)
  const [policy,      setPolicy]      = useState<Policy | null>(null)
  const [logs,        setLogs]        = useState<AuditLog[]>([])
  const [expanded,    setExpanded]    = useState<Set<string>>(new Set())
  const [loading,     setLoading]     = useState(true)
  const [notFound,    setNotFound]    = useState(false)
  const [toggling,    setToggling]    = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastFetch,   setLastFetch]   = useState<Date | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── derived state ──────────────────────────────────────────────────────────
  const dbBlocked = policy?.deny.some(isBlockingRule) ?? false
  const allowCount = logs.filter(l => l.allowed).length
  const denyCount  = logs.filter(l => !l.allowed).length

  // ── data fetching ──────────────────────────────────────────────────────────
  const fetchAll = useCallback(async (agentId?: string) => {
    try {
      const id = agentId ?? agent?.agent_id
      if (!id) return

      const [logsRes, policyRes] = await Promise.all([
        fetch(`${API_URL}/logs?agent_id=${id}&limit=30`, { headers: { 'X-Admin-Key': ADMIN_API_KEY } }),
        fetch(`${API_URL}/agents/${id}/policy`,           { headers: { 'X-Admin-Key': ADMIN_API_KEY } }),
      ])

      if (logsRes.ok)   setLogs(await logsRes.json())
      if (policyRes.ok) setPolicy(await policyRes.json())
      setLastFetch(new Date())
    } catch {
      // silently ignore during auto-refresh
    }
  }, [agent?.agent_id])

  const findDemoAgent = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/agents`, { headers: { 'X-Admin-Key': ADMIN_API_KEY } })
      if (!res.ok) throw new Error('Failed to fetch agents')

      const agents: Agent[] = await res.json()
      const found = agents.find(a => a.name === DEMO_AGENT_NAME && a.is_active)

      if (!found) {
        setNotFound(true)
        return
      }

      setAgent(found)
      setNotFound(false)
      await fetchAll(found.agent_id)
    } catch (e) {
      toast.error('Could not reach backend', { description: String(e) })
      setNotFound(true)
    } finally {
      setLoading(false)
    }
  }, [fetchAll])

  // ── initial load ───────────────────────────────────────────────────────────
  useEffect(() => {
    findDemoAgent()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── auto-refresh every 2 s ────────────────────────────────────────────────
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    if (autoRefresh && agent) {
      timerRef.current = setInterval(() => fetchAll(), 2000)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [autoRefresh, agent, fetchAll])

  // ── toggle policy ──────────────────────────────────────────────────────────
  const toggleDbBlock = async () => {
    if (!agent || !policy) return
    setToggling(true)

    const newDeny = dbBlocked
      ? policy.deny.filter(r => !isBlockingRule(r))    // remove block
      : [...policy.deny, BLOCK_DB_RULE]                 // add block

    try {
      const res = await fetch(`${API_URL}/agents/${agent.agent_id}/policy`, {
        method:  'PUT',
        headers: adminHeaders,
        body:    JSON.stringify({ allow: policy.allow, deny: newDeny }),
      })
      if (!res.ok) throw new Error(await res.text())

      const updated: Policy = await res.json()
      setPolicy(updated)

      if (dbBlocked) {
        toast.success('DB writes restored', {
          description: 'WebResearchBot can now write to research_findings',
        })
      } else {
        toast.error('DB writes blocked', {
          description: 'All write:database actions are now denied',
        })
      }
    } catch (e) {
      toast.error('Policy update failed', { description: String(e) })
    } finally {
      setToggling(false)
    }
  }

  const toggleExpand = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  // ── render: not found ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="p-8 max-w-2xl">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="h-8 w-8 text-blue-500" />
          <h1 className="text-3xl font-bold">Live Demo</h1>
        </div>

        <Card className="border-amber-200 bg-amber-50">
          <CardHeader>
            <CardTitle className="text-amber-800 flex items-center gap-2">
              <Terminal className="h-5 w-5" />
              Demo agent not found
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-amber-700">
              No active <strong>WebResearchBot</strong> agent found. Run the setup script first.
            </p>
            <div className="bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-sm space-y-1">
              <p className="text-gray-500"># Terminal 1 — set up the demo agent (once)</p>
              <p>cd sdk/examples</p>
              <p>python demo_setup.py</p>
            </div>
            <div className="bg-gray-900 text-green-400 rounded-lg p-4 font-mono text-sm space-y-1">
              <p className="text-gray-500"># Terminal 2 — run the agent</p>
              <p>python demo_agent.py</p>
            </div>
            <Button onClick={findDemoAgent} className="mt-2">
              <RefreshCw className="h-4 w-4 mr-2" />
              Check again
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ── render: main demo page ─────────────────────────────────────────────────
  return (
    <div className="p-8">

      {/* ── header ── */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-blue-500" />
            <h1 className="text-3xl font-bold text-gray-900">Live Demo</h1>
            <Badge variant="success" className="text-sm">WebResearchBot</Badge>
          </div>
          <p className="text-gray-500 mt-1 ml-11">
            Watch AgentGuard govern a real AI agent in real time
          </p>
          {lastFetch && (
            <p className="text-xs text-gray-400 ml-11 mt-0.5">
              Last refreshed {lastFetch.toLocaleTimeString()}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(p => !p)}
            className={autoRefresh ? 'border-green-500 text-green-700' : ''}
          >
            <Activity className={`h-4 w-4 mr-2 ${autoRefresh ? 'animate-pulse text-green-500' : ''}`} />
            {autoRefresh ? 'Live' : 'Paused'}
          </Button>
          <Button variant="outline" size="sm" onClick={() => fetchAll()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* ── terminal hint ── */}
      <div className="mb-6 bg-gray-900 rounded-lg px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal className="h-4 w-4 text-green-400" />
          <span className="font-mono text-green-400 text-sm">
            python sdk/examples/demo_agent.py
          </span>
          <span className="text-gray-500 text-sm">— run this in another terminal while watching here</span>
        </div>
        <span className="text-xs text-gray-500 font-mono">
          {agent?.agent_id.substring(0, 16)}…
        </span>
      </div>

      {/* ── stats row ── */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">Total Actions</p>
            <p className="text-2xl font-bold">{logs.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">Allowed</p>
            <p className="text-2xl font-bold text-green-600">{allowCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">Denied</p>
            <p className="text-2xl font-bold text-red-600">{denyCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-gray-500 mb-1">DB Writes</p>
            <p className="text-2xl font-bold">
              {logs.filter(l => l.action === 'write:database').length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ── two-column: pipeline + policy ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">

        {/* agent pipeline */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-blue-500" />
              Agent Pipeline
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <StepBadge step={1} icon={Shield}   label="Permission check" sub="enforce(search:web)" />
            <Arrow blocked={false} />
            <StepBadge step={2} icon={Globe}    label="Web search"        sub="[mocked] arxiv, blogs, papers" />
            <Arrow blocked={dbBlocked} />
            <StepBadge step={3} icon={Shield}   label="Permission check"  sub="enforce(write:database)" />
            {dbBlocked
              ? <Arrow blocked={true} />
              : <Arrow blocked={false} />
            }
            <StepBadge step={4} icon={Database} label="Database write"    sub="research_findings table" />

            <div className="mt-4 pt-4 border-t">
              {dbBlocked ? (
                <div className="flex items-center gap-2 text-red-700 bg-red-50 rounded-lg px-3 py-2">
                  <XCircle className="h-4 w-4" />
                  <span className="text-sm font-medium">Step 4 is currently BLOCKED by policy</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-green-700 bg-green-50 rounded-lg px-3 py-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="text-sm font-medium">All steps currently ALLOWED by policy</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* policy panel */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              Live Policy Controls
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">

            {/* allow rules */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Allow</p>
              <div className="space-y-1.5">
                {(policy?.allow ?? BASE_ALLOW).map((rule, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm bg-green-50 rounded px-3 py-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />
                    <span className="font-mono text-green-800">{rule.action}</span>
                    <span className="text-green-600">→</span>
                    <span className="font-mono text-green-700">{rule.resource}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* deny rules */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Deny</p>
              <div className="space-y-1.5">
                {(policy?.deny ?? BASE_DENY).map((rule, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-2 text-sm rounded px-3 py-1.5 ${
                      isBlockingRule(rule)
                        ? 'bg-red-100 ring-1 ring-red-400'
                        : 'bg-red-50'
                    }`}
                  >
                    <XCircle className="h-3.5 w-3.5 text-red-600 flex-shrink-0" />
                    <span className="font-mono text-red-800">{rule.action}</span>
                    <span className="text-red-500">→</span>
                    <span className="font-mono text-red-700">{rule.resource}</span>
                    {isBlockingRule(rule) && (
                      <Badge variant="destructive" className="ml-auto text-xs">active</Badge>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* toggle button */}
            <div className="pt-2 border-t">
              <p className="text-xs text-gray-500 mb-3">
                Toggle the policy mid-demo — no code changes required.
              </p>
              <Button
                onClick={toggleDbBlock}
                disabled={toggling || !agent}
                variant={dbBlocked ? 'outline' : 'destructive'}
                className="w-full"
              >
                {toggling ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : dbBlocked ? (
                  <Unlock className="h-4 w-4 mr-2" />
                ) : (
                  <Lock className="h-4 w-4 mr-2" />
                )}
                {dbBlocked ? 'Restore DB Write Access' : 'Block DB Writes'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── live audit log ── */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              Live Audit Trail
              {autoRefresh && (
                <span className="ml-2 text-xs font-normal text-green-600 flex items-center gap-1">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                  auto-refresh every 2s
                </span>
              )}
            </CardTitle>
            <span className="text-sm text-gray-500">{logs.length} entries (last 30)</span>
          </div>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Activity className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p className="font-medium">No logs yet</p>
              <p className="text-sm mt-1">
                Run <code className="bg-gray-100 px-1 rounded">python demo_agent.py</code> to generate activity
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 text-left">
                    <th className="p-2 w-6"></th>
                    <th className="p-2 text-xs font-semibold text-gray-500 w-24">Time</th>
                    <th className="p-2 text-xs font-semibold text-gray-500">Action</th>
                    <th className="p-2 text-xs font-semibold text-gray-500">Resource</th>
                    <th className="p-2 text-xs font-semibold text-gray-500">Decision</th>
                    <th className="p-2 text-xs font-semibold text-gray-500">Run ID</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map(log => (
                    <LogRow
                      key={log.log_id}
                      log={log}
                      expanded={expanded.has(log.log_id)}
                      onToggle={() => toggleExpand(log.log_id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── demo script ── */}
      <Card className="mt-6 bg-gray-50 border-gray-200">
        <CardHeader>
          <CardTitle className="text-sm text-gray-600 flex items-center gap-2">
            <Terminal className="h-4 w-4" />
            Demo Script (60 seconds)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-2 text-sm text-gray-700">
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">1</span>
              <span>Run <code className="bg-white border px-1.5 rounded font-mono text-xs">python demo_agent.py</code> in a terminal. Watch logs appear below with <strong>ALLOWED</strong> status.</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">2</span>
              <span>Click <strong>"Block DB Writes"</strong> above to add a deny rule — <em>no agent code changes.</em></span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">3</span>
              <span>Run <code className="bg-white border px-1.5 rounded font-mono text-xs">python demo_agent.py</code> again. The DB write now shows <strong>DENIED</strong>.</span>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-bold">4</span>
              <span>Click <strong>"Restore DB Write Access"</strong>. Run again — back to green. The agent never changed.</span>
            </li>
          </ol>
        </CardContent>
      </Card>

    </div>
  )
}
