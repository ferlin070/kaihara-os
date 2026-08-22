import { useState, useEffect, useCallback } from 'react'
import { getTasks, getProgress, updateTaskStatus, plan, type Task, type Progress } from '../lib/api'

const columns = [
  { key: 'todo' as const, label: 'TODO', color: 'border-kaihara-muted' },
  { key: 'doing' as const, label: 'DOING', color: 'border-kaihara-warning' },
  { key: 'review' as const, label: 'REVIEW', color: 'border-kaihara-accent' },
  { key: 'done' as const, label: 'DONE', color: 'border-kaihara-success' },
]

export default function TaskBoard() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [progress, setProgress] = useState<Progress | null>(null)
  const [idea, setIdea] = useState('')
  const [planning, setPlanning] = useState(false)

  const fetchTasks = useCallback(async () => {
    try {
      const [tasksRes, progRes] = await Promise.all([
        getTasks(),
        getProgress(),
      ])
      setTasks(tasksRes.tasks || [])
      setProgress(progRes)
    } catch {
      setTasks([])
    }
  }, [])

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
    } catch {
      // error
    }
    setPlanning(false)
  }

  const handleStatusChange = async (taskId: string, status: string) => {
    await updateTaskStatus(taskId, status)
    fetchTasks()
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Progress bar */}
      {progress && progress.total > 0 && (
        <div className="px-4 py-2 border-b border-kaihara-border flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-kaihara-muted">
                {progress.done}/{progress.total} tasks done
              </span>
              <span className="text-kaihara-accent">{progress.percent}%</span>
            </div>
            <div className="h-2 bg-kaihara-border rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-kaihara-primary to-kaihara-accent transition-all duration-500"
                style={{ width: `${progress.percent}%` }}
              />
            </div>
          </div>
          <div className="flex gap-2 text-xs">
            <span className="text-kaihara-warning">Doing: {progress.doing}</span>
            <span className="text-kaihara-muted">Todo: {progress.todo}</span>
            <span className="text-kaihara-success">Done: {progress.done}</span>
          </div>
        </div>
      )}

      {/* Plan input */}
      <div className="px-4 py-2 border-b border-kaihara-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handlePlan()}
            placeholder="Describe what to build... (e.g. 'todo app with reminders')"
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent"
            disabled={planning}
          />
          <button
            onClick={handlePlan}
            disabled={!idea.trim() || planning}
            className="btn-primary disabled:opacity-50"
          >
            {planning ? 'Planning...' : 'Generate PRD'}
          </button>
        </div>
      </div>

      {/* Kanban board */}
      <div className="flex-1 overflow-x-auto p-4">
        {tasks.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-kaihara-muted text-sm mb-2">No tasks yet.</p>
              <p className="text-kaihara-muted text-xs">
                Describe an idea above to generate a PRD and task plan.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-3 h-full">
            {columns.map(col => {
              const colTasks = tasks.filter(t => t.status === col.key)
              return (
                <div key={col.key} className={`bg-kaihara-surface border-t-2 ${col.color} rounded-lg p-3 overflow-y-auto`}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs uppercase tracking-wider font-bold">{col.label}</h3>
                    <span className="text-xs text-kaihara-muted">{colTasks.length}</span>
                  </div>
                  <div className="space-y-2">
                    {colTasks.map(task => (
                      <div key={task.id} className="bg-kaihara-bg border border-kaihara-border rounded p-2.5 group">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-mono text-kaihara-muted">{task.id}</span>
                          <span className="text-xs text-kaihara-muted">{task.phase}</span>
                        </div>
                        <p className="text-sm mb-2">{task.title}</p>
                        <div className="flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                          <span className={`text-xs ${
                            task.complexity === 'complex' ? 'text-kaihara-danger' :
                            task.complexity === 'medium' ? 'text-kaihara-warning' :
                            'text-kaihara-success'
                          }`}>
                            {task.complexity}
                          </span>
                          <select
                            value={task.status}
                            onChange={(e) => handleStatusChange(task.id, e.target.value)}
                            className="bg-kaihara-bg text-xs border border-kaihara-border rounded px-1 py-0.5"
                          >
                            <option value="todo">todo</option>
                            <option value="doing">doing</option>
                            <option value="review">review</option>
                            <option value="done">done</option>
                            <option value="blocked">blocked</option>
                          </select>
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
