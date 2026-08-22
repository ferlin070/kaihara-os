import { useState, useEffect, useCallback } from 'react'
import { getSkills, getSkillStats, createSkill, type Skill } from '../lib/api'

const categoryColors: Record<string, string> = {
  skills: 'text-kaihara-accent',
  tools: 'text-kaihara-primary',
  'ui-ux': 'text-purple-400',
  coding: 'text-kaihara-success',
  security: 'text-kaihara-danger',
  memory: 'text-kaihara-warning',
  output: 'text-kaihara-accent',
  workflow: 'text-blue-400',
  finance: 'text-green-400',
  custom: 'text-kaihara-muted',
}

export default function SkillBrowser() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [stats, setStats] = useState<{ total: number; categories: Record<string, number> } | null>(null)
  const [filter, setFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [creating, setCreating] = useState(false)
  const [newSkillDesc, setNewSkillDesc] = useState('')

  const fetchSkills = useCallback(async () => {
    try {
      const [skillsRes, statsRes] = await Promise.all([
        getSkills(filter || undefined, search || undefined),
        getSkillStats(),
      ])
      setSkills(skillsRes.skills || [])
      setStats(statsRes)
    } catch {
      setSkills([])
    }
  }, [filter, search])

  useEffect(() => {
    fetchSkills()
  }, [fetchSkills])

  const handleCreate = async () => {
    if (!newSkillDesc.trim() || creating) return
    setCreating(true)
    try {
      await createSkill(newSkillDesc.trim())
      setNewSkillDesc('')
      fetchSkills()
    } catch {}
    setCreating(false)
  }

  const categories = stats ? Object.keys(stats.categories) : []

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold uppercase tracking-wide">Skill Browser</h2>
          {stats && (
            <span className="text-xs text-kaihara-muted">{stats.total} skills installed</span>
          )}
        </div>

        {/* Search */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search skills..."
          className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent mb-2"
        />

        {/* Category filter */}
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => setFilter('')}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              !filter ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'
            }`}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                filter === cat ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'
              }`}
            >
              {cat} ({stats?.categories[cat] || 0})
            </button>
          ))}
        </div>
      </div>

      {/* Create skill */}
      <div className="px-4 py-2 border-b border-kaihara-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={newSkillDesc}
            onChange={(e) => setNewSkillDesc(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="Describe a skill to create..."
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent"
            disabled={creating}
          />
          <button
            onClick={handleCreate}
            disabled={!newSkillDesc.trim() || creating}
            className="btn-primary disabled:opacity-50"
          >
            {creating ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>

      {/* Skills list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {skills.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-kaihara-muted text-sm">No skills found.</p>
          </div>
        ) : (
          skills.map(skill => (
            <div key={skill.id} className="hud-panel hover:border-kaihara-accent transition-colors cursor-pointer">
              <div className="flex items-start justify-between mb-1">
                <div>
                  <h3 className="text-sm font-medium">{skill.name}</h3>
                  <span className={`text-xs ${categoryColors[skill.category] || 'text-kaihara-muted'}`}>
                    {skill.category}
                  </span>
                </div>
                <span className="text-xs font-mono text-kaihara-muted">{skill.id}</span>
              </div>
              <p className="text-xs text-kaihara-muted mt-1">{skill.description}</p>
              <div className="flex flex-wrap gap-1 mt-2">
                {skill.tags.slice(0, 4).map((tag, i) => (
                  <span key={i} className="text-xs bg-kaihara-bg px-1.5 py-0.5 rounded text-kaihara-muted">
                    {tag}
                  </span>
                ))}
              </div>
              <p className="text-xs text-kaihara-muted mt-1.5">Source: {skill.source}</p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
