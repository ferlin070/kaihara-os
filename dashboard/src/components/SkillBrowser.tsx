import { useState, useEffect, useCallback } from 'react'
import {
  getSkills, getSkillStats, createSkill,
  getPrompts, savePrompt, deletePrompt, usePrompt,
  extractRepoSkills,
  type Skill, type Prompt,
} from '../lib/api'

type Tab = 'skills' | 'prompts' | 'extract'

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

const promptCategories = ['general', 'coding', 'marketing', 'research', 'security', 'creative', 'workflow']

export default function SkillBrowser() {
  const [tab, setTab] = useState<Tab>('skills')

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Tab Navigation */}
      <div className="flex-shrink-0 flex border-b border-kaihara-border">
        {([
          { id: 'skills' as Tab, label: '📚 Skills' },
          { id: 'prompts' as Tab, label: '💬 Prompts' },
          { id: 'extract' as Tab, label: '🔗 Extract Repo' },
        ]).map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-5 py-2.5 text-sm font-medium uppercase tracking-wide transition-colors ${
              tab === t.id
                ? 'text-kaihara-accent border-b-2 border-kaihara-accent'
                : 'text-kaihara-muted hover:text-kaihara-text'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {tab === 'skills' && <SkillsTab />}
        {tab === 'prompts' && <PromptsTab />}
        {tab === 'extract' && <ExtractTab />}
      </div>
    </div>
  )
}

// ============================================================
// Skills Tab
// ============================================================

function SkillsTab() {
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

  useEffect(() => { fetchSkills() }, [fetchSkills])

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
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold uppercase tracking-wide">Skill Browser</h2>
          {stats && (
            <span className="text-xs text-kaihara-muted">{stats.total} skills installed</span>
          )}
        </div>

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search skills..."
          className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent mb-2"
        />

        <div className="flex flex-wrap gap-1">
          <button onClick={() => setFilter('')}
            className={`px-2 py-1 text-xs rounded ${!filter ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'}`}>
            All
          </button>
          {categories.map(cat => (
            <button key={cat} onClick={() => setFilter(cat)}
              className={`px-2 py-1 text-xs rounded ${filter === cat ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'}`}>
              {cat} ({stats?.categories[cat] || 0})
            </button>
          ))}
        </div>
      </div>

      {/* Create skill */}
      <div className="flex-shrink-0 px-4 py-2 border-b border-kaihara-border">
        <div className="flex gap-2">
          <input type="text" value={newSkillDesc}
            onChange={(e) => setNewSkillDesc(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="Describe a skill to create..."
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent"
            disabled={creating} />
          <button onClick={handleCreate}
            disabled={!newSkillDesc.trim() || creating}
            className="btn-primary disabled:opacity-50">
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
                {(Array.isArray(skill.tags) ? skill.tags : String(skill.tags || '').split(',').filter(Boolean)).slice(0, 4).map((tag: any, i: number) => (
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

// ============================================================
// Prompts Tab — Save & use prompts
// ============================================================

function PromptsTab() {
  const [prompts, setPrompts] = useState<Prompt[]>([])
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [newPrompt, setNewPrompt] = useState({ name: '', content: '', category: 'general', tags: '', description: '' })
  const [saving, setSaving] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const fetchPrompts = useCallback(async () => {
    try {
      const res = await getPrompts(filter || undefined, search || undefined)
      setPrompts(res.prompts || [])
    } catch {
      setPrompts([])
    }
  }, [filter, search])

  useEffect(() => { fetchPrompts() }, [fetchPrompts])

  const handleSave = async () => {
    if (!newPrompt.name.trim() || !newPrompt.content.trim() || saving) return
    setSaving(true)
    try {
      await savePrompt(
        newPrompt.name.trim(),
        newPrompt.content.trim(),
        newPrompt.category,
        newPrompt.tags.split(',').map(t => t.trim()).filter(Boolean),
        newPrompt.description.trim()
      )
      setNewPrompt({ name: '', content: '', category: 'general', tags: '', description: '' })
      setShowCreate(false)
      fetchPrompts()
    } catch {}
    setSaving(false)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this prompt?')) return
    await deletePrompt(id)
    fetchPrompts()
  }

  const handleCopy = (prompt: Prompt) => {
    navigator.clipboard.writeText(prompt.content)
    setCopiedId(prompt.id)
    usePrompt(prompt.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold uppercase tracking-wide">Prompt Storage</h2>
          <span className="text-xs text-kaihara-muted">{prompts.length} prompts saved</span>
        </div>

        <input type="text" value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search prompts..."
          className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent mb-2" />

        <div className="flex items-center gap-2">
          <div className="flex flex-wrap gap-1 flex-1">
            <button onClick={() => setFilter('')}
              className={`px-2 py-1 text-xs rounded ${!filter ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'}`}>
              All
            </button>
            {promptCategories.map(cat => (
              <button key={cat} onClick={() => setFilter(cat)}
                className={`px-2 py-1 text-xs rounded ${filter === cat ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'}`}>
                {cat}
              </button>
            ))}
          </div>
          <button onClick={() => setShowCreate(!showCreate)}
            className="px-3 py-1 text-xs bg-kaihara-accent text-white rounded hover:bg-kaihara-accent/80">
            + New
          </button>
        </div>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border bg-kaihara-border/20">
          <div className="space-y-2">
            <input type="text" value={newPrompt.name}
              onChange={(e) => setNewPrompt({ ...newPrompt, name: e.target.value })}
              placeholder="Prompt name"
              className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent" />
            <textarea value={newPrompt.content}
              onChange={(e) => setNewPrompt({ ...newPrompt, content: e.target.value })}
              placeholder="Paste your prompt here..."
              rows={4}
              className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent font-mono resize-none" />
            <input type="text" value={newPrompt.description}
              onChange={(e) => setNewPrompt({ ...newPrompt, description: e.target.value })}
              placeholder="Brief description"
              className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent" />
            <div className="flex gap-2">
              <select value={newPrompt.category}
                onChange={(e) => setNewPrompt({ ...newPrompt, category: e.target.value })}
                className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent">
                {promptCategories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <input type="text" value={newPrompt.tags}
                onChange={(e) => setNewPrompt({ ...newPrompt, tags: e.target.value })}
                placeholder="Tags (comma separated)"
                className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-kaihara-accent" />
            </div>
            <div className="flex gap-2">
              <button onClick={handleSave}
                disabled={!newPrompt.name.trim() || !newPrompt.content.trim() || saving}
                className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded hover:bg-kaihara-accent/80 disabled:opacity-50">
                {saving ? 'Saving...' : 'Save Prompt'}
              </button>
              <button onClick={() => setShowCreate(false)}
                className="px-4 py-1.5 text-xs bg-kaihara-border text-kaihara-muted rounded hover:text-kaihara-text">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Prompts List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {prompts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-kaihara-muted text-sm">No prompts saved yet.</p>
          </div>
        ) : (
          prompts.map(prompt => (
            <div key={prompt.id} className="hud-panel hover:border-kaihara-accent transition-colors">
              <div className="flex items-start justify-between mb-1">
                <div>
                  <h3 className="text-sm font-medium">{prompt.name}</h3>
                  <span className={`text-xs ${categoryColors[prompt.category] || 'text-kaihara-muted'}`}>
                    {prompt.category}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-kaihara-muted">{prompt.uses} uses</span>
                  <button onClick={() => handleCopy(prompt)}
                    className="text-xs px-2 py-0.5 bg-kaihara-accent/20 text-kaihara-accent rounded hover:bg-kaihara-accent/30">
                    {copiedId === prompt.id ? '✓ Copied' : 'Copy'}
                  </button>
                  <button onClick={() => handleDelete(prompt.id)}
                    className="text-xs px-2 py-0.5 bg-kaihara-danger/20 text-kaihara-danger rounded hover:bg-kaihara-danger/30">
                    Delete
                  </button>
                </div>
              </div>
              {prompt.description && (
                <p className="text-xs text-kaihara-muted mt-1">{prompt.description}</p>
              )}
              <pre className="text-xs text-kaihara-text bg-kaihara-bg p-2 rounded mt-2 overflow-x-auto max-h-20 font-mono">
                {prompt.content.slice(0, 200)}{prompt.content.length > 200 ? '...' : ''}
              </pre>
              <div className="flex flex-wrap gap-1 mt-2">
                {(Array.isArray(prompt.tags) ? prompt.tags : []).map((tag: any, i: number) => (
                  <span key={i} className="text-xs bg-kaihara-bg px-1.5 py-0.5 rounded text-kaihara-muted">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ============================================================
// Extract Tab — Extract skills from GitHub repos
// ============================================================

function ExtractTab() {
  const [repoUrl, setRepoUrl] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleExtract = async () => {
    if (!repoUrl.trim() || extracting) return
    setExtracting(true)
    setResult(null)
    try {
      const res = await extractRepoSkills(repoUrl.trim())
      setResult(res)
    } catch (e) {
      setResult({ error: String(e) })
    }
    setExtracting(false)
  }

  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      {/* Header */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-wide mb-2">Extract Skills from GitHub</h2>
        <p className="text-xs text-kaihara-muted">
          Enter a GitHub repository URL to extract SKILL.md files and add them to your skill library.
        </p>
      </div>

      {/* Input */}
      <div className="hud-panel">
        <label className="text-xs text-kaihara-muted mb-2 block">REPOSITORY URL</label>
        <div className="flex gap-2">
          <input type="text" value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleExtract()}
            placeholder="https://github.com/owner/repo or owner/repo"
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-2 text-sm focus:outline-none focus:border-kaihara-accent font-mono"
            disabled={extracting} />
          <button onClick={handleExtract}
            disabled={!repoUrl.trim() || extracting}
            className="px-4 py-2 bg-kaihara-accent text-white text-sm rounded hover:bg-kaihara-accent/80 disabled:opacity-50 font-medium">
            {extracting ? 'Extracting...' : 'Extract'}
          </button>
        </div>
      </div>

      {/* How it works */}
      <div className="hud-panel">
        <h3 className="text-xs font-bold text-kaihara-muted mb-2">HOW IT WORKS</h3>
        <div className="space-y-1 text-xs text-kaihara-muted">
          <p>1. Fetches the repository file tree via GitHub API</p>
          <p>2. Finds all SKILL.md files (and similar patterns)</p>
          <p>3. Downloads content and parses metadata (frontmatter)</p>
          <p>4. Installs each skill into your local skill library</p>
        </div>
      </div>

      {/* Examples */}
      <div className="hud-panel">
        <h3 className="text-xs font-bold text-kaihara-muted mb-2">EXAMPLE REPOS</h3>
        <div className="space-y-1">
          {[
            { url: 'anthropics/anthropic-cookbook', desc: 'Anthropic prompt engineering patterns' },
            { url: 'langchain-ai/langchain', desc: 'LangChain agent patterns' },
            { url: 'hwchase17/langchain', desc: 'LangChain templates' },
          ].map(ex => (
            <button key={ex.url} onClick={() => setRepoUrl(ex.url)}
              className="w-full text-left px-2 py-1.5 rounded hover:bg-kaihara-border/50 transition-colors">
              <span className="text-xs font-mono text-kaihara-accent">{ex.url}</span>
              <span className="text-xs text-kaihara-muted ml-2">— {ex.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="hud-panel">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-bold text-kaihara-muted">RESULT</h3>
            {result.error ? (
              <span className="text-xs px-2 py-0.5 bg-kaihara-danger/20 text-kaihara-danger rounded">Error</span>
            ) : (
              <span className="text-xs px-2 py-0.5 bg-kaihara-success/20 text-kaihara-success rounded">Success</span>
            )}
          </div>
          {result.error ? (
            <p className="text-xs text-kaihara-danger">{result.error}</p>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-4 text-xs">
                <span className="text-kaihara-muted">Repo: <span className="text-kaihara-text">{result.repo}</span></span>
                <span className="text-kaihara-muted">Found: <span className="text-kaihara-text">{result.found}</span></span>
                <span className="text-kaihara-success">Installed: <span className="text-kaihara-text">{result.installed}</span></span>
              </div>
              {result.skills?.length > 0 && (
                <div className="space-y-1">
                  {result.skills.map((s: any) => (
                    <div key={s.id} className="flex items-center gap-2 text-xs">
                      <span className="text-kaihara-success">✓</span>
                      <span className="font-mono text-kaihara-accent">{s.id}</span>
                      <span className="text-kaihara-muted">— {s.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
