import { useState, useEffect, useCallback } from 'react'
import {
  getTasks, getProgress, updateTaskStatus, deleteTask, bulkUpdateTasks,
  assignTask, plan, type Task, type Progress,
} from '../lib/api'

const columns = [
  { key: 'todo' as const, label: 'TODO', color: 'border-kaihara-muted' },
  { key: 'doing' as const, label: 'DOING', color: 'border-kaihara-warning' },
  { key: 'review' as const, label: 'REVIEW', color: 'border-kaihara-accent' },
  { key: 'done' as const, label: 'DONE', color: 'border-kaihara-success' },
]

const agents = ['coding', 'marketing', 'security', 'research', 'deploy', 'kaihara']

export default function TaskBoard() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [progress, setProgress] = useState<Progress | null>(null)
  const [idea, setIdea] = useState('')
  const [planning, setPlanning] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [filterPhase, setFilterPhase] = useState('')
  const [showExport, setShowExport] = useState(false)

  const fetchTasks = useCallback(async () => {
    try {
      const [tasksRes, progRes] = await Promise.all([
        getTasks(undefined, filterPhase || undefined),
        getProgress(),
      ])
      setTasks(tasksRes.tasks || [])
      setProgress(progRes)
    } catch {
      setTasks([])
    }
  }, [filterPhase])

  useEffect(() => {
    fetchTasks()
    const interval = setInterval(fetchTasks, 10000)
    return () => clearInterval(interval)
  }, [fetchTasks])

  const handlePlan = async () => {
    if (!idea.trim() || planning) return
    setPlanning(true)
    try {
      await plan(idea.trim())
      setIdea('')
      fetchTasks()
    } catch {}
    setPlanning(false)
  }

  const handleStatusChange = async (taskId: string, status: string) => {
    await updateTaskStatus(taskId, status)
    fetchTasks()
  }

  const handleDelete = async (taskId: string) => {
    if (!confirm('Delete this task?')) return
    await deleteTask(taskId)
    fetchTasks()
  }

  const handleBulkStatus = async (status: string) => {
    if (selected.size === 0) return
    await bulkUpdateTasks(Array.from(selected), status)
    setSelected(new Set())
    fetchTasks()
  }

  const handleAssign = async (taskId: string, agent: string) => {
    await assignTask(taskId, agent)
    fetchTasks()
  }

  const toggleSelect = (taskId: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(taskId) ? next.delete(taskId) : next.add(taskId)
      return next
    })
  }

  const selectAll = (status: string) => {
    const ids = (tasks || []).filter(t => t.status === status).map(t => t.id)
    setSelected(new Set(ids))
  }

  const exportTasks = () => {
    const md = (tasks || []).map(t =>
      `- [${t.status === 'done' ? 'x' : ' '}] **${t.title}** (${t.phase}) — ${t.complexity}${t.assigned_agent ? ` → ${t.assigned_agent}` : ''}`
    ).join('\n')
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'tasks.md'; a.click()
    URL.revokeObjectURL(url)
  }

  const phases = [...new Set((tasks || []).map(t => t.phase))]

  return (
    <div className="flex-1 flex flex-col">
      {/* Progress bar */}
      {progress && progress.total > 0 && (
        <div className="px-4 py-2 border-b border-kaihara-border">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-kaihara-muted">{progress.done}/{progress.total} tasks done</span>
            <span className="text-kaihara-accent">{progress.percent}%</span>
          </div>
          <div className="h-2 bg-kaihara-border rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-kaihara-primary to-kaihara-accent transition-all duration-500"
              style={{ width: `${progress.percent}%` }} />
          </div>
          {/* Phase breakdown */}
          <div className="flex flex-wrap gap-3 mt-2">
            {Object.entries(progress.phases).map(([phase, data]) => (
              <div key={phase} className="text-xs">
                <span className="text-kaihara-muted">{phase}: </span>
                <span className="text-kaihara-success">{data.done}</span>
                <span className="text-kaihara-muted">/{data.total}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plan input */}
      <div className="px-4 py-2 border-b border-kaihara-border">
        <div className="flex gap-2">
          <input type="text" value={idea} onChange={(e) => setIdea(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handlePlan()}
            placeholder="Describe what to build... (e.g. 'todo app with reminders')"
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent"
            disabled={planning} />
          <button onClick={handlePlan} disabled={!idea.trim() || planning}
            className="btn-primary disabled:opacity-50">
            {planning ? 'Planning...' : 'Generate PRD'}
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="px-4 py-2 border-b border-kaihara-border flex items-center gap-2">
        {/* Phase filter */}
        <select value={filterPhase} onChange={e => setFilterPhase(e.target.value)}
          className="bg-kaihara-bg border border-kaihara-border rounded px-2 py-1 text-xs">
          <option value="">All Phases</option>
          {phases.map(p => <option key={p} value={p}>{p}</option>)}
        </select>

        {/* Bulk actions */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2 ml-2">
            <span className="text-xs text-kaihara-accent">{selected.size} selected</span>
            <button onClick={() => handleBulkStatus('doing')} className="text-xs px-2 py-0.5 bg-kaihara-warning/20 text-kaihara-warning rounded">→ Doing</button>
            <button onClick={() => handleBulkStatus('done')} className="text-xs px-2 py-0.5 bg-kaihara-success/20 text-kaihara-success rounded">→ Done</button>
            <button onClick={() => handleBulkStatus('blocked')} className="text-xs px-2 py-0.5 bg-kaihara-danger/20 text-kaihara-danger rounded">→ Blocked</button>
            <button onClick={() => setSelected(new Set())} className="text-xs text-kaihara-muted">Clear</button>
          </div>
        )}

        <div className="flex-1" />

        {/* Export */}
        <button onClick={exportTasks} className="text-xs px-2 py-1 bg-kaihara-border text-kaihara-muted rounded hover:text-kaihara-text">
          📤 Export
        </button>
      </div>

      {/* Kanban board */}
      <div className="flex-1 overflow-x-auto p-4">
        {(tasks || []).length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-kaihara-muted text-sm mb-2">No tasks yet.</p>
              <p className="text-kaihara-muted text-xs">Describe an idea above to generate a PRD and task plan.</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-3 h-full">
            {columns.map(col => {
              const colTasks = (tasks || []).filter(t => t.status === col.key)
              return (
                <div key={col.key} className={`bg-kaihara-surface border-t-2 ${col.color} rounded-lg p-3 overflow-y-auto`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <h3 className="text-xs uppercase tracking-wider font-bold">{col.label}</h3>
                      <span className="text-xs text-kaihara-muted">{colTasks.length}</span>
                    </div>
                    <button onClick={() => selectAll(col.key)} className="text-xs text-kaihara-muted hover:text-kaihara-accent" title="Select all">
                      ☑
                    </button>
                  </div>
                  <div className="space-y-2">
                    {colTasks.map(task => (
                      <div key={task.id}
                        className={`bg-kaihara-bg border rounded p-2.5 group transition-colors ${
                          selected.has(task.id) ? 'border-kaihara-accent' : 'border-kaihara-border hover:border-kaihara-accent/50'
                        }`}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <input type="checkbox" checked={selected.has(task.id)}
                              onChange={() => toggleSelect(task.id)}
                              className="w-3 h-3 accent-kaihara-accent" />
                            <span className="text-xs font-mono text-kaihara-muted">{task.id}</span>
                          </div>
                          <span className="text-xs text-kaihara-muted">{task.phase}</span>
                        </div>
                        <p className="text-sm mb-2">{task.title}</p>

                        {/* Assignment */}
                        {task.assigned_agent && (
                          <div className="text-xs text-kaihara-accent mb-1">→ {task.assigned_agent}</div>
                        )}

                        <div className="flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                          <span className={`text-xs ${
                            task.complexity === 'complex' ? 'text-kaihara-danger' :
                            task.complexity === 'medium' ? 'text-kaihara-warning' :
                            'text-kaihara-success'
                          }`}>
                            {task.complexity}
                          </span>
                          <div className="flex items-center gap-1">
                            {/* Assign dropdown */}
                            <select value={task.assigned_agent || ''}
                              onChange={e => handleAssign(task.id, e.target.value)}
                              className="bg-kaihara-bg text-xs border border-kaihara-border rounded px-1 py-0.5 max-w-20"
                              title="Assign to agent">
                              <option value="">--</option>
                              {agents.map(a => <option key={a} value={a}>{a}</option>)}
                            </select>
                            {/* Status dropdown */}
                            <select value={task.status}
                              onChange={(e) => handleStatusChange(task.id, e.target.value)}
                              className="bg-kaihara-bg text-xs border border-kaihara-border rounded px-1 py-0.5">
                              <option value="todo">todo</option>
                              <option value="doing">doing</option>
                              <option value="review">review</option>
                              <option value="done">done</option>
                              <option value="blocked">blocked</option>
                            </select>
                            {/* Delete */}
                            <button onClick={() => handleDelete(task.id)}
                              className="text-xs text-kaihara-danger/50 hover:text-kaihara-danger px-1"
                              title="Delete task">✕</button>
                          </div>
                        </div>
                      </div>
                    ))}
                    {colTasks.length === 0 && (
                      <p className="text-xs text-kaihara-muted text-center py-4">Empty</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
