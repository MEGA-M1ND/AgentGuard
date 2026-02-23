'use client'

import { useEffect, useState } from 'react'
import { Shield, Plus, Trash2, Save, RefreshCw, ChevronDown, ChevronUp, Eye } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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

interface Agent {
  agent_id: string
  name: string
  owner_team: string
  environment: string
  is_active: boolean
}

interface PolicyRule {
  action: string
  resource: string | null
}

interface Policy {
  agent_id: string
  allow: PolicyRule[]
  deny: PolicyRule[]
  created_at: string
  updated_at: string
}

const EXAMPLE_RULES = [
  { action: 'read:*', resource: '*', description: 'Read anything (files, database, etc.)' },
  { action: 'write:*', resource: '*', description: 'Write anything (files, database, etc.)' },
  { action: 'send:email', resource: '*', description: 'Send any email' },
  { action: 'query:database', resource: '*', description: 'Query any database' },
  { action: 'delete:*', resource: '*', description: 'Delete anything (dangerous!)' },
  { action: 'execute:*', resource: '*', description: 'Execute anything (very dangerous!)' },
  { action: '*', resource: '*', description: 'Allow everything (full access)' },
]

export default function PoliciesPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [policies, setPolicies] = useState<Record<string, Policy>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Editing state
  const [editingAgent, setEditingAgent] = useState<string | null>(null)
  const [allowRules, setAllowRules] = useState<PolicyRule[]>([])
  const [denyRules, setDenyRules] = useState<PolicyRule[]>([])
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [saving, setSaving] = useState(false)

  const fetchAgents = async () => {
    try {
      const response = await fetch(`${API_URL}/agents`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY }
      })
      if (response.ok) {
        const data = await response.json()
        setAgents(data)
        return data as Agent[]
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err)
    }
    return []
  }

  const fetchPolicy = async (agentId: string): Promise<Policy | null> => {
    try {
      const response = await fetch(`${API_URL}/agents/${agentId}/policy`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY }
      })
      if (response.ok) {
        return await response.json()
      }
    } catch (err) {
      // Policy might not exist yet - that's OK
    }
    return null
  }

  const fetchAll = async () => {
    try {
      setLoading(true)
      setError(null)
      const agentList = await fetchAgents()

      const policyMap: Record<string, Policy> = {}
      for (const agent of agentList) {
        const policy = await fetchPolicy(agent.agent_id)
        if (policy) {
          policyMap[agent.agent_id] = policy
        }
      }
      setPolicies(policyMap)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const startEditing = (agentId: string) => {
    const existing = policies[agentId]
    if (existing) {
      setAllowRules(existing.allow.map(r => ({ action: r.action, resource: r.resource || '' })))
      setDenyRules(existing.deny.map(r => ({ action: r.action, resource: r.resource || '' })))
    } else {
      setAllowRules([{ action: '', resource: '' }])
      setDenyRules([])
    }
    setEditingAgent(agentId)
    setExpandedAgent(agentId)
  }

  const savePolicy = async () => {
    if (!editingAgent) return

    try {
      setSaving(true)
      setError(null)

      const cleanRules = (rules: PolicyRule[]) =>
        rules.filter(r => r.action.trim() !== '').map(r => ({
          action: r.action.trim(),
          resource: r.resource?.trim() || null
        }))

      const response = await fetch(`${API_URL}/agents/${editingAgent}/policy`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-ADMIN-KEY': ADMIN_API_KEY
        },
        body: JSON.stringify({
          allow: cleanRules(allowRules),
          deny: cleanRules(denyRules)
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to save policy: ${response.statusText}`)
      }

      const savedPolicy = await response.json()
      setPolicies(prev => ({ ...prev, [editingAgent]: savedPolicy }))
      setEditingAgent(null)
      toast.success('Policy saved successfully!', {
        description: 'The policy has been updated and is now in effect.'
      })
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to save policy'
      setError(errorMsg)
      toast.error('Failed to save policy', { description: errorMsg })
    } finally {
      setSaving(false)
    }
  }

  const addRule = (type: 'allow' | 'deny') => {
    if (type === 'allow') {
      setAllowRules([...allowRules, { action: '', resource: '' }])
    } else {
      setDenyRules([...denyRules, { action: '', resource: '' }])
    }
  }

  const removeRule = (type: 'allow' | 'deny', index: number) => {
    if (type === 'allow') {
      setAllowRules(allowRules.filter((_, i) => i !== index))
    } else {
      setDenyRules(denyRules.filter((_, i) => i !== index))
    }
  }

  const updateRule = (type: 'allow' | 'deny', index: number, field: 'action' | 'resource', value: string) => {
    if (type === 'allow') {
      const updated = [...allowRules]
      updated[index] = { ...updated[index], [field]: value }
      setAllowRules(updated)
    } else {
      const updated = [...denyRules]
      updated[index] = { ...updated[index], [field]: value }
      setDenyRules(updated)
    }
  }

  const applyExample = (rule: typeof EXAMPLE_RULES[0], type: 'allow' | 'deny') => {
    if (type === 'allow') {
      setAllowRules([...allowRules, { action: rule.action, resource: rule.resource }])
    } else {
      setDenyRules([...denyRules, { action: rule.action, resource: rule.resource }])
    }
  }

  const getPreviewJson = () => {
    const cleanRules = (rules: PolicyRule[]) =>
      rules.filter(r => r.action.trim() !== '').map(r => ({
        action: r.action.trim(),
        resource: r.resource?.trim() || null
      }))
    return JSON.stringify({ allow: cleanRules(allowRules), deny: cleanRules(denyRules) }, null, 2)
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Policies</h1>
          <p className="text-gray-600 mt-1">Define allow/deny rules for each agent</p>
        </div>
        <Button variant="outline" onClick={fetchAll}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading policies...</p>
        </div>
      )}

      {/* No Agents */}
      {!loading && agents.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 mb-2">No agents found</p>
            <p className="text-sm text-gray-400">Create agents first, then configure their policies here.</p>
          </CardContent>
        </Card>
      )}

      {/* Agent Policy Cards */}
      {!loading && agents.length > 0 && (
        <div className="space-y-4">
          {agents.map((agent) => {
            const policy = policies[agent.agent_id]
            const isEditing = editingAgent === agent.agent_id
            const isExpanded = expandedAgent === agent.agent_id

            return (
              <Card key={agent.agent_id} className={isEditing ? 'ring-2 ring-blue-500' : ''}>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setExpandedAgent(isExpanded ? null : agent.agent_id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                      </button>
                      <div>
                        <CardTitle className="text-lg">{agent.name}</CardTitle>
                        <CardDescription>
                          <code className="text-xs">{agent.agent_id}</code> &middot; {agent.environment}
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {policy ? (
                        <Badge variant="success">Policy Set</Badge>
                      ) : (
                        <Badge variant="warning">No Policy</Badge>
                      )}
                      {!isEditing && (
                        <Button size="sm" onClick={() => startEditing(agent.agent_id)}>
                          {policy ? 'Edit Policy' : 'Add Policy'}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>

                {/* Expanded: Show current policy or editor */}
                {isExpanded && (
                  <CardContent>
                    {isEditing ? (
                      /* ---- EDITOR MODE ---- */
                      <div className="space-y-6">
                        {/* Info Box */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
                          <p className="font-semibold text-blue-900 mb-3">💡 Flexible Action Format - Type Naturally!</p>
                          <div className="text-blue-800 space-y-3">
                            <div>
                              <p className="font-medium mb-1">✨ All these formats work the same:</p>
                              <div className="grid grid-cols-2 gap-2 ml-4">
                                <code className="bg-blue-100 px-2 py-1 rounded">read:file</code>
                                <span className="text-blue-600">← Standard</span>
                                <code className="bg-blue-100 px-2 py-1 rounded">read file</code>
                                <span className="text-blue-600">← Natural!</span>
                                <code className="bg-blue-100 px-2 py-1 rounded">Read File</code>
                                <span className="text-blue-600">← Capitalized</span>
                                <code className="bg-blue-100 px-2 py-1 rounded">read-file</code>
                                <span className="text-blue-600">← Hyphenated</span>
                                <code className="bg-blue-100 px-2 py-1 rounded">read_file</code>
                                <span className="text-blue-600">← Snake case</span>
                                <code className="bg-blue-100 px-2 py-1 rounded">readFile</code>
                                <span className="text-blue-600">← CamelCase</span>
                              </div>
                            </div>
                            <div>
                              <p className="font-medium mb-1">🎯 Examples:</p>
                              <ul className="ml-4 space-y-1">
                                <li><code className="bg-blue-100 px-1">send email</code> = Send emails</li>
                                <li><code className="bg-blue-100 px-1">query database</code> = Query database</li>
                                <li><code className="bg-blue-100 px-1">delete *</code> = Delete anything (wildcard)</li>
                                <li><code className="bg-blue-100 px-1">read</code> = Just "read" works too!</li>
                              </ul>
                            </div>
                          </div>
                        </div>
                        {/* Allow Rules */}
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-sm font-semibold text-green-700 flex items-center gap-2">
                              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                              Allow Rules
                            </h3>
                            <Button size="sm" variant="outline" onClick={() => addRule('allow')}>
                              <Plus className="h-3 w-3 mr-1" /> Add Rule
                            </Button>
                          </div>
                          {allowRules.length === 0 && (
                            <p className="text-sm text-gray-400 italic">No allow rules. Agent will be denied all actions.</p>
                          )}
                          <div className="space-y-2">
                            {allowRules.map((rule, index) => (
                              <div key={index} className="flex items-center gap-2">
                                <div className="flex-1">
                                  <Input
                                    placeholder="Action (e.g., read file, send email, delete *)"
                                    value={rule.action}
                                    onChange={(e) => updateRule('allow', index, 'action', e.target.value)}
                                    className="text-sm"
                                  />
                                </div>
                                <div className="flex-1">
                                  <Input
                                    placeholder="Resource (e.g., *, s3://bucket/*)"
                                    value={rule.resource || ''}
                                    onChange={(e) => updateRule('allow', index, 'resource', e.target.value)}
                                    className="text-sm"
                                  />
                                </div>
                                <Button size="icon" variant="ghost" onClick={() => removeRule('allow', index)}>
                                  <Trash2 className="h-4 w-4 text-red-500" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Deny Rules */}
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-sm font-semibold text-red-700 flex items-center gap-2">
                              <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                              Deny Rules
                            </h3>
                            <Button size="sm" variant="outline" onClick={() => addRule('deny')}>
                              <Plus className="h-3 w-3 mr-1" /> Add Rule
                            </Button>
                          </div>
                          {denyRules.length === 0 && (
                            <p className="text-sm text-gray-400 italic">No deny rules. Deny rules override allow rules.</p>
                          )}
                          <div className="space-y-2">
                            {denyRules.map((rule, index) => (
                              <div key={index} className="flex items-center gap-2">
                                <div className="flex-1">
                                  <Input
                                    placeholder="Action (e.g., delete *, execute code)"
                                    value={rule.action}
                                    onChange={(e) => updateRule('deny', index, 'action', e.target.value)}
                                    className="text-sm"
                                  />
                                </div>
                                <div className="flex-1">
                                  <Input
                                    placeholder="Resource (e.g., *, production/*)"
                                    value={rule.resource || ''}
                                    onChange={(e) => updateRule('deny', index, 'resource', e.target.value)}
                                    className="text-sm"
                                  />
                                </div>
                                <Button size="icon" variant="ghost" onClick={() => removeRule('deny', index)}>
                                  <Trash2 className="h-4 w-4 text-red-500" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Quick Add Examples */}
                        <div className="border-t pt-4">
                          <p className="text-xs text-gray-500 font-medium mb-2">Quick add examples:</p>
                          <div className="flex flex-wrap gap-2">
                            {EXAMPLE_RULES.map((rule, i) => (
                              <div key={i} className="flex items-center gap-1">
                                <button
                                  onClick={() => applyExample(rule, 'allow')}
                                  className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded hover:bg-green-100 border border-green-200"
                                  title={`Allow: ${rule.description}`}
                                >
                                  + {rule.action}
                                </button>
                                <button
                                  onClick={() => applyExample(rule, 'deny')}
                                  className="text-xs bg-red-50 text-red-700 px-1 py-1 rounded hover:bg-red-100 border border-red-200"
                                  title={`Deny: ${rule.description}`}
                                >
                                  -
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-3 border-t pt-4">
                          <Button onClick={savePolicy} disabled={saving}>
                            <Save className="h-4 w-4 mr-2" />
                            {saving ? 'Saving...' : 'Save Policy'}
                          </Button>
                          <Button variant="outline" onClick={() => setShowPreview(true)}>
                            <Eye className="h-4 w-4 mr-2" />
                            Preview JSON
                          </Button>
                          <Button variant="ghost" onClick={() => { setEditingAgent(null) }}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : policy ? (
                      /* ---- VIEW MODE ---- */
                      <div className="space-y-4">
                        <div>
                          <h3 className="text-sm font-semibold text-green-700 mb-2">Allow Rules ({policy.allow.length})</h3>
                          {policy.allow.length === 0 ? (
                            <p className="text-sm text-gray-400 italic">None</p>
                          ) : (
                            <div className="space-y-1">
                              {policy.allow.map((rule: any, i: number) => (
                                <div key={i} className="flex items-center gap-2 text-sm">
                                  <Badge variant="success" className="text-xs">ALLOW</Badge>
                                  <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.action}</code>
                                  {rule.resource && (
                                    <>
                                      <span className="text-gray-400">on</span>
                                      <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.resource}</code>
                                    </>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <div>
                          <h3 className="text-sm font-semibold text-red-700 mb-2">Deny Rules ({policy.deny.length})</h3>
                          {policy.deny.length === 0 ? (
                            <p className="text-sm text-gray-400 italic">None</p>
                          ) : (
                            <div className="space-y-1">
                              {policy.deny.map((rule: any, i: number) => (
                                <div key={i} className="flex items-center gap-2 text-sm">
                                  <Badge variant="destructive" className="text-xs">DENY</Badge>
                                  <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.action}</code>
                                  {rule.resource && (
                                    <>
                                      <span className="text-gray-400">on</span>
                                      <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.resource}</code>
                                    </>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-gray-400">
                          Last updated: {new Date(policy.updated_at).toLocaleString()}
                        </p>
                      </div>
                    ) : (
                      /* ---- NO POLICY ---- */
                      <div className="text-center py-6">
                        <Shield className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                        <p className="text-sm text-gray-500 mb-3">No policy configured. This agent will be denied all actions by default.</p>
                        <Button size="sm" onClick={() => startEditing(agent.agent_id)}>
                          <Plus className="h-4 w-4 mr-2" />
                          Add Policy
                        </Button>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>
      )}

      {/* JSON Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Policy JSON Preview</DialogTitle>
            <DialogDescription>
              This is the JSON that will be sent to the API
            </DialogDescription>
          </DialogHeader>
          <pre className="bg-gray-900 text-green-400 p-4 rounded-lg text-sm overflow-x-auto max-h-96">
            {getPreviewJson()}
          </pre>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPreview(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
