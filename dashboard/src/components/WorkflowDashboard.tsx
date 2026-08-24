import { useState, useEffect, useCallback } from 'react'

interface WorkflowStep {
  index: number
  name: string
  agent: string
  state: string
  approval_required: boolean
  approval_status: string | null
  retry_count: number
}

interface Workflow {
  id: string
  name: string
  template: string
  state: string
  total_steps: number
  completed_steps: number
  current_step: string | null
  error: string | null
  steps: WorkflowStep[]
  created_at: string
  updated_at: string
}

interface WorkflowTemplate {
  name: string
  description: string
}

const STATE_COLORS: Record<string, string> = {
  pending: 'bg-gray-500',
  running: 'bg-blue-500',
  waiting_approval: 'bg-yellow-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-600',
  paused: 'bg-orange-500',
  skipped: 'bg-purple-500',
}

const STEP_ICONS: Record<string, string> = {
  find_businesses: '🔍',
  analyze_business: '📊',
  generate_demo: '🌐',
  outreach: '📧',
  win_job: '✅',
  build_project: '🏗️',
  deploy_site: '🚀',
  close_payment: '💰',
}

export default function WorkflowDashboard() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [startForm, setStartForm] = useState({
    niche: 'restoran',
    location: 'Johor Bahru',
    channel: 'email',
  })

  const fetchWorkflows = useCallback(async () => {
    try {
      const res = await fetch('/api/workflow')
      const data = await res.json()
      setWorkflows(data.workflows || [])
    } catch (err) {
      console.error('Failed to fetch workflows:', err)
    }
  }, [])

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch('/api/workflow/templates')
      const data = await res.json()
      setTemplates(data.templates || [])
    } catch (err) {
      console.error('Failed to fetch templates:', err)
    }
  }, [])

  const fetchWorkflowDetail = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/workflow/${id}`)
      const data = await res.json()
      setSelectedWorkflow(data)
    } catch (err) {
      console.error('Failed to fetch workflow detail:', err)
    }
  }, [])

  useEffect(() => {
    fetchWorkflows()
    fetchTemplates()
    setLoading(false)
  }, [fetchWorkflows, fetchTemplates])

  // Auto-refresh running workflows
  useEffect(() => {
    const interval = setInterval(() => {
      const hasRunning = workflows.some(w => w.state === 'running' || w.state === 'pending')
      if (hasRunning) {
        fetchWorkflows()
        if (selectedWorkflow) {
          fetchWorkflowDetail(selectedWorkflow.id)
        }
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [workflows, selectedWorkflow, fetchWorkflows, fetchWorkflowDetail])

  const handleStartWorkflow = async () => {
    setStarting(true)
    try {
      const res = await fetch('/api/workflow/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template: 'biz_autopilot',
          input_data: {
            niche: startForm.niche,
            location: startForm.location,
            outreach_channel: startForm.channel,
          },
        }),
      })
      const data = await res.json()
      if (data.workflow_id) {
        fetchWorkflows()
        fetchWorkflowDetail(data.workflow_id)
      }
    } catch (err) {
      console.error('Failed to start workflow:', err)
    }
    setStarting(false)
  }

  const handlePause = async (id: string) => {
    await fetch(`/api/workflow/${id}/pause`, { method: 'POST' })
    fetchWorkflows()
    fetchWorkflowDetail(id)
  }

  const handleResume = async (id: string) => {
    await fetch(`/api/workflow/${id}/resume`, { method: 'POST' })
    fetchWorkflows()
    fetchWorkflowDetail(id)
  }

  const handleCancel = async (id: string) => {
    if (!confirm('Cancel this workflow?')) return
    await fetch(`/api/workflow/${id}/cancel`, { method: 'POST' })
    fetchWorkflows()
    fetchWorkflowDetail(id)
  }

  const handleApprove = async (id: string, stepIndex: number) => {
    await fetch(`/api/workflow/${id}/approve/${stepIndex}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved: true }),
    })
    fetchWorkflowDetail(id)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin w-8 h-8 border-2 border-kaihara-accent border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Left: Workflow List */}
      <div className="w-1/3 border-r border-kaihara-border p-4 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Workflows</h2>
          <button
            onClick={() => {
              const form = document.getElementById('start-form')
              form?.classList.toggle('hidden')
            }}
            className="px-3 py-1 bg-kaihara-accent text-white rounded text-sm hover:opacity-80"
          >
            + Start New
          </button>
        </div>

        {/* Start Form */}
        <div id="start-form" className="hidden mb-4 p-4 bg-kaihara-card rounded-lg border border-kaihara-border">
          <h3 className="text-sm font-bold mb-3">Biz Autopilot</h3>
          <div className="space-y-2">
            <select
              value={startForm.niche}
              onChange={e => setStartForm(f => ({ ...f, niche: e.target.value }))}
              className="w-full p-2 bg-kaihara-bg border border-kaihara-border rounded text-sm"
            >
              <option value="restoran">Restoran</option>
              <option value="salon">Salon</option>
              <option value="kedai">Kedai</option>
              <option value="klinik">Klinik</option>
              <option value="automotive">Automotive</option>
            </select>
            <input
              type="text"
              placeholder="Lokasi"
              value={startForm.location}
              onChange={e => setStartForm(f => ({ ...f, location: e.target.value }))}
              className="w-full p-2 bg-kaihara-bg border border-kaihara-border rounded text-sm"
            />
            <select
              value={startForm.channel}
              onChange={e => setStartForm(f => ({ ...f, channel: e.target.value }))}
              className="w-full p-2 bg-kaihara-bg border border-kaihara-border rounded text-sm"
            >
              <option value="email">Email</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="both">Both</option>
            </select>
            <button
              onClick={handleStartWorkflow}
              disabled={starting}
              className="w-full py-2 bg-kaihara-accent text-white rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
            >
              {starting ? 'Starting...' : 'Start Workflow'}
            </button>
          </div>
        </div>

        {/* Workflow List */}
        <div className="space-y-2">
          {workflows.length === 0 ? (
            <p className="text-kaihara-muted text-sm text-center py-8">
              No workflows yet. Click "Start New" to begin.
            </p>
          ) : (
            workflows.map(wf => (
              <div
                key={wf.id}
                onClick={() => fetchWorkflowDetail(wf.id)}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedWorkflow?.id === wf.id
                    ? 'border-kaihara-accent bg-kaihara-accent/10'
                    : 'border-kaihara-border hover:border-kaihara-accent/50'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{wf.name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs text-white ${STATE_COLORS[wf.state] || 'bg-gray-500'}`}>
                    {wf.state}
                  </span>
                </div>
                <div className="text-xs text-kaihara-muted">
                  {wf.completed_steps}/{wf.total_steps} steps • {wf.id.slice(0, 12)}
                </div>
                {/* Progress bar */}
                <div className="mt-2 h-1 bg-kaihara-bg rounded-full overflow-hidden">
                  <div
                    className="h-full bg-kaihara-accent transition-all"
                    style={{ width: `${(wf.completed_steps / Math.max(wf.total_steps, 1)) * 100}%` }}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right: Workflow Detail */}
      <div className="flex-1 p-6 overflow-y-auto">
        {selectedWorkflow ? (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold">{selectedWorkflow.name}</h2>
                <p className="text-sm text-kaihara-muted">
                  {selectedWorkflow.id} • Created: {new Date(selectedWorkflow.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex gap-2">
                {selectedWorkflow.state === 'running' && (
                  <button
                    onClick={() => handlePause(selectedWorkflow.id)}
                    className="px-3 py-1 bg-yellow-500 text-white rounded text-sm"
                  >
                    Pause
                  </button>
                )}
                {selectedWorkflow.state === 'paused' && (
                  <button
                    onClick={() => handleResume(selectedWorkflow.id)}
                    className="px-3 py-1 bg-green-500 text-white rounded text-sm"
                  >
                    Resume
                  </button>
                )}
                {(selectedWorkflow.state === 'running' || selectedWorkflow.state === 'paused' || selectedWorkflow.state === 'pending') && (
                  <button
                    onClick={() => handleCancel(selectedWorkflow.id)}
                    className="px-3 py-1 bg-red-500 text-white rounded text-sm"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {/* Overall Progress */}
            <div className="mb-6 p-4 bg-kaihara-card rounded-lg border border-kaihara-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Progress</span>
                <span className="text-sm text-kaihara-muted">
                  {selectedWorkflow.completed_steps}/{selectedWorkflow.total_steps} steps
                </span>
              </div>
              <div className="h-2 bg-kaihara-bg rounded-full overflow-hidden">
                <div
                  className="h-full bg-kaihara-accent transition-all"
                  style={{ width: `${(selectedWorkflow.completed_steps / Math.max(selectedWorkflow.total_steps, 1)) * 100}%` }}
                />
              </div>
              {selectedWorkflow.error && (
                <p className="mt-2 text-sm text-red-500">Error: {selectedWorkflow.error}</p>
              )}
            </div>

            {/* Steps */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-kaihara-muted uppercase">Steps</h3>
              {selectedWorkflow.steps.map(step => (
                <div
                  key={step.index}
                  className={`flex items-center gap-4 p-3 rounded-lg border ${
                    step.state === 'completed'
                      ? 'border-green-500/30 bg-green-500/5'
                      : step.state === 'running'
                      ? 'border-blue-500/30 bg-blue-500/5'
                      : step.state === 'failed'
                      ? 'border-red-500/30 bg-red-500/5'
                      : step.state === 'waiting_approval'
                      ? 'border-yellow-500/30 bg-yellow-500/5'
                      : 'border-kaihara-border'
                  }`}
                >
                  <span className="text-2xl">{STEP_ICONS[step.name] || '📋'}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{step.name}</span>
                      <span className="text-xs text-kaihara-muted">({step.agent})</span>
                    </div>
                    {step.retry_count > 0 && (
                      <span className="text-xs text-yellow-500">Retry: {step.retry_count}</span>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs text-white ${STATE_COLORS[step.state] || 'bg-gray-500'}`}>
                    {step.state}
                  </span>
                  {step.approval_required && step.state === 'waiting_approval' && (
                    <button
                      onClick={() => handleApprove(selectedWorkflow.id, step.index)}
                      className="px-2 py-1 bg-green-500 text-white rounded text-xs"
                    >
                      Approve
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-kaihara-muted">
            <div className="text-center">
              <p className="text-4xl mb-4">🔄</p>
              <p className="text-lg font-medium">Select a workflow to view details</p>
              <p className="text-sm">Or start a new one from the left panel</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
