import { useState, useEffect, useCallback } from 'react'
import {
  getLandingSites, deployLanding, deleteLandingSite,
  type LandingSite,
} from '../lib/api'

export default function LandingPages() {
  const [sites, setSites] = useState<LandingSite[]>([])
  const [name, setName] = useState('')
  const [html, setHtml] = useState('')
  const [deploying, setDeploying] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    try {
      const d = await getLandingSites()
      if (d.ok) setSites(d.sites || [])
    } catch {}
  }, [])

  useEffect(() => { fetch() }, [fetch])

  const handleDeploy = async () => {
    if (!name.trim() || !html.trim() || deploying) return
    setDeploying(true)
    setMsg(null)
    try {
      const r = await deployLanding(name.trim(), html)
      if (r.ok) {
        setMsg(`✅ Live: https://${r.domain}`)
        setName('')
        setHtml('')
        fetch()
      } else {
        setMsg(`❌ ${r.error}`)
      }
    } catch (e) {
      setMsg(`❌ ${String(e)}`)
    }
    setDeploying(false)
  }

  const handleDelete = async (domain: string) => {
    if (!confirm(`Delete ${domain}?`)) return
    await deleteLandingSite(domain.replace('.nakhodacloud.top', ''))
    fetch()
  }

  const loadTemplate = () => {
    setHtml(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Landing Page</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; background: linear-gradient(135deg, #0a0e1a, #1a2332);
           color: #e5e7eb; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .card { text-align: center; padding: 60px 40px; max-width: 600px; }
    h1 { font-size: 3rem; margin-bottom: 16px;
         background: linear-gradient(90deg, #06b6d4, #3b82f6);
         -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    p { color: #9ca3af; font-size: 1.1rem; line-height: 1.6; }
    .cta { display: inline-block; margin-top: 32px; padding: 14px 40px;
           background: linear-gradient(90deg, #06b6d4, #3b82f6); color: white;
           border-radius: 50px; text-decoration: none; font-weight: bold; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Your Brand</h1>
    <p>Tagline anda di sini. Terangkan nilai produk atau servis dengan ringkas dan jelas.</p>
    <a href="#" class="cta">Get Started</a>
  </div>
</body>
</html>`)
  }

  return (
    <div className="hud-panel space-y-3">
      <h4 className="text-[10px] text-kaihara-muted mb-1">
        LANDING PAGES — *.nakhodacloud.top (web-hosting CT 100)
      </h4>

      {/* Deploy form */}
      <div className="space-y-2">
        <input
          type="text" value={name} onChange={e => setName(e.target.value)}
          placeholder="site-name (akan jadi site-name.nakhodacloud.top)"
          className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-2 text-sm focus:outline-none focus:border-kaihara-accent font-mono"
          disabled={deploying}
        />
        <textarea
          value={html} onChange={e => setHtml(e.target.value)}
          placeholder="<html>... HTML content ..."
          rows={6}
          className="w-full bg-kaihara-bg border border-kaihara-border rounded px-3 py-2 text-xs font-mono focus:outline-none focus:border-kaihara-accent"
          disabled={deploying}
        />
        <div className="flex gap-2">
          <button
            onClick={handleDeploy}
            disabled={!name.trim() || !html.trim() || deploying}
            className="flex-1 px-4 py-2 bg-kaihara-accent text-white text-sm rounded hover:bg-kaihara-accent/80 disabled:opacity-50 font-medium"
          >
            {deploying ? '🚀 Deploying...' : '🚀 Deploy Landing Page'}
          </button>
          <button onClick={loadTemplate} disabled={deploying}
            className="px-3 py-2 text-xs bg-kaihara-border rounded hover:opacity-80">
            📋 Template
          </button>
        </div>
        {msg && <p className="text-xs">{msg}</p>}
      </div>

      {/* Sites list */}
      <div className="border-t border-kaihara-border pt-2">
        <p className="text-[10px] text-kaihara-muted mb-1.5">
          HOSTED SITES ({sites.length})
        </p>
        <div className="max-h-64 overflow-y-auto space-y-0.5">
          {sites.map(s => (
            <div key={s.domain} className="flex items-center justify-between group px-2 py-1 rounded hover:bg-kaihara-border/30">
              <a href={`https://${s.domain}`} target="_blank" rel="noopener noreferrer"
                 className="text-xs text-kaihara-accent hover:underline truncate flex-1 min-w-0">
                {s.domain}
              </a>
              <span className="text-[10px] text-kaihara-muted mx-2">{s.size}</span>
              <button
                onClick={() => handleDelete(s.domain)}
                className="opacity-0 group-hover:opacity-100 text-[10px] text-kaihara-danger hover:text-kaihara-danger/70 transition-opacity"
                title="Delete"
              >
                🗑
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
