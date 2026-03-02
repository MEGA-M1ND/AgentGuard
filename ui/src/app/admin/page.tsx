'use client'

import { useEffect, useState } from 'react'
import {
  Users, Shield, Plus, Trash2, RefreshCw, Key,
  Crown, Eye, CheckCircle, ChevronDown, ChevronUp, Copy
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin-secret-key'

interface AdminUser {
  admin_id: string
  name: string
  role: string
  team: string | null
  is_active: boolean
  created_at: string
}

interface TeamPolicy {
  team: string
  allow_rules: { action: string; resource: string }[]
  deny_rules: { action: string; resource: string }[]
  require_approval_rules: { action: string; resource: string }[]
}

const ROLE_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType; level: number }> = {
  'super-admin': { label: 'Super Admin', color: 'bg-red-100 text-red-800',    icon: Crown,       level: 4 },
  'admin':       { label: 'Admin',       color: 'bg-blue-100 text-blue-800',   icon: Shield,      level: 3 },
  'auditor':     { label: 'Auditor',     color: 'bg-green-100 text-green-800', icon: Eye,         level: 2 },
  'approver':    { label: 'Approver',    color: 'bg-amber-100 text-amber-800', icon: CheckCircle, level: 1 },
}

const headers = { 'X-Admin-Key': ADMIN_KEY, 'Content-Type': 'application/json' }

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState<{ name: string; key: string } | null>(null)

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', role: 'auditor', team: '' })

  // Team policy
  const [teamName, setTeamName] = useState('')
  const [teamPolicy, setTeamPolicy] = useState<TeamPolicy | null>(null)
  const [loadingTeam, setLoadingTeam] = useState(false)
  const [teamForm, setTeamForm] = useState({
    deny: '{"action": "delete:*", "resource": "production/*"}',
    allow: '',
    approval: '',
  })
  const [savingTeam, setSavingTeam] = useState(false)
  const [teamExpanded, setTeamExpanded] = useState(false)

  const loadUsers = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/admin/users`, { headers })
      if (res.ok) setUsers(await res.json())
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { loadUsers() }, [])

  const createUser = async () => {
    if (!form.name.trim()) { toast.error('Name is required'); return }
    setCreating(true)
    try {
      const res = await fetch(`${API_URL}/admin/users`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: form.name,
          role: form.role,
          team: form.team.trim() || null,
        }),
      })
      if (!res.ok) { toast.error((await res.json()).detail); return }
      const data = await res.json()
      setNewKey({ name: data.name, key: data.api_key })
      setForm({ name: '', role: 'auditor', team: '' })
      setShowCreate(false)
      await loadUsers()
      toast.success(`Admin user "${data.name}" created`)
    } finally { setCreating(false) }
  }

  const deactivateUser = async (id: string, name: string) => {
    if (!confirm(`Deactivate "${name}"? They will lose access immediately.`)) return
    await fetch(`${API_URL}/admin/users/${id}`, { method: 'DELETE', headers })
    await loadUsers()
    toast.success(`${name} deactivated`)
  }

  const loadTeamPolicy = async () => {
    if (!teamName.trim()) { toast.error('Enter a team name'); return }
    setLoadingTeam(true)
    try {
      const res = await fetch(`${API_URL}/teams/${teamName}/policy`, { headers })
      if (res.ok) {
        const p = await res.json()
        setTeamPolicy(p)
        setTeamForm({
          deny: p.deny_rules.map((r: any) => JSON.stringify(r)).join('\n'),
          allow: p.allow_rules.map((r: any) => JSON.stringify(r)).join('\n'),
          approval: p.require_approval_rules.map((r: any) => JSON.stringify(r)).join('\n'),
        })
        setTeamExpanded(true)
      } else {
        setTeamPolicy({ team: teamName, allow_rules: [], deny_rules: [], require_approval_rules: [] })
        setTeamExpanded(true)
      }
    } finally { setLoadingTeam(false) }
  }

  const parseRules = (text: string) => {
    if (!text.trim()) return []
    return text.trim().split('\n').map(line => {
      try { return JSON.parse(line.trim()) } catch { return null }
    }).filter(Boolean)
  }

  const saveTeamPolicy = async () => {
    if (!teamName.trim()) return
    setSavingTeam(true)
    try {
      const body = {
        deny_rules: parseRules(teamForm.deny),
        allow_rules: parseRules(teamForm.allow),
        require_approval_rules: parseRules(teamForm.approval),
      }
      const res = await fetch(`${API_URL}/teams/${teamName}/policy`, {
        method: 'PUT', headers, body: JSON.stringify(body),
      })
      if (!res.ok) { toast.error((await res.json()).detail); return }
      setTeamPolicy(await res.json())
      toast.success(`Team policy saved for "${teamName}"`)
    } finally { setSavingTeam(false) }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Shield className="h-6 w-6 text-blue-600" />
          Access Control
        </h1>
        <p className="text-gray-500 mt-1">
          Manage admin users, roles, and team-level base policies.
        </p>
      </div>

      {/* Role Hierarchy */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Role Hierarchy</CardTitle>
          <CardDescription>Higher roles inherit all permissions of lower roles.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap">
            {Object.entries(ROLE_CONFIG).sort((a, b) => b[1].level - a[1].level).map(([role, cfg]) => {
              const Icon = cfg.icon
              return (
                <div key={role} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${cfg.color}`}>
                  <Icon className="h-4 w-4" />
                  <span>{cfg.label}</span>
                  <span className="opacity-50 text-xs">lv{cfg.level}</span>
                </div>
              )
            })}
            <div className="flex items-center text-gray-400 text-sm gap-1">← strongest</div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-600">
            <div><span className="font-medium">Super Admin:</span> Full access, create admin users</div>
            <div><span className="font-medium">Admin:</span> Manage agents, policies, team rules</div>
            <div><span className="font-medium">Auditor:</span> View logs, reports (read-only)</div>
            <div><span className="font-medium">Approver:</span> Approve/deny pending actions</div>
          </div>
        </CardContent>
      </Card>

      {/* Admin Users */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" /> Admin Users
              </CardTitle>
              <CardDescription>Named users with role-scoped JWT access. Keys are shown once at creation.</CardDescription>
            </div>
            <Button size="sm" onClick={() => setShowCreate(v => !v)}>
              <Plus className="h-4 w-4 mr-1" /> Add User
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">

          {/* Create form */}
          {showCreate && (
            <div className="border rounded-lg p-4 bg-gray-50 space-y-3">
              <div className="text-sm font-medium text-gray-700">New Admin User</div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Name</label>
                  <Input
                    placeholder="Alice Chen"
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Role</label>
                  <select
                    value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                    className="w-full border rounded-md px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="admin">admin</option>
                    <option value="auditor">auditor</option>
                    <option value="approver">approver</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Team scope (optional)</label>
                  <Input
                    placeholder="payments (blank = all teams)"
                    value={form.team}
                    onChange={e => setForm(f => ({ ...f, team: e.target.value }))}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={createUser} disabled={creating}>
                  {creating ? <RefreshCw className="h-3 w-3 mr-1 animate-spin" /> : <Plus className="h-3 w-3 mr-1" />}
                  Create
                </Button>
                <Button size="sm" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              </div>
            </div>
          )}

          {/* New key reveal */}
          {newKey && (
            <div className="border-2 border-green-300 bg-green-50 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-green-700 font-semibold">
                <Key className="h-4 w-4" />
                API Key for {newKey.name} — save this now, it won&apos;t be shown again
              </div>
              <div className="flex gap-2 items-center">
                <code className="flex-1 bg-white border rounded px-3 py-2 text-sm font-mono break-all">
                  {newKey.key}
                </code>
                <Button size="sm" variant="outline" onClick={() => {
                  navigator.clipboard.writeText(newKey.key)
                  toast.success('Copied!')
                }}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setNewKey(null)}>Dismiss</Button>
            </div>
          )}

          {/* User list */}
          {loading ? (
            <div className="text-sm text-gray-400 py-4 text-center">Loading...</div>
          ) : users.length === 0 ? (
            <div className="text-sm text-gray-400 py-8 text-center">
              No admin users yet. The <code className="text-xs bg-gray-100 px-1 rounded">ADMIN_API_KEY</code> env var acts as implicit super-admin.
            </div>
          ) : (
            <div className="space-y-2">
              {users.map(u => {
                const cfg = ROLE_CONFIG[u.role] ?? ROLE_CONFIG.auditor
                const Icon = cfg.icon
                return (
                  <div key={u.admin_id} className="flex items-center justify-between border rounded-lg px-4 py-3 bg-white hover:bg-gray-50">
                    <div className="flex items-center gap-3">
                      <div className={`rounded-full p-2 ${cfg.color}`}>
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="font-medium text-sm">{u.name}</div>
                        <div className="text-xs text-gray-400">{u.admin_id}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={cfg.color}>{cfg.label}</Badge>
                      {u.team ? (
                        <Badge variant="outline">{u.team}</Badge>
                      ) : (
                        <Badge variant="outline" className="text-gray-400">all teams</Badge>
                      )}
                      {!u.is_active && <Badge className="bg-gray-100 text-gray-500">inactive</Badge>}
                      {u.is_active && (
                        <Button
                          size="sm" variant="ghost"
                          className="text-red-500 hover:text-red-700 hover:bg-red-50 h-7 w-7 p-0"
                          onClick={() => deactivateUser(u.admin_id, u.name)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Team Policy */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" /> Team Base Policy
          </CardTitle>
          <CardDescription>
            Team-level rules are merged with every agent in that team.
            Deny rules from the team override agent allow rules.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Team name (e.g. payments)"
              value={teamName}
              onChange={e => setTeamName(e.target.value)}
              className="max-w-xs"
              onKeyDown={e => e.key === 'Enter' && loadTeamPolicy()}
            />
            <Button onClick={loadTeamPolicy} disabled={loadingTeam} variant="outline">
              {loadingTeam ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Load'}
            </Button>
          </div>

          {teamPolicy && (
            <div className="space-y-4 border rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">Policy for team: <code className="bg-white px-1 rounded">{teamPolicy.team}</code></span>
                <button
                  onClick={() => setTeamExpanded(v => !v)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  {teamExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
              </div>

              {teamExpanded && (
                <div className="space-y-3">
                  {[
                    { key: 'deny' as const, label: 'Deny Rules', color: 'text-red-700', placeholder: '{"action": "delete:*", "resource": "production/*"}' },
                    { key: 'allow' as const, label: 'Allow Rules', color: 'text-green-700', placeholder: '{"action": "read:*", "resource": "*"}' },
                    { key: 'approval' as const, label: 'Require Approval', color: 'text-amber-700', placeholder: '{"action": "transfer:funds", "resource": "*"}' },
                  ].map(({ key, label, color, placeholder }) => (
                    <div key={key}>
                      <label className={`text-xs font-semibold ${color} mb-1 block`}>{label}</label>
                      <textarea
                        value={teamForm[key]}
                        onChange={e => setTeamForm(f => ({ ...f, [key]: e.target.value }))}
                        placeholder={`One JSON rule per line:\n${placeholder}`}
                        rows={3}
                        className="w-full border rounded-md px-3 py-2 text-xs font-mono resize-none bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  ))}
                  <Button onClick={saveTeamPolicy} disabled={savingTeam} size="sm">
                    {savingTeam ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : null}
                    Save Team Policy
                  </Button>
                </div>
              )}

              {/* Current rules summary */}
              {!teamExpanded && (
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div><span className="text-red-600 font-medium">{teamPolicy.deny_rules.length}</span> deny rules</div>
                  <div><span className="text-green-600 font-medium">{teamPolicy.allow_rules.length}</span> allow rules</div>
                  <div><span className="text-amber-600 font-medium">{teamPolicy.require_approval_rules.length}</span> approval rules</div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
