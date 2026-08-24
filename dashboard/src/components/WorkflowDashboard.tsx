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

const STATE_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  pending: { color: 'text-kaihara-muted', bg: 'bg-kaihara-surface', label: 'Pending' },
  running: { color: 'text-kaihara-primary', bg: 'bg-kaihara-primary/10', label: 'Running' },
  waiting_approval: { color: 'text-kaihara-warning', bg: 'bg-kaihara-warning/10', label: 'Approval' },
  completed: { color: 'text-kaihara-success', bg: 'bg-kaihara-success/10', label: 'Done' },
  failed: { color: 'text-kaihara-danger', bg: 'bg-kaihara-danger/10', label: 'Failed' },
  cancelled: { color: 'text-kaihara-muted', bg: 'bg-kaihara-surface', label: 'Cancelled' },
  paused: { color: 'text-kaihara-warning', bg: 'bg-kaihara-warning/10', label: 'Paused' },
  skipped: { color: 'text-kaihara-accent', bg: 'bg-kaihara-accent/10', label: 'Skipped' },
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
  const [showStartForm, setShowStartForm] = useState(false)
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
        setShowStartForm(false)
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
        <div className="animate-spin w-8 h-8 border-2 border-kaihara-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="flex h-full">
      {/* Left: Workflow List */}
      <div className="w-96 border-r border-kaihara-border flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-kaihara-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Workflows</h2>
            <button
              onClick={() => setShowStartForm(!showStartForm)}
              className="btn-primary text-sm"
            >
              + New
            </button>
          </div>

          {/* Start Form */}
          {showStartForm && (
            <div className="card animate-slide-up">
              <h3 className="text-sm font-medium mb-3">Biz Autopilot</h3>
              <div className="space-y-3">
                <select
                  value={startForm.niche}
                  onChange={e => setStartForm(f => ({ ...f, niche: e.target.value }))}
                  className="input"
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
                  className="input"
                />
                <select
                  value={startForm.channel}
                  onChange={e => setStartForm(f => ({ ...f, channel: e.target.value }))}
                  className="input"
                >
                  <option value="email">Email</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="both">Both</option>
                </select>
                <button
                  onClick={handleStartWorkflow}
                  disabled={starting}
                  className="w-full btn-primary disabled:opacity-50"
                >
                  {starting ? 'Starting...' : 'Start Workflow'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Workflow List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {workflows.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">🔄</div>
              <p className="text-kaihara-muted text-sm">No workflows yet</p>
              <p className="text-kaihara-subtle text-xs mt-1">Click "+ New" to start one</p>
            </div>
          ) : (
            workflows.map(wf => {
              const config = STATE_CONFIG[wf.state] || STATE_CONFIG.pending
              const progress = (wf.completed_steps / Math.max(wf.total_steps, 1)) * 100
              
              return (
                <div
                  key={wf.id}
                  onClick={() => fetchWorkflowDetail(wf.id)}
                  className={`card-hover ${
                    selectedWorkflow?.id === wf.id ? 'border-kaihara-primary/50 shadow-glow' : ''
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm truncate">{wf.name}</h3>
                      <p className="text-xs text-kaihara-muted mt-1">
                        {wf.completed_steps}/{wf.total_steps} steps
                      </p>
                    </div>
                    <span className={`badge ${config.bg} ${config.color}`}>
                      {config.label}
                    </span>
                  </div>
                  
                  {/* Progress bar */}
                  <div className="h-1.5 bg-kaihara-surface rounded-full overflow-hidden">
                    <div
                      className="h-full bg-kaihara-primary rounded-full transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between mt-3 text-xs text-kaihara-subtle">
                    <span>{wf.id.slice(0, 12)}</span>
                    <span>{new Date(wf.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Right: Workflow Detail */}
      <div className="flex-1 overflow-y-auto">
        {selectedWorkflow ? (
          <div className="p-6 max-w-4xl mx-auto">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold">{selectedWorkflow.name}</h2>
                <p className="text-sm text-kaihara-muted mt-1">
                  {selectedWorkflow.id} · Created {new Date(selectedWorkflow.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex gap-2">
                {selectedWorkflow.state === 'running' && (
                  <button onClick={() => handlePause(selectedWorkflow.id)} className="btn bg-kaihara-warning/10 text-kaihara-warning hover:bg-kaihara-warning/20">
                    Pause
                  </button>
                )}
                {selectedWorkflow.state === 'paused' && (
                  <button onClick={() => handleResume(selectedWorkflow.id)} className="btn bg-kaihara-success/10 text-kaihara-success hover:bg-kaihara-success/20">
                    Resume
                  </button>
                )}
                {(selectedWorkflow.state === 'running' || selectedWorkflow.state === 'paused' || selectedWorkflow.state === 'pending') && (
                  <button onClick={() => handleCancel(selectedWorkflow.id)} className="btn bg-kaihara-danger/10 text-kaihara-danger hover:bg-kaihara-danger/20">
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {/* Overall Progress */}
            <div className="card mb-6">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium">Progress</span>
                <span className="text-sm text-kaihara-muted">
                  {selectedWorkflow.completed_steps}/{selectedWorkflow.total_steps} steps
                </span>
              </div>
              <div className="h-2 bg-kaihara-surface rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-kaihara-primary to-kaihara-accent rounded-full transition-all duration-500"
                  style={{ width: `${(selectedWorkflow.completed_steps / Math.max(selectedWorkflow.total_steps, 1)) * 100}%` }}
                />
              </div>
              {selectedWorkflow.error && (
                <div className="mt-3 p-3 bg-kaihara-danger/10 border border-kaihara-danger/20 rounded-lg">
                  <p className="text-sm text-kaihara-danger">{selectedWorkflow.error}</p>
                </div>
              )}
            </div>

            {/* Steps Pipeline */}
            <div>
              <h3 className="text-sm font-semibold text-kaihara-muted uppercase tracking-wider mb-4">Pipeline</h3>
              <div className="space-y-3">
                {selectedWorkflow.steps.map((step, idx) => {
                  const config = STATE_CONFIG[step.state] || STATE_CONFIG.pending
                  const icon = STEP_ICONS[step.name] || '📋'
                  
                  return (
                    <div
                      key={step.index}
                      className={`card flex items-center gap-4 ${
                        step.state === 'running' ? 'border-kaihara-primary/50 shadow-glow' :
                        step.state === 'completed' ? 'border-kaihara-success/30' :
                        step.state === 'failed' ? 'border-kaihara-danger/30' :
                        step.state === 'waiting_approval' ? 'border-kaihara-warning/30' : ''
                      }`}
                    >
                      {/* Step Number */}
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${
                        step.state === 'completed' ? 'bg-kaihara-success/10' :
                        step.state === 'running' ? 'bg-kaihara-primary/10 animate-pulse' :
                        'bg-kaihara-surface'
                      }`}>
                        {icon}
                      </div>
                      
                      {/* Step Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{step.name.replace(/_/g, ' ')}</span>
                          <span className="text-xs text-kaihara-subtle">· {step.agent}</span>
                        </div>
                        {step.retry_count > 0 && (
                          <span className="text-xs text-kaihara-warning">Retry: {step.retry_count}</span>
                        )}
                      </div>
                      
                      {/* Status */}
                      <span className={`badge ${config.bg} ${config.color}`}>
                        {config.label}
                      </span>
                      
                      {/* Approval Button */}
                      {step.approval_required && step.state === 'waiting_approval' && (
                        <button
                          onClick={() => handleApprove(selectedWorkflow.id, step.index)}
                          className="btn-primary text-xs"
                        >
                          Approve
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-5xl mb-4">🔄</div>
              <h3 className="text-lg font-medium mb-2">Select a workflow</h3>
              <p className="text-sm text-kaihara-muted">Choose from the list or start a new one</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
