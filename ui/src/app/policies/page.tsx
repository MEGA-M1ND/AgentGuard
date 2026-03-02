'use client'

import { useEffect, useState } from 'react'
import { Shield, Plus, Trash2, Save, RefreshCw, ChevronDown, ChevronUp, Eye, Sparkles, CheckCircle, AlertTriangle, X, BookOpen, Tag, Filter } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
  conditions?: Record<string, any>
}

interface Policy {
  agent_id: string
  allow: PolicyRule[]
  deny: PolicyRule[]
  require_approval: PolicyRule[]
  created_at: string
  updated_at: string
}

interface AIDraft {
  allow: PolicyRule[]
  deny: PolicyRule[]
  explanation: string
}

interface PolicyTemplate {
  id: string
  name: string
  description: string
  tags: string[]
  allow: PolicyRule[]
  deny: PolicyRule[]
  require_approval: PolicyRule[]
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

function formatConditions(c: Record<string, any>): string {
  const parts: string[] = []
  if (c.env) parts.push(`env:${(c.env as string[]).join(',')}`)
  if (c.time_range) {
    const tr = c.time_range as { start: string; end: string; tz?: string }
    parts.push(`${tr.start}–${tr.end} ${tr.tz || 'UTC'}`)
  }
  if (c.day_of_week) parts.push((c.day_of_week as string[]).join('/'))
  return parts.length ? parts.join(' · ') : 'conditions'
}

export default function PoliciesPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [policies, setPolicies] = useState<Record<string, Policy>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Editing state
  const [editingAgent, setEditingAgent] = useState<string | null>(null)
  const [allowRules, setAllowRules] = useState<PolicyRule[]>([])
  const [denyRules, setDenyRules] = useState<PolicyRule[]>([])
  const [approvalRules, setApprovalRules] = useState<PolicyRule[]>([])
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [saving, setSaving] = useState(false)

  // Template state
  const [templates, setTemplates] = useState<PolicyTemplate[]>([])
  const [templateDialogAgent, setTemplateDialogAgent] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<PolicyTemplate | null>(null)

  // AI generation state
  const [aiDialogAgent, setAiDialogAgent] = useState<string | null>(null)
  const [aiDescription, setAiDescription] = useState('')
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [aiDraft, setAiDraft] = useState<AIDraft | null>(null)
  const [isAiDraft, setIsAiDraft] = useState(false)

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
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    try {
      const res = await fetch(`${API_URL}/policy-templates`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY },
      })
      if (res.ok) setTemplates(await res.json())
    } catch {
      // silently ignore — templates are a convenience feature
    }
  }

  const openTemplateDialog = (agentId: string) => {
    setTemplateDialogAgent(agentId)
    setSelectedTemplate(null)
  }

  const closeTemplateDialog = () => {
    setTemplateDialogAgent(null)
    setSelectedTemplate(null)
  }

  const applyTemplate = () => {
    if (!selectedTemplate || !templateDialogAgent) return
    setAllowRules(selectedTemplate.allow.map(r => ({ action: r.action, resource: r.resource || '*' })))
    setDenyRules(selectedTemplate.deny.map(r => ({ action: r.action, resource: r.resource || '*' })))
    setApprovalRules((selectedTemplate.require_approval || []).map(r => ({ action: r.action, resource: r.resource || '*' })))
    setIsAiDraft(false)
    setEditingAgent(templateDialogAgent)
    setExpandedAgent(templateDialogAgent)
    closeTemplateDialog()
    toast.success(`Template applied: ${selectedTemplate.name}`, {
      description: 'Review the rules, then click Save Policy to activate.',
    })
  }

  const startEditing = (agentId: string) => {
    const existing = policies[agentId]
    if (existing) {
      setAllowRules(existing.allow.map((r: any) => ({ action: r.action, resource: r.resource || '', conditions: r.conditions })))
      setDenyRules(existing.deny.map((r: any) => ({ action: r.action, resource: r.resource || '', conditions: r.conditions })))
      setApprovalRules((existing.require_approval || []).map((r: any) => ({ action: r.action, resource: r.resource || '', conditions: r.conditions })))
    } else {
      setAllowRules([{ action: '', resource: '' }])
      setDenyRules([])
      setApprovalRules([])
    }
    setIsAiDraft(false)
    setEditingAgent(agentId)
    setExpandedAgent(agentId)
  }

  // --- AI Generation ---

  const openAiDialog = (agentId: string) => {
    setAiDialogAgent(agentId)
    setAiDescription('')
    setAiError(null)
    setAiDraft(null)
  }

  const closeAiDialog = () => {
    setAiDialogAgent(null)
    setAiDescription('')
    setAiError(null)
    setAiDraft(null)
    setAiGenerating(false)
  }

  const generatePolicy = async () => {
    if (!aiDialogAgent || aiDescription.trim().length < 10) return

    setAiGenerating(true)
    setAiError(null)
    setAiDraft(null)

    try {
      const res = await fetch(`${API_URL}/agents/${aiDialogAgent}/policy/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-ADMIN-KEY': ADMIN_API_KEY,
        },
        body: JSON.stringify({ description: aiDescription.trim() }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Generation failed')
      }

      const draft: AIDraft = await res.json()
      setAiDraft(draft)
    } catch (err) {
      setAiError(err instanceof Error ? err.message : 'AI generation failed')
    } finally {
      setAiGenerating(false)
    }
  }

  const applyAiDraft = () => {
    if (!aiDraft || !aiDialogAgent) return

    setAllowRules(aiDraft.allow.map(r => ({ action: r.action, resource: r.resource || '*' })))
    setDenyRules(aiDraft.deny.map(r => ({ action: r.action, resource: r.resource || '*' })))
    setApprovalRules([])
    setIsAiDraft(true)
    setEditingAgent(aiDialogAgent)
    setExpandedAgent(aiDialogAgent)
    closeAiDialog()
    toast.success('AI draft loaded into editor', {
      description: 'Review the rules below, then click Save Policy to activate.'
    })
  }

  // --- Policy Save ---

  const savePolicy = async () => {
    if (!editingAgent) return

    try {
      setSaving(true)
      setError(null)

      const cleanRules = (rules: PolicyRule[]) =>
        rules.filter(r => r.action.trim() !== '').map(r => ({
          action: r.action.trim(),
          resource: r.resource?.trim() || null,
          ...(r.conditions && Object.keys(r.conditions).length > 0 ? { conditions: r.conditions } : {}),
        }))

      const response = await fetch(`${API_URL}/agents/${editingAgent}/policy`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-ADMIN-KEY': ADMIN_API_KEY
        },
        body: JSON.stringify({
          allow: cleanRules(allowRules),
          deny: cleanRules(denyRules),
          require_approval: cleanRules(approvalRules),
        })
      })

      if (!response.ok) {
        throw new Error(`Failed to save policy: ${response.statusText}`)
      }

      const savedPolicy = await response.json()
      setPolicies(prev => ({ ...prev, [editingAgent]: savedPolicy }))
      setEditingAgent(null)
      setIsAiDraft(false)
      setApprovalRules([])
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

  const addRule = (type: 'allow' | 'deny' | 'approval') => {
    if (type === 'allow') setAllowRules([...allowRules, { action: '', resource: '' }])
    else if (type === 'deny') setDenyRules([...denyRules, { action: '', resource: '' }])
    else setApprovalRules([...approvalRules, { action: '', resource: '' }])
  }

  const removeRule = (type: 'allow' | 'deny' | 'approval', index: number) => {
    if (type === 'allow') setAllowRules(allowRules.filter((_, i) => i !== index))
    else if (type === 'deny') setDenyRules(denyRules.filter((_, i) => i !== index))
    else setApprovalRules(approvalRules.filter((_, i) => i !== index))
  }

  const updateRule = (type: 'allow' | 'deny' | 'approval', index: number, field: 'action' | 'resource', value: string) => {
    if (type === 'allow') {
      const updated = [...allowRules]
      updated[index] = { ...updated[index], [field]: value }
      setAllowRules(updated)
    } else if (type === 'deny') {
      const updated = [...denyRules]
      updated[index] = { ...updated[index], [field]: value }
      setDenyRules(updated)
    } else {
      const updated = [...approvalRules]
      updated[index] = { ...updated[index], [field]: value }
      setApprovalRules(updated)
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
    return JSON.stringify({ allow: cleanRules(allowRules), deny: cleanRules(denyRules), require_approval: cleanRules(approvalRules) }, null, 2)
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
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-blue-300 text-blue-700 hover:bg-blue-50"
                            onClick={() => openTemplateDialog(agent.agent_id)}
                          >
                            <BookOpen className="h-3.5 w-3.5 mr-1.5" />
                            Templates
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-purple-300 text-purple-700 hover:bg-purple-50"
                            onClick={() => openAiDialog(agent.agent_id)}
                          >
                            <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                            Generate with AI
                          </Button>
                          <Button size="sm" onClick={() => startEditing(agent.agent_id)}>
                            {policy ? 'Edit Policy' : 'Add Policy'}
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </CardHeader>

                {isExpanded && (
                  <CardContent>
                    {isEditing ? (
                      /* ---- EDITOR MODE ---- */
                      <div className="space-y-6">

                        {/* AI Draft Banner */}
                        {isAiDraft && (
                          <div className="flex items-start gap-3 bg-amber-50 border border-amber-300 rounded-lg p-4">
                            <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-amber-900">AI-Generated Draft — Pending Review</p>
                              <p className="text-sm text-amber-800 mt-0.5">
                                These rules were generated by Claude AI. Review carefully before saving — AI can make mistakes.
                              </p>
                            </div>
                            <button onClick={() => setIsAiDraft(false)} className="text-amber-500 hover:text-amber-700 shrink-0">
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        )}

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
                              <div key={index} className="space-y-1">
                                <div className="flex items-center gap-2">
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
                                {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                                  <div className="flex items-center gap-1.5 text-xs text-blue-600 ml-2">
                                    <Filter className="h-3 w-3 flex-shrink-0" />
                                    <span className="text-blue-500">Conditions:</span>
                                    <code className="bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded text-blue-700" title={JSON.stringify(rule.conditions, null, 2)}>
                                      {formatConditions(rule.conditions)}
                                    </code>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Require Approval Rules */}
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-sm font-semibold text-amber-700 flex items-center gap-2">
                              <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                              Require Approval Rules
                            </h3>
                            <Button size="sm" variant="outline" onClick={() => addRule('approval')}>
                              <Plus className="h-3 w-3 mr-1" /> Add Rule
                            </Button>
                          </div>
                          <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-2 text-xs text-amber-800">
                            Actions matching these rules will <strong>pause and wait</strong> for a human to approve or deny in the Approvals queue.
                          </div>
                          {approvalRules.length === 0 && (
                            <p className="text-sm text-gray-400 italic">No approval rules. All matching actions go directly to allow/deny.</p>
                          )}
                          <div className="space-y-2">
                            {approvalRules.map((rule, index) => (
                              <div key={index} className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <div className="flex-1">
                                    <Input
                                      placeholder="Action (e.g., delete:*, write:database)"
                                      value={rule.action}
                                      onChange={(e) => updateRule('approval', index, 'action', e.target.value)}
                                      className="text-sm border-amber-300 focus:ring-amber-400"
                                    />
                                  </div>
                                  <div className="flex-1">
                                    <Input
                                      placeholder="Resource (e.g., production/*, *)"
                                      value={rule.resource || ''}
                                      onChange={(e) => updateRule('approval', index, 'resource', e.target.value)}
                                      className="text-sm border-amber-300 focus:ring-amber-400"
                                    />
                                  </div>
                                  <Button size="icon" variant="ghost" onClick={() => removeRule('approval', index)}>
                                    <Trash2 className="h-4 w-4 text-red-500" />
                                  </Button>
                                </div>
                                {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                                  <div className="flex items-center gap-1.5 text-xs text-blue-600 ml-2">
                                    <Filter className="h-3 w-3 flex-shrink-0" />
                                    <span className="text-blue-500">Conditions:</span>
                                    <code className="bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded text-blue-700" title={JSON.stringify(rule.conditions, null, 2)}>
                                      {formatConditions(rule.conditions)}
                                    </code>
                                  </div>
                                )}
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
                              <div key={index} className="space-y-1">
                                <div className="flex items-center gap-2">
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
                                {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                                  <div className="flex items-center gap-1.5 text-xs text-blue-600 ml-2">
                                    <Filter className="h-3 w-3 flex-shrink-0" />
                                    <span className="text-blue-500">Conditions:</span>
                                    <code className="bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded text-blue-700" title={JSON.stringify(rule.conditions, null, 2)}>
                                      {formatConditions(rule.conditions)}
                                    </code>
                                  </div>
                                )}
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
                          <Button variant="ghost" onClick={() => { setEditingAgent(null); setIsAiDraft(false); setApprovalRules([]) }}>
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
                                <div key={i} className="flex items-center gap-2 text-sm flex-wrap">
                                  <Badge variant="success" className="text-xs">ALLOW</Badge>
                                  <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.action}</code>
                                  {rule.resource && (
                                    <>
                                      <span className="text-gray-400">on</span>
                                      <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.resource}</code>
                                    </>
                                  )}
                                  {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                                    <span
                                      className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded cursor-help"
                                      title={JSON.stringify(rule.conditions, null, 2)}
                                    >
                                      <Filter className="h-2.5 w-2.5" />
                                      {formatConditions(rule.conditions)}
                                    </span>
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
                                <div key={i} className="flex items-center gap-2 text-sm flex-wrap">
                                  <Badge variant="destructive" className="text-xs">DENY</Badge>
                                  <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.action}</code>
                                  {rule.resource && (
                                    <>
                                      <span className="text-gray-400">on</span>
                                      <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.resource}</code>
                                    </>
                                  )}
                                  {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                                    <span
                                      className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded cursor-help"
                                      title={JSON.stringify(rule.conditions, null, 2)}
                                    >
                                      <Filter className="h-2.5 w-2.5" />
                                      {formatConditions(rule.conditions)}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        {policy.require_approval && policy.require_approval.length > 0 && (
                          <div>
                            <h3 className="text-sm font-semibold text-amber-700 mb-2">Require Approval ({policy.require_approval.length})</h3>
                            <div className="space-y-1">
                              {policy.require_approval.map((rule: any, i: number) => (
                                <div key={i} className="flex items-center gap-2 text-sm flex-wrap">
                                  <Badge className="bg-amber-100 text-amber-800 border border-amber-300 text-xs">APPROVAL</Badge>
                                  <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.action}</code>
                                  {rule.resource && (
                                    <>
                                      <span className="text-gray-400">on</span>
                                      <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.resource}</code>
                                    </>
                                  )}
                                  {rule.conditions && Object.keys(rule.conditions).length > 0 && (
                                    <span
                                      className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded cursor-help"
                                      title={JSON.stringify(rule.conditions, null, 2)}
                                    >
                                      <Filter className="h-2.5 w-2.5" />
                                      {formatConditions(rule.conditions)}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <p className="text-xs text-gray-400">
                          Last updated: {new Date(policy.updated_at).toLocaleString()}
                        </p>
                      </div>
                    ) : (
                      /* ---- NO POLICY ---- */
                      <div className="text-center py-6">
                        <Shield className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                        <p className="text-sm text-gray-500 mb-3">No policy configured. This agent will be denied all actions by default.</p>
                        <div className="flex justify-center gap-3 flex-wrap">
                          <Button size="sm" variant="outline" className="border-blue-300 text-blue-700 hover:bg-blue-50" onClick={() => openTemplateDialog(agent.agent_id)}>
                            <BookOpen className="h-4 w-4 mr-2" />
                            Use Template
                          </Button>
                          <Button size="sm" variant="outline" className="border-purple-300 text-purple-700 hover:bg-purple-50" onClick={() => openAiDialog(agent.agent_id)}>
                            <Sparkles className="h-4 w-4 mr-2" />
                            Generate with AI
                          </Button>
                          <Button size="sm" onClick={() => startEditing(agent.agent_id)}>
                            <Plus className="h-4 w-4 mr-2" />
                            Add Policy
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>
      )}

      {/* ---- TEMPLATE DIALOG ---- */}
      <Dialog open={!!templateDialogAgent} onOpenChange={(open) => { if (!open) closeTemplateDialog() }}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-blue-600" />
              Policy Templates
            </DialogTitle>
            <DialogDescription>
              Choose a pre-built template to quickly configure common policy patterns.
              You can customise the rules in the editor after applying.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            {templates.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-4">Loading templates…</p>
            )}
            {templates.map((tpl) => (
              <button
                key={tpl.id}
                onClick={() => setSelectedTemplate(tpl.id === selectedTemplate?.id ? null : tpl)}
                className={`w-full text-left rounded-lg border p-4 transition-colors ${
                  selectedTemplate?.id === tpl.id
                    ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                    : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-gray-900">{tpl.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{tpl.description}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {tpl.tags.map(tag => (
                        <span key={tag} className="inline-flex items-center gap-0.5 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                          <Tag className="h-2.5 w-2.5" />{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="shrink-0 flex flex-col gap-1 text-xs text-right">
                    <span className="text-green-700 font-medium">{tpl.allow.length} allow</span>
                    {tpl.require_approval.length > 0 && (
                      <span className="text-amber-700 font-medium">{tpl.require_approval.length} approval</span>
                    )}
                    <span className="text-red-700 font-medium">{tpl.deny.length} deny</span>
                  </div>
                </div>

                {/* Rule preview when selected */}
                {selectedTemplate?.id === tpl.id && (
                  <div className="mt-3 pt-3 border-t border-blue-200 grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <p className="font-semibold text-green-700 mb-1">Allow</p>
                      {tpl.allow.map((r, i) => (
                        <div key={i} className="flex items-center gap-1">
                          <span className="w-1.5 h-1.5 bg-green-500 rounded-full shrink-0" />
                          <code className="text-green-800">{r.action}</code>
                          <span className="text-gray-400">on {r.resource || '*'}</span>
                        </div>
                      ))}
                      {tpl.require_approval.length > 0 && (
                        <>
                          <p className="font-semibold text-amber-700 mt-2 mb-1">Require Approval</p>
                          {tpl.require_approval.map((r, i) => (
                            <div key={i} className="flex items-center gap-1">
                              <span className="w-1.5 h-1.5 bg-amber-500 rounded-full shrink-0" />
                              <code className="text-amber-800">{r.action}</code>
                              <span className="text-gray-400">on {r.resource || '*'}</span>
                            </div>
                          ))}
                        </>
                      )}
                    </div>
                    <div>
                      <p className="font-semibold text-red-700 mb-1">Deny</p>
                      {tpl.deny.length === 0 ? (
                        <span className="text-gray-400 italic">None</span>
                      ) : tpl.deny.map((r, i) => (
                        <div key={i} className="flex items-center gap-1">
                          <span className="w-1.5 h-1.5 bg-red-500 rounded-full shrink-0" />
                          <code className="text-red-800">{r.action}</code>
                          <span className="text-gray-400">on {r.resource || '*'}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </button>
            ))}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="ghost" onClick={closeTemplateDialog}>Cancel</Button>
            <Button
              onClick={applyTemplate}
              disabled={!selectedTemplate}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Apply Template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ---- AI GENERATION DIALOG ---- */}
      <Dialog open={!!aiDialogAgent} onOpenChange={(open) => { if (!open) closeAiDialog() }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-600" />
              Generate Policy with AI
            </DialogTitle>
            <DialogDescription>
              Describe in plain English what this agent should and shouldn&apos;t be able to do.
              Claude will generate structured allow/deny rules for your review.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1.5">
                What should this agent do? What should it be blocked from?
              </label>
              <textarea
                className="w-full min-h-[120px] rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                placeholder={`Examples:\n• "Allow it to search the web and write to the research database, but never delete records or access payment data"\n• "This agent handles customer support — let it read tickets and send emails, but block any database writes and code execution"\n• "Full read access everywhere, but deny all deletes and deny writes to production"`}
                value={aiDescription}
                onChange={(e) => setAiDescription(e.target.value)}
                disabled={aiGenerating}
              />
              <p className="text-xs text-gray-400 mt-1">{aiDescription.trim().length} characters (min 10)</p>
            </div>

            {/* Error */}
            {aiError && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{aiError}</span>
              </div>
            )}

            {/* AI Draft Preview */}
            {aiDraft && (
              <div className="border border-purple-200 bg-purple-50 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-purple-600" />
                  <p className="text-sm font-semibold text-purple-900">Policy generated — review before applying</p>
                </div>

                <p className="text-sm text-purple-800 italic">{aiDraft.explanation}</p>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-semibold text-green-700 mb-1.5">Allow ({aiDraft.allow.length} rules)</p>
                    {aiDraft.allow.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">None</p>
                    ) : (
                      <div className="space-y-1">
                        {aiDraft.allow.map((r, i) => (
                          <div key={i} className="flex items-center gap-1.5 text-xs">
                            <span className="w-1.5 h-1.5 bg-green-500 rounded-full shrink-0" />
                            <code className="bg-white border border-green-200 px-1.5 py-0.5 rounded text-green-800">{r.action}</code>
                            <span className="text-gray-400">on {r.resource || '*'}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-red-700 mb-1.5">Deny ({aiDraft.deny.length} rules)</p>
                    {aiDraft.deny.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">None</p>
                    ) : (
                      <div className="space-y-1">
                        {aiDraft.deny.map((r, i) => (
                          <div key={i} className="flex items-center gap-1.5 text-xs">
                            <span className="w-1.5 h-1.5 bg-red-500 rounded-full shrink-0" />
                            <code className="bg-white border border-red-200 px-1.5 py-0.5 rounded text-red-800">{r.action}</code>
                            <span className="text-gray-400">on {r.resource || '*'}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="ghost" onClick={closeAiDialog}>
              Cancel
            </Button>
            {!aiDraft ? (
              <Button
                onClick={generatePolicy}
                disabled={aiGenerating || aiDescription.trim().length < 10}
                className="bg-purple-600 hover:bg-purple-700 text-white"
              >
                <Sparkles className="h-4 w-4 mr-2" />
                {aiGenerating ? 'Generating...' : 'Generate Policy'}
              </Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => { setAiDraft(null); setAiError(null) }}>
                  Regenerate
                </Button>
                <Button
                  onClick={applyAiDraft}
                  className="bg-purple-600 hover:bg-purple-700 text-white"
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Apply to Editor
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
