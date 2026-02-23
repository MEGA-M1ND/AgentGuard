'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Play, CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || 'admin-secret-key'

interface Agent {
  agent_id: string
  name: string
  owner_team: string
  environment: string
  is_active: boolean
}

interface TestResult {
  allowed: boolean
  reason: string
  action: string
  resource: string
  timestamp: string
}

// Sample actions for quick testing
const SAMPLE_ACTIONS = [
  { action: 'read:ticket', resource: 'ticket-12345', description: 'Read support ticket' },
  { action: 'delete:ticket', resource: 'ticket-12345', description: 'Delete support ticket' },
  { action: 'read:customer', resource: 'customer-abc123', description: 'Read customer data' },
  { action: 'read:payment', resource: 'payment-info', description: 'Read payment info' },
  { action: 'query:database', resource: 'analytics/sales', description: 'Query sales database' },
  { action: 'delete:content', resource: 'user-generated/spam', description: 'Delete user content' },
  { action: 'send:email', resource: 'support/notification', description: 'Send email' },
  { action: 'update:customer', resource: 'customer-xyz', description: 'Update customer' },
]

export default function TestPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [agentApiKey, setAgentApiKey] = useState<string>('')
  const [action, setAction] = useState('')
  const [resource, setResource] = useState('')
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [testHistory, setTestHistory] = useState<TestResult[]>([])

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/agents`, {
        headers: { 'X-ADMIN-KEY': ADMIN_API_KEY }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch agents: ${response.statusText}`)
      }

      const data = await response.json()
      const activeAgents = data.filter((a: Agent) => a.is_active)
      setAgents(activeAgents)

      // Auto-select first agent if available
      if (activeAgents.length > 0) {
        setSelectedAgent(activeAgents[0].agent_id)
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err)
      toast.error('Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  const handleTestAction = async () => {
    if (!selectedAgent) {
      toast.error('Please select an agent')
      return
    }

    if (!agentApiKey.trim()) {
      toast.error('Please enter the agent\'s API key')
      return
    }

    if (!action.trim()) {
      toast.error('Please enter an action')
      return
    }

    try {
      setTesting(true)
      setTestResult(null)

      // Step 1: Call enforce endpoint with agent's API key
      const enforceResponse = await fetch(`${API_URL}/enforce`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Agent-Key': agentApiKey.trim()
        },
        body: JSON.stringify({
          action: action.trim(),
          resource: resource.trim() || undefined,
          context: {
            source: 'test-action-page',
            timestamp: new Date().toISOString()
          }
        })
      })

      if (!enforceResponse.ok) {
        const errorData = await enforceResponse.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `Enforcement check failed with status ${enforceResponse.status}`)
      }

      const enforceResult = await enforceResponse.json()

      const result: TestResult = {
        allowed: enforceResult.allowed,
        reason: enforceResult.reason,
        action: action.trim(),
        resource: resource.trim() || 'N/A',
        timestamp: new Date().toISOString()
      }

      setTestResult(result)
      setTestHistory([result, ...testHistory.slice(0, 9)]) // Keep last 10 results

      // Step 2: Create audit log entry using agent's API key
      try {
        await fetch(`${API_URL}/logs`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Agent-Key': agentApiKey.trim()
          },
          body: JSON.stringify({
            action: action.trim(),
            resource: resource.trim() || undefined,
            allowed: enforceResult.allowed,
            result: enforceResult.allowed ? 'success' : 'denied',
            context: {
              source: 'test-action-page',
              test: true
            },
            metadata: {
              test: true,
              reason: enforceResult.reason
            }
          })
        })
      } catch (logErr) {
        console.warn('Failed to create audit log:', logErr)
        // Don't fail the test if log creation fails
      }

      // Show toast notification
      if (enforceResult.allowed) {
        toast.success('Action Allowed!', {
          description: enforceResult.reason
        })
      } else {
        toast.error('Action Denied!', {
          description: enforceResult.reason
        })
      }
    } catch (err) {
      console.error('Test failed:', err)
      toast.error('Test failed', {
        description: err instanceof Error ? err.message : 'Unknown error'
      })
    } finally {
      setTesting(false)
    }
  }

  const loadSampleAction = (sample: typeof SAMPLE_ACTIONS[0]) => {
    setAction(sample.action)
    setResource(sample.resource)
    toast.info('Sample action loaded', { description: sample.description })
  }

  const selectedAgentData = agents.find(a => a.agent_id === selectedAgent)

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Test Actions</h1>
        <p className="text-gray-600 mt-1">
          Test agent permissions in real-time and see policy enforcement in action
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Test Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Test Form Card */}
          <Card>
            <CardHeader>
              <CardTitle>Run Policy Test</CardTitle>
              <CardDescription>
                Select an agent and test if an action is allowed by their policy
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Agent Selection */}
              <div className="space-y-2">
                <Label htmlFor="agent">Select Agent</Label>
                {loading ? (
                  <div className="text-sm text-gray-500">Loading agents...</div>
                ) : agents.length === 0 ? (
                  <div className="text-sm text-gray-500">
                    No active agents found. Create an agent first.
                  </div>
                ) : (
                  <>
                    <select
                      id="agent"
                      value={selectedAgent}
                      onChange={(e) => setSelectedAgent(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {agents.map((agent) => (
                        <option key={agent.agent_id} value={agent.agent_id}>
                          {agent.name} ({agent.owner_team})
                        </option>
                      ))}
                    </select>
                    {selectedAgentData && (
                      <div className="flex gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">
                          {selectedAgentData.environment}
                        </Badge>
                        <Badge variant={selectedAgentData.is_active ? 'success' : 'secondary'} className="text-xs">
                          {selectedAgentData.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* API Key Input */}
              <div className="space-y-2">
                <Label htmlFor="apiKey">
                  Agent API Key <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder="agk_xxxxxxxxxxxxx"
                  value={agentApiKey}
                  onChange={(e) => setAgentApiKey(e.target.value)}
                  disabled={testing}
                />
                <p className="text-xs text-gray-500">
                  Save the API key when creating an agent. The demo agents' keys are shown in the seeder output.
                </p>
              </div>

              {/* Action Input */}
              <div className="space-y-2">
                <Label htmlFor="action">
                  Action <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="action"
                  placeholder="e.g., read:file, delete:database, send:email"
                  value={action}
                  onChange={(e) => setAction(e.target.value)}
                  disabled={testing}
                />
                <p className="text-xs text-gray-500">
                  Format: verb:noun (e.g., read:ticket, delete:content)
                </p>
              </div>

              {/* Resource Input */}
              <div className="space-y-2">
                <Label htmlFor="resource">Resource (Optional)</Label>
                <Input
                  id="resource"
                  placeholder="e.g., ticket-12345, customer-data.pdf"
                  value={resource}
                  onChange={(e) => setResource(e.target.value)}
                  disabled={testing}
                />
                <p className="text-xs text-gray-500">
                  Specific resource to test against (supports wildcards in policy)
                </p>
              </div>

              {/* Test Button */}
              <Button
                onClick={handleTestAction}
                disabled={testing || !selectedAgent || !agentApiKey.trim() || !action.trim()}
                className="w-full"
                size="lg"
              >
                {testing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Test Action
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Current Test Result */}
          {testResult && (
            <Card className={testResult.allowed ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'}>
              <CardHeader>
                <div className="flex items-center gap-3">
                  {testResult.allowed ? (
                    <CheckCircle2 className="h-8 w-8 text-green-600" />
                  ) : (
                    <XCircle className="h-8 w-8 text-red-600" />
                  )}
                  <div>
                    <CardTitle className={testResult.allowed ? 'text-green-900' : 'text-red-900'}>
                      {testResult.allowed ? 'Action Allowed' : 'Action Denied'}
                    </CardTitle>
                    <CardDescription className={testResult.allowed ? 'text-green-700' : 'text-red-700'}>
                      {testResult.reason}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-semibold">Action:</span>{' '}
                    <code className="bg-white px-2 py-0.5 rounded">{testResult.action}</code>
                  </div>
                  <div>
                    <span className="font-semibold">Resource:</span>{' '}
                    <code className="bg-white px-2 py-0.5 rounded">{testResult.resource}</code>
                  </div>
                  <div>
                    <span className="font-semibold">Agent:</span> {selectedAgentData?.name}
                  </div>
                  <div className="text-xs text-gray-600 mt-3">
                    An audit log entry has been created for this test.
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Test History */}
          {testHistory.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Recent Tests</CardTitle>
                <CardDescription>Last 10 policy tests</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {testHistory.map((result, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        {result.allowed ? (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600" />
                        )}
                        <div>
                          <code className="text-xs bg-white px-2 py-0.5 rounded">
                            {result.action}
                          </code>
                          {result.resource !== 'N/A' && (
                            <span className="text-xs text-gray-500 ml-2">
                              → {result.resource}
                            </span>
                          )}
                        </div>
                      </div>
                      <Badge variant={result.allowed ? 'success' : 'destructive'} className="text-xs">
                        {result.allowed ? 'ALLOWED' : 'DENIED'}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Quick Actions */}
        <div className="space-y-6">
          {/* Sample Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Sample Actions</CardTitle>
              <CardDescription>Quick test scenarios</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {SAMPLE_ACTIONS.map((sample, index) => (
                  <button
                    key={index}
                    onClick={() => loadSampleAction(sample)}
                    disabled={testing}
                    className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="font-medium text-sm text-gray-900">
                      {sample.description}
                    </div>
                    <code className="text-xs text-gray-600">
                      {sample.action}
                    </code>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Help Card */}
          <Card className="bg-blue-50 border-blue-200">
            <CardHeader>
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <CardTitle className="text-blue-900">How It Works</CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-blue-900 space-y-2">
              <p>
                1. Select an agent with configured policies
              </p>
              <p>
                2. Enter the agent's API key (from creation or seeder output)
              </p>
              <p>
                3. Enter an action (like <code className="bg-white px-1 rounded">read:file</code>)
              </p>
              <p>
                4. Optionally specify a resource
              </p>
              <p>
                5. Click "Test Action" to check if it's allowed
              </p>
              <p className="pt-2 border-t border-blue-200">
                Each test creates an audit log entry you can view in the Logs page
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
