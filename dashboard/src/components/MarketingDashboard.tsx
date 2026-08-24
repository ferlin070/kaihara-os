import { useState, useEffect, useCallback } from 'react'
import {
  getMarketingDashboard, getLeads, createLead, deleteLead, convertLead,
  getClients, createClient, deleteClient, approveClient,
  getCampaigns, createCampaign, deleteCampaign,
  getContent, createContent, publishContent, generateContent,
  getSeoTracking, addSeoTracking, seoAudit, keywordResearch, competitorAnalysis,
  getInvoices, createInvoice, payInvoice, deleteInvoice,
  marketingChat,
  type Lead, type Client, type Campaign, type Content, type Invoice,
} from '../lib/api'

type MktTab = 'overview' | 'leads' | 'clients' | 'campaigns' | 'content' | 'seo' | 'invoices' | 'chat'

const statusColors: Record<string, string> = {
  new: 'bg-kaihara-accent/20 text-kaihara-accent',
  contacted: 'bg-kaihara-warning/20 text-kaihara-warning',
  qualified: 'bg-kaihara-success/20 text-kaihara-success',
  converted: 'bg-kaihara-success text-white',
  active: 'bg-kaihara-success/20 text-kaihara-success',
  inactive: 'bg-kaihara-muted/20 text-kaihara-muted',
  draft: 'bg-kaihara-muted/20 text-kaihara-muted',
  active_campaign: 'bg-kaihara-accent/20 text-kaihara-accent',
  completed: 'bg-kaihara-success/20 text-kaihara-success',
  paused: 'bg-kaihara-warning/20 text-kaihara-warning',
  published: 'bg-kaihara-success/20 text-kaihara-success',
  scheduled: 'bg-kaihara-accent/20 text-kaihara-accent',
  paid: 'bg-kaihara-success/20 text-kaihara-success',
  sent: 'bg-kaihara-accent/20 text-kaihara-accent',
  overdue: 'bg-kaihara-danger/20 text-kaihara-danger',
}

export default function MarketingDashboard() {
  const [tab, setTab] = useState<MktTab>('overview')

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-shrink-0 flex border-b border-kaihara-border overflow-x-auto">
        {([
          { id: 'overview' as MktTab, label: '📊 Overview' },
          { id: 'leads' as MktTab, label: '🎯 Leads' },
          { id: 'clients' as MktTab, label: '👥 Clients' },
          { id: 'campaigns' as MktTab, label: '📢 Campaigns' },
          { id: 'content' as MktTab, label: '✍️ Content' },
          { id: 'seo' as MktTab, label: '🔍 SEO' },
          { id: 'invoices' as MktTab, label: '💰 Invoices' },
          { id: 'chat' as MktTab, label: '🤖 AI Agent' },
        ]).map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-xs font-medium uppercase tracking-wide whitespace-nowrap transition-colors ${
              tab === t.id ? 'text-kaihara-accent border-b-2 border-kaihara-accent' : 'text-kaihara-muted hover:text-kaihara-text'
            }`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'leads' && <LeadsTab />}
        {tab === 'clients' && <ClientsTab />}
        {tab === 'campaigns' && <CampaignsTab />}
        {tab === 'content' && <ContentTab />}
        {tab === 'seo' && <SeoTab />}
        {tab === 'invoices' && <InvoicesTab />}
        {tab === 'chat' && <AgentChatTab />}
      </div>
    </div>
  )
}

// ============================================================
// Overview
// ============================================================

function OverviewTab() {
  const [data, setData] = useState<any>(null)
  useEffect(() => { getMarketingDashboard().then(setData).catch(() => {}) }, [])
  if (!data) return <div className="p-4 text-kaihara-muted text-sm animate-pulse">Loading dashboard...</div>

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-sm font-bold uppercase tracking-wide">Marketing Dashboard</h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          { label: 'Leads', value: data.leads?.total || 0, icon: '🎯', color: 'text-kaihara-accent' },
          { label: 'Clients', value: data.clients?.total || 0, icon: '👥', color: 'text-kaihara-success' },
          { label: 'Campaigns', value: data.campaigns?.total || 0, icon: '📢', color: 'text-kaihara-warning' },
          { label: 'Revenue', value: `RM ${data.invoices?.total_revenue || 0}`, icon: '💰', color: 'text-kaihara-success' },
          { label: 'SEO Score', value: `${data.seo?.avg_page_score || 0}`, icon: '🔍', color: 'text-kaihara-accent' },
        ].map((kpi, i) => (
          <div key={i} className="hud-panel text-center">
            <div className="text-lg mb-1">{kpi.icon}</div>
            <div className={`text-xl font-bold font-mono ${kpi.color}`}>{kpi.value}</div>
            <div className="text-xs text-kaihara-muted">{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* Revenue + Leads by Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="hud-panel">
          <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-2">Revenue</h3>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between"><span className="text-kaihara-muted">Collected</span><span className="text-kaihara-success font-mono">RM {data.invoices?.total_revenue || 0}</span></div>
            <div className="flex justify-between"><span className="text-kaihara-muted">Outstanding</span><span className="text-kaihara-warning font-mono">RM {data.invoices?.total_outstanding || 0}</span></div>
            <div className="flex justify-between"><span className="text-kaihara-muted">Overdue</span><span className="text-kaihara-danger font-mono">{data.invoices?.overdue_count || 0}</span></div>
          </div>
        </div>
        <div className="hud-panel">
          <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-2">Lead Pipeline</h3>
          <div className="space-y-1 text-xs">
            {Object.entries(data.leads?.by_status || {}).map(([status, count]) => (
              <div key={status} className="flex justify-between">
                <span className="text-kaihara-muted capitalize">{status}</span>
                <span className="font-mono">{count as number}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="hud-panel">
        <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-2">Recent Activity</h3>
        <div className="space-y-1">
          {(data.activity || []).slice(0, 5).map((a: any, i: number) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="text-kaihara-accent">▸</span>
              <span className="text-kaihara-text">{a.action}</span>
              <span className="text-kaihara-muted">{a.entity_type} #{a.entity_id}</span>
            </div>
          ))}
          {(!data.activity || data.activity.length === 0) && <p className="text-xs text-kaihara-muted">No recent activity.</p>}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Leads
// ============================================================

function LeadsTab() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', phone: '', company: '', source: 'manual', notes: '' })

  const fetch = useCallback(async () => {
    const res = await getLeads(filter || undefined, search || undefined)
    setLeads(res.leads || [])
  }, [filter, search])

  useEffect(() => { fetch() }, [fetch])

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await createLead(form)
    setForm({ name: '', email: '', phone: '', company: '', source: 'manual', notes: '' })
    setShowForm(false)
    fetch()
  }

  const handleConvert = async (id: number) => {
    if (!confirm('Convert lead to client?')) return
    await convertLead(id)
    fetch()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold uppercase tracking-wide">Leads ({(leads || []).length})</h2>
          <button onClick={() => setShowForm(!showForm)} className="px-3 py-1 text-xs bg-kaihara-accent text-white rounded">+ New</button>
        </div>
        <div className="flex gap-2">
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..."
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
          {['new', 'contacted', 'qualified', 'converted'].map(s => (
            <button key={s} onClick={() => setFilter(filter === s ? '' : s)}
              className={`px-2 py-1 text-xs rounded ${filter === s ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {showForm && (
        <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border bg-kaihara-border/20">
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input placeholder="Name *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input placeholder="Phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input placeholder="Company" value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
          </div>
          <input placeholder="Notes" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent mb-2" />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded">Save</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-1.5 text-xs bg-kaihara-border text-kaihara-muted rounded">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {(leads || []).map(lead => (
          <div key={lead.id} className="hud-panel hover:border-kaihara-accent/50 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <div>
                <span className="text-sm font-medium">{lead.name}</span>
                {lead.company && <span className="text-xs text-kaihara-muted ml-2">@ {lead.company}</span>}
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded ${statusColors[lead.status] || 'bg-kaihara-border text-kaihara-muted'}`}>{lead.status}</span>
                <span className="text-xs font-mono text-kaihara-accent">{lead.score}</span>
              </div>
            </div>
            <div className="flex gap-4 text-xs text-kaihara-muted">
              {lead.email && <span>{lead.email}</span>}
              {lead.phone && <span>{lead.phone}</span>}
              <span>Source: {lead.source}</span>
            </div>
            <div className="flex gap-2 mt-2">
              {lead.status !== 'converted' && (
                <button onClick={() => handleConvert(lead.id)} className="text-xs px-2 py-0.5 bg-kaihara-success/20 text-kaihara-success rounded">Convert → Client</button>
              )}
              <button onClick={() => deleteLead(lead.id).then(fetch)} className="text-xs px-2 py-0.5 bg-kaihara-danger/20 text-kaihara-danger rounded">Delete</button>
            </div>
          </div>
        ))}
        {(leads || []).length === 0 && <p className="text-center text-kaihara-muted text-sm py-8">No leads found.</p>}
      </div>
    </div>
  )
}

// ============================================================
// Clients
// ============================================================

function ClientsTab() {
  const [clients, setClients] = useState<Client[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', phone: '', company: '', tier: 'basic', notes: '' })

  const fetch = useCallback(async () => {
    const res = await getClients(filter || undefined, undefined, search || undefined)
    setClients(res.clients || [])
  }, [filter, search])

  useEffect(() => { fetch() }, [fetch])

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await createClient(form)
    setForm({ name: '', email: '', phone: '', company: '', tier: 'basic', notes: '' })
    setShowForm(false)
    fetch()
  }

  const handleApprove = async (clientId: number) => {
    const msg = prompt('Approval message for client (email/WhatsApp):')
    if (!msg) return
    await approveClient(clientId, { type: 'service', message: msg, channels: ['email', 'whatsapp'] })
    alert('Approval request sent!')
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold uppercase tracking-wide">Clients ({(clients || []).length})</h2>
          <button onClick={() => setShowForm(!showForm)} className="px-3 py-1 text-xs bg-kaihara-accent text-white rounded">+ New</button>
        </div>
        <div className="flex gap-2">
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..."
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
          {['active', 'inactive'].map(s => (
            <button key={s} onClick={() => setFilter(filter === s ? '' : s)}
              className={`px-2 py-1 text-xs rounded ${filter === s ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {showForm && (
        <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border bg-kaihara-border/20">
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input placeholder="Name *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input placeholder="Email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input placeholder="Phone" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input placeholder="Company" value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded">Save</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-1.5 text-xs bg-kaihara-border text-kaihara-muted rounded">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {(clients || []).map(client => (
          <div key={client.id} className="hud-panel hover:border-kaihara-accent/50 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <div>
                <span className="text-sm font-medium">{client.name}</span>
                <span className="text-xs text-kaihara-muted ml-2">{client.tier}</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded ${statusColors[client.status] || ''}`}>{client.status}</span>
            </div>
            <div className="flex gap-4 text-xs text-kaihara-muted">
              {client.email && <span>{client.email}</span>}
              {client.phone && <span>{client.phone}</span>}
              {client.company && <span>@ {client.company}</span>}
            </div>
            <div className="flex justify-between items-center mt-2">
              <div className="flex gap-4 text-xs">
                <span className="text-kaihara-success">Paid: RM {client.total_paid}</span>
                <span className="text-kaihara-warning">Invoiced: RM {client.total_invoiced}</span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => handleApprove(client.id)} className="text-xs px-2 py-0.5 bg-kaihara-accent/20 text-kaihara-accent rounded">Send Approval</button>
                <button onClick={() => deleteClient(client.id).then(fetch)} className="text-xs px-2 py-0.5 bg-kaihara-danger/20 text-kaihara-danger rounded">Delete</button>
              </div>
            </div>
          </div>
        ))}
        {(clients || []).length === 0 && <p className="text-center text-kaihara-muted text-sm py-8">No clients found.</p>}
      </div>
    </div>
  )
}

// ============================================================
// Campaigns
// ============================================================

function CampaignsTab() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', type: 'general', budget: 0, target_audience: '' })

  const fetch = useCallback(async () => {
    const res = await getCampaigns()
    setCampaigns(res.campaigns || [])
  }, [])

  useEffect(() => { fetch() }, [fetch])

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await createCampaign(form)
    setForm({ name: '', description: '', type: 'general', budget: 0, target_audience: '' })
    setShowForm(false)
    fetch()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wide">Campaigns ({(campaigns || []).length})</h2>
          <button onClick={() => setShowForm(!showForm)} className="px-3 py-1 text-xs bg-kaihara-accent text-white rounded">+ New</button>
        </div>
      </div>

      {showForm && (
        <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border bg-kaihara-border/20">
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input placeholder="Campaign Name *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input placeholder="Target Audience" value={form.target_audience} onChange={e => setForm({ ...form, target_audience: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
          </div>
          <input placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent mb-2" />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded">Create</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-1.5 text-xs bg-kaihara-border text-kaihara-muted rounded">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {(campaigns || []).map(c => (
          <div key={c.id} className="hud-panel">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">{c.name}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${statusColors[c.status] || ''}`}>{c.status}</span>
            </div>
            <p className="text-xs text-kaihara-muted">{c.description}</p>
            <div className="flex gap-4 text-xs mt-2">
              <span className="text-kaihara-muted">Budget: <span className="text-kaihara-text">RM {c.budget}</span></span>
              <span className="text-kaihara-muted">Spent: <span className="text-kaihara-warning">RM {c.spent}</span></span>
              <span className="text-kaihara-muted">Audience: <span className="text-kaihara-text">{c.target_audience || 'All'}</span></span>
            </div>
            <button onClick={() => deleteCampaign(c.id).then(fetch)} className="text-xs px-2 py-0.5 bg-kaihara-danger/20 text-kaihara-danger rounded mt-2">Delete</button>
          </div>
        ))}
        {(campaigns || []).length === 0 && <p className="text-center text-kaihara-muted text-sm py-8">No campaigns yet.</p>}
      </div>
    </div>
  )
}

// ============================================================
// Content
// ============================================================

function ContentTab() {
  const [content, setContent] = useState<Content[]>([])
  const [showForm, setShowForm] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [form, setForm] = useState({ title: '', body: '', content_type: 'post', platform: 'instagram', hashtags: '' })

  const fetch = useCallback(async () => {
    const res = await getContent()
    setContent(res.content || [])
  }, [])

  useEffect(() => { fetch() }, [fetch])

  const handleCreate = async () => {
    if (!form.title.trim()) return
    await createContent({ ...form, hashtags: form.hashtags.split(',').map(h => h.trim()).filter(Boolean) })
    setForm({ title: '', body: '', content_type: 'post', platform: 'instagram', hashtags: '' })
    setShowForm(false)
    fetch()
  }

  const handleGenerate = async () => {
    const topic = prompt('What topic should I create content about?')
    if (!topic) return
    setGenerating(true)
    try {
      const res = await generateContent({ topic, platform: form.platform, content_type: form.content_type })
      if (res.generated) {
        // Try to parse JSON from response
        try {
          const parsed = JSON.parse(res.generated.match(/\{[\s\S]*\}/)?.[0] || '{}')
          setForm(f => ({ ...f, title: parsed.title || topic, body: parsed.body || res.generated, hashtags: (parsed.hashtags || []).join(', ') }))
        } catch {
          setForm(f => ({ ...f, title: topic, body: res.generated }))
        }
      }
    } catch {}
    setGenerating(false)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wide">Content ({(content || []).length})</h2>
          <div className="flex gap-2">
            <button onClick={handleGenerate} disabled={generating}
              className="px-3 py-1 text-xs bg-kaihara-warning/20 text-kaihara-warning rounded disabled:opacity-50">
              {generating ? 'Generating...' : '🤖 AI Generate'}
            </button>
            <button onClick={() => setShowForm(!showForm)} className="px-3 py-1 text-xs bg-kaihara-accent text-white rounded">+ New</button>
          </div>
        </div>
      </div>

      {showForm && (
        <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border bg-kaihara-border/20">
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input placeholder="Title *" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <select value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent">
              <option value="instagram">Instagram</option>
              <option value="facebook">Facebook</option>
              <option value="twitter">Twitter/X</option>
              <option value="tiktok">TikTok</option>
              <option value="linkedin">LinkedIn</option>
            </select>
          </div>
          <textarea placeholder="Content body..." value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} rows={3} className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent font-mono resize-none mb-2" />
          <input placeholder="Hashtags (comma separated)" value={form.hashtags} onChange={e => setForm({ ...form, hashtags: e.target.value })} className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent mb-2" />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded">Save</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-1.5 text-xs bg-kaihara-border text-kaihara-muted rounded">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {(content || []).map(c => (
          <div key={c.id} className="hud-panel">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">{c.title}</span>
              <div className="flex gap-2">
                <span className="text-xs bg-kaihara-border px-2 py-0.5 rounded">{c.platform}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${statusColors[c.status] || ''}`}>{c.status}</span>
              </div>
            </div>
            <p className="text-xs text-kaihara-muted line-clamp-2">{c.body}</p>
            <div className="flex gap-2 mt-2">
              {c.status === 'draft' && (
                <button onClick={() => publishContent(c.id).then(fetch)} className="text-xs px-2 py-0.5 bg-kaihara-success/20 text-kaihara-success rounded">Publish</button>
              )}
            </div>
          </div>
        ))}
        {(content || []).length === 0 && <p className="text-center text-kaihara-muted text-sm py-8">No content yet. Click AI Generate to create!</p>}
      </div>
    </div>
  )
}

// ============================================================
// SEO
// ============================================================

function SeoTab() {
  const [tracking, setTracking] = useState<any[]>([])
  const [auditResult, setAuditResult] = useState<any>(null)
  const [auditUrl, setAuditUrl] = useState('')
  const [auditing, setAuditing] = useState(false)

  useEffect(() => { getSeoTracking().then(r => setTracking(r.tracking || [])).catch(() => {}) }, [])

  const handleAudit = async () => {
    if (!auditUrl.trim() || auditing) return
    setAuditing(true)
    try {
      const res = await seoAudit(auditUrl)
      setAuditResult(res)
    } catch {}
    setAuditing(false)
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-sm font-bold uppercase tracking-wide">SEO Tools</h2>

      {/* SEO Audit */}
      <div className="hud-panel">
        <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-2">SEO Audit</h3>
        <div className="flex gap-2 mb-3">
          <input type="text" value={auditUrl} onChange={e => setAuditUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent font-mono"
            onKeyDown={e => e.key === 'Enter' && handleAudit()} />
          <button onClick={handleAudit} disabled={auditing}
            className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded disabled:opacity-50">
            {auditing ? 'Auditing...' : 'Audit'}
          </button>
        </div>

        {auditResult && !auditResult.error && (
          <div className="space-y-2">
            <div className="flex items-center gap-3 mb-2">
              <div className="text-2xl font-bold font-mono text-kaihara-accent">{auditResult.score}/100</div>
              <div className="text-xs text-kaihara-muted">{auditResult.title}</div>
            </div>
            {auditResult.issues?.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-kaihara-danger mb-1">Issues ({(auditResult.issues || []).length})</h4>
                {(auditResult.issues || []).map((issue: string, i: number) => (
                  <div key={i} className="text-xs text-kaihara-danger/80 ml-2">• {issue}</div>
                ))}
              </div>
            )}
            {auditResult.checks?.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-kaihara-success mb-1">Passed ({(auditResult.checks || []).length})</h4>
                {(auditResult.checks || []).map((check: string, i: number) => (
                  <div key={i} className="text-xs text-kaihara-success/80 ml-2">✓ {check}</div>
                ))}
              </div>
            )}
          </div>
        )}
        {auditResult?.error && <p className="text-xs text-kaihara-danger">{auditResult.error}</p>}
      </div>

      {/* Tracked Keywords */}
      <div className="hud-panel">
        <h3 className="text-xs font-bold text-kaihara-muted uppercase mb-2">Tracked Keywords ({(tracking || []).length})</h3>
        <div className="space-y-1">
          {(tracking || []).map((t: any) => (
            <div key={t.id} className="flex items-center justify-between text-xs">
              <span className="text-kaihara-text">{t.keyword || t.url}</span>
              <div className="flex gap-3">
                <span className="text-kaihara-muted">Position: <span className="text-kaihara-accent font-mono">#{t.position}</span></span>
                <span className="text-kaihara-muted">Score: <span className="text-kaihara-success font-mono">{t.page_score}</span></span>
              </div>
            </div>
          ))}
          {(tracking || []).length === 0 && <p className="text-xs text-kaihara-muted">No keywords tracked yet.</p>}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Invoices
// ============================================================

function InvoicesTab() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ client_id: 0, amount: 0, description: '', tax_rate: 0 })

  const fetch = useCallback(async () => {
    const res = await getInvoices()
    setInvoices(res.invoices || [])
  }, [])

  useEffect(() => { fetch() }, [fetch])

  const handleCreate = async () => {
    if (!form.client_id || !form.amount) return
    await createInvoice(form)
    setForm({ client_id: 0, amount: 0, description: '', tax_rate: 0 })
    setShowForm(false)
    fetch()
  }

  const handlePay = async (id: number) => {
    const method = prompt('Payment method (bank/ewallet/cash):')
    if (!method) return
    await payInvoice(id, { method })
    fetch()
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wide">Invoices ({(invoices || []).length})</h2>
          <button onClick={() => setShowForm(!showForm)} className="px-3 py-1 text-xs bg-kaihara-accent text-white rounded">+ New</button>
        </div>
      </div>

      {showForm && (
        <div className="flex-shrink-0 px-4 py-3 border-b border-kaihara-border bg-kaihara-border/20">
          <div className="grid grid-cols-2 gap-2 mb-2">
            <input type="number" placeholder="Client ID" value={form.client_id || ''} onChange={e => setForm({ ...form, client_id: Number(e.target.value) })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
            <input type="number" placeholder="Amount (MYR)" value={form.amount || ''} onChange={e => setForm({ ...form, amount: Number(e.target.value) })} className="bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent" />
          </div>
          <input placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent mb-2" />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded">Create</button>
            <button onClick={() => setShowForm(false)} className="px-4 py-1.5 text-xs bg-kaihara-border text-kaihara-muted rounded">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {(invoices || []).map(inv => (
          <div key={inv.id} className="hud-panel">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-mono text-kaihara-accent">{inv.invoice_number}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${statusColors[inv.status] || ''}`}>{inv.status}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-kaihara-muted">{inv.description}</span>
              <span className="font-mono text-kaihara-success">RM {inv.total}</span>
            </div>
            <div className="flex justify-between text-xs mt-1">
              <span className="text-kaihara-muted">Due: {inv.due_date}</span>
              {inv.status !== 'paid' && (
                <button onClick={() => handlePay(inv.id)} className="text-xs px-2 py-0.5 bg-kaihara-success/20 text-kaihara-success rounded">Mark Paid</button>
              )}
            </div>
          </div>
        ))}
        {(invoices || []).length === 0 && <p className="text-center text-kaihara-muted text-sm py-8">No invoices yet.</p>}
      </div>
    </div>
  )
}

// ============================================================
// AI Agent Chat
// ============================================================

function AgentChatTab() {
  const [messages, setMessages] = useState<{ role: string; text: string }[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    if (!input.trim() || loading) return
    const msg = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', text: msg }])
    setLoading(true)
    try {
      const res = await marketingChat(msg)
      setMessages(m => [...m, { role: 'agent', text: res.response || 'No response.' }])
    } catch {
      setMessages(m => [...m, { role: 'agent', text: 'Error connecting to marketing agent.' }])
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-shrink-0 px-4 py-2 border-b border-kaihara-border">
        <h2 className="text-sm font-bold uppercase tracking-wide">Marketing AI Agent</h2>
        <p className="text-xs text-kaihara-muted">Ask about competitors, SEO, content ideas, campaigns...</p>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {messages.map((m, i) => (
          <div key={i} className={`text-xs p-2 rounded max-w-[85%] ${m.role === 'user' ? 'bg-kaihara-accent/20 text-kaihara-text ml-auto' : 'bg-kaihara-border text-kaihara-text'}`}>
            {m.text}
          </div>
        ))}
        {loading && <div className="text-xs text-kaihara-muted animate-pulse">Agent is thinking...</div>}
      </div>
      <div className="flex-shrink-0 p-3 border-t border-kaihara-border">
        <div className="flex gap-2">
          <input type="text" value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Ask marketing agent..."
            className="flex-1 bg-kaihara-bg border border-kaihara-border rounded px-3 py-1.5 text-xs focus:outline-none focus:border-kaihara-accent"
            disabled={loading} />
          <button onClick={send} disabled={loading}
            className="px-4 py-1.5 text-xs bg-kaihara-accent text-white rounded disabled:opacity-50">Send</button>
        </div>
      </div>
    </div>
  )
}
