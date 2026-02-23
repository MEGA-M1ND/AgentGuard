'use client'

import { useEffect, useState } from 'react'
import { Plus, Copy, Check, Trash2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin-secret-key'

interface Agent {
  agent_id: string
  name: string
  owner_team: string
  environment: string
  is_active: boolean
  created_at: string
  updated_at: string
}

interface CreateAgentResponse {
  agent_id: string
  name: string
  owner_team: string
  environment: string
  is_active: boolean
  created_at: string
  api_key: string
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showApiKeyDialog, setShowApiKeyDialog] = useState(false)
  const [newAgentApiKey, setNewAgentApiKey] = useState<string>('')
  const [newAgentName, setNewAgentName] = useState<string>('')
  const [copiedKey, setCopiedKey] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    owner_team: '',
    environment: 'production'
  })

  const fetchAgents = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`${API_URL}/agents`, {
        headers: {
          'X-ADMIN-KEY': ADMIN_API_KEY
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch agents: ${response.statusText}`)
      }

      const data = await response.json()
      setAgents(data)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to fetch agents'
      setError(errorMsg)
      toast.error('Failed to load agents', { description: errorMsg })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAgents()
  }, [])

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const response = await fetch(`${API_URL}/agents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-ADMIN-KEY': ADMIN_API_KEY
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        throw new Error(`Failed to create agent: ${response.statusText}`)
      }

      const data: CreateAgentResponse = await response.json()

      // Show the API key to the user
      setNewAgentApiKey(data.api_key)
      setNewAgentName(data.name)
      setShowCreateDialog(false)
      setShowApiKeyDialog(true)

      // Reset form
      setFormData({
        name: '',
        owner_team: '',
        environment: 'production'
      })

      // Refresh agents list
      fetchAgents()

      toast.success('Agent created successfully!', {
        description: `Created ${data.name}. Don't forget to save the API key!`
      })
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to create agent'
      setError(errorMsg)
      toast.error('Failed to create agent', { description: errorMsg })
    }
  }

  const handleDeleteAgent = async (agentId: string) => {
    if (!confirm('Are you sure you want to delete this agent? This action cannot be undone.')) {
      return
    }

    try {
      const response = await fetch(`${API_URL}/agents/${agentId}`, {
        method: 'DELETE',
        headers: {
          'X-ADMIN-KEY': ADMIN_API_KEY
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to delete agent: ${response.statusText}`)
      }

      // Refresh agents list
      fetchAgents()

      toast.success('Agent deleted successfully', {
        description: 'The agent has been removed from the system.'
      })
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete agent'
      setError(errorMsg)
      toast.error('Failed to delete agent', { description: errorMsg })
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(true)
      setTimeout(() => setCopiedKey(false), 2000)
      toast.success('Copied to clipboard!')
    } catch (err) {
      console.error('Failed to copy:', err)
      toast.error('Failed to copy to clipboard')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agents</h1>
          <p className="text-gray-600 mt-1">Manage your AI agents and their identities</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={fetchAgents}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Agent
          </Button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading agents...</p>
        </div>
      )}

      {/* Agents Grid */}
      {!loading && agents.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg border">
          <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500 mb-4">No agents found</p>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Your First Agent
          </Button>
        </div>
      )}

      {!loading && agents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <Card key={agent.agent_id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="text-xl">{agent.name}</CardTitle>
                    <CardDescription className="mt-1">
                      {agent.owner_team}
                    </CardDescription>
                  </div>
                  <Badge variant={agent.is_active ? 'success' : 'destructive'}>
                    {agent.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 uppercase font-medium">Agent ID</p>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-sm bg-gray-100 px-2 py-1 rounded flex-1 truncate">
                        {agent.agent_id}
                      </code>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyToClipboard(agent.agent_id)}
                      >
                        {copiedKey ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-gray-500 uppercase font-medium">Environment</p>
                    <Badge variant="secondary" className="mt-1">
                      {agent.environment}
                    </Badge>
                  </div>

                  <div>
                    <p className="text-xs text-gray-500 uppercase font-medium">Created</p>
                    <p className="text-sm text-gray-700 mt-1">{formatDate(agent.created_at)}</p>
                  </div>

                  <div className="pt-4 border-t flex gap-2">
                    <Button
                      variant="destructive"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleDeleteAgent(agent.agent_id)}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Agent Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Agent</DialogTitle>
            <DialogDescription>
              Create a new AI agent with a unique identity and API key.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateAgent}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Agent Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., CustomerSupportBot"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="owner_team">Owner Team *</Label>
                <Input
                  id="owner_team"
                  placeholder="e.g., Customer Success"
                  value={formData.owner_team}
                  onChange={(e) => setFormData({ ...formData, owner_team: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="environment">Environment *</Label>
                <select
                  id="environment"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={formData.environment}
                  onChange={(e) => setFormData({ ...formData, environment: e.target.value })}
                  required
                >
                  <option value="production">Production</option>
                  <option value="staging">Staging</option>
                  <option value="development">Development</option>
                </select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                Cancel
              </Button>
              <Button type="submit">Create Agent</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* API Key Display Dialog */}
      <Dialog open={showApiKeyDialog} onOpenChange={setShowApiKeyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Agent Created Successfully!</DialogTitle>
            <DialogDescription>
              Your agent <strong>{newAgentName}</strong> has been created. Save the API key below - you won't be able to see it again.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>API Key</Label>
            <div className="flex items-center gap-2 mt-2">
              <Input
                readOnly
                value={newAgentApiKey}
                className="font-mono text-sm"
              />
              <Button
                size="sm"
                onClick={() => copyToClipboard(newAgentApiKey)}
              >
                {copiedKey ? (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </>
                )}
              </Button>
            </div>
            <p className="text-sm text-amber-600 mt-3 bg-amber-50 p-3 rounded-lg border border-amber-200">
              ⚠️ Important: Store this API key securely. You won't be able to retrieve it later.
            </p>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowApiKeyDialog(false)}>
              I've Saved the Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// Import Users icon for empty state
import { Users } from 'lucide-react'
