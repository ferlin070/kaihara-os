import { useState, useCallback } from 'react'
import {
  generatePoster, generateBanner, generateInstagramPost,
  generateYoutubeThumb, generateQuoteImage,
  searchStockImage, searchStockVideo, videoTrim, videoConcat,
  videoFromImages, videoAddText, videoExport, mediaProbe,
} from '../lib/api'

type Tab = 'poster' | 'banner' | 'social' | 'stock' | 'video' | 'probe'

export default function EditorView() {
  const [tab, setTab] = useState<Tab>('poster')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string>('')
  const [error, setError] = useState<string>('')

  // Poster
  const [posterTitle, setPosterTitle] = useState('')
  const [posterSub, setPosterSub] = useState('')
  const [posterColor, setPosterColor] = useState('#1a1a2e')

  // Banner
  const [bannerTitle, setBannerTitle] = useState('')
  const [bannerColor, setBannerColor] = useState('#0f3460')

  // Social
  const [socialText, setSocialText] = useState('')
  const [socialType, setSocialType] = useState<'instagram' | 'youtube' | 'quote'>('instagram')
  const [quoteAuthor, setQuoteAuthor] = useState('')

  // Stock
  const [stockQuery, setStockQuery] = useState('')
  const [stockType, setStockType] = useState<'image' | 'video'>('image')
  const [stockResults, setStockResults] = useState<any[]>([])

  // Video
  const [videoPath, setVideoPath] = useState('')
  const [videoStart, setVideoStart] = useState(0)
  const [videoEnd, setVideoEnd] = useState(10)
  const [videoText, setVideoText] = useState('')

  // Probe
  const [probePath, setProbePath] = useState('')
  const [probeResult, setProbeResult] = useState<any>(null)

  const handleGenerate = useCallback(async (fn: () => Promise<any>) => {
    setLoading(true)
    setError('')
    setResult('')
    try {
      const r = await fn()
      if (r.ok) {
        setResult(r.output || 'Generated successfully')
      } else {
        setError(r.error || 'Failed')
      }
    } catch (e) {
      setError(String(e))
    }
    setLoading(false)
  }, [])

  const handleStockSearch = useCallback(async () => {
    if (!stockQuery) return
    setLoading(true)
    setError('')
    setStockResults([])
    try {
      const fn = stockType === 'image' ? searchStockImage : searchStockVideo
      const r = await fn(stockQuery, 12)
      if (r.ok) {
        setStockResults(stockType === 'image' ? r.photos : r.videos)
      } else {
        setError(r.error || 'Search failed')
      }
    } catch (e) {
      setError(String(e))
    }
    setLoading(false)
  }, [stockQuery, stockType])

  const handleProbe = useCallback(async () => {
    if (!probePath) return
    setLoading(true)
    setProbeResult(null)
    try {
      const r = await mediaProbe(probePath)
      setProbeResult(r)
    } catch (e) {
      setError(String(e))
    }
    setLoading(false)
  }, [probePath])

  const tabs: { id: Tab; label: string }[] = [
    { id: 'poster', label: 'Poster' },
    { id: 'banner', label: 'Banner' },
    { id: 'social', label: 'Social' },
    { id: 'stock', label: 'Stock' },
    { id: 'video', label: 'Video' },
    { id: 'probe', label: 'Probe' },
  ]

  return (
    <div className="flex flex-col gap-4 p-4 max-w-7xl mx-auto">
      <h2 className="text-sm font-bold text-kaihara-text flex items-center gap-2">
        <span className="text-kaihara-accent">🎬</span> Editor Agent
      </h2>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-kaihara-border">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 text-xs font-medium transition-colors ${
              tab === t.id ? 'text-kaihara-accent border-b-2 border-kaihara-accent' : 'text-kaihara-muted hover:text-kaihara-text'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Poster Tab */}
      {tab === 'poster' && (
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-3">GENERATE POSTER</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-kaihara-muted">Title</label>
              <input value={posterTitle} onChange={e => setPosterTitle(e.target.value)}
                className="kaihara-input w-full text-xs mt-1" placeholder="Enter poster title..." />
            </div>
            <div>
              <label className="text-[10px] text-kaihara-muted">Subtitle</label>
              <input value={posterSub} onChange={e => setPosterSub(e.target.value)}
                className="kaihara-input w-full text-xs mt-1" placeholder="Enter subtitle..." />
            </div>
            <div>
              <label className="text-[10px] text-kaihara-muted">Background Color</label>
              <div className="flex gap-2 mt-1">
                <input type="color" value={posterColor} onChange={e => setPosterColor(e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer" />
                <input value={posterColor} onChange={e => setPosterColor(e.target.value)}
                  className="kaihara-input flex-1 text-xs" />
              </div>
            </div>
          </div>
          <button onClick={() => handleGenerate(() => generatePoster({
            title: posterTitle || 'Hello World',
            subtitle: posterSub,
            bg_color: posterColor,
          }))}
            disabled={loading}
            className="kaihara-btn text-xs mt-3 px-4 py-2">
            {loading ? 'Generating...' : 'Generate Poster'}
          </button>
        </div>
      )}

      {/* Banner Tab */}
      {tab === 'banner' && (
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-3">GENERATE BANNER</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-kaihara-muted">Title</label>
              <input value={bannerTitle} onChange={e => setBannerTitle(e.target.value)}
                className="kaihara-input w-full text-xs mt-1" placeholder="Enter banner title..." />
            </div>
            <div>
              <label className="text-[10px] text-kaihara-muted">Background Color</label>
              <div className="flex gap-2 mt-1">
                <input type="color" value={bannerColor} onChange={e => setBannerColor(e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer" />
                <input value={bannerColor} onChange={e => setBannerColor(e.target.value)}
                  className="kaihara-input flex-1 text-xs" />
              </div>
            </div>
          </div>
          <button onClick={() => handleGenerate(() => generateBanner({
            title: bannerTitle || 'Banner',
            bg_color: bannerColor,
          }))}
            disabled={loading}
            className="kaihara-btn text-xs mt-3 px-4 py-2">
            {loading ? 'Generating...' : 'Generate Banner'}
          </button>
        </div>
      )}

      {/* Social Tab */}
      {tab === 'social' && (
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-3">SOCIAL MEDIA CONTENT</h4>
          <div className="flex gap-2 mb-3">
            {(['instagram', 'youtube', 'quote'] as const).map(type => (
              <button key={type} onClick={() => setSocialType(type)}
                className={`text-[10px] px-2 py-1 rounded ${socialType === type ? 'bg-kaihara-accent text-white' : 'bg-kaihara-border text-kaihara-muted'}`}>
                {type === 'instagram' ? 'Instagram Post' : type === 'youtube' ? 'YouTube Thumbnail' : 'Quote Image'}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-[10px] text-kaihara-muted">
                {socialType === 'quote' ? 'Quote' : 'Text'}
              </label>
              <textarea value={socialText} onChange={e => setSocialText(e.target.value)}
                className="kaihara-input w-full text-xs mt-1 h-16" placeholder="Enter text..." />
            </div>
            {socialType === 'quote' && (
              <div>
                <label className="text-[10px] text-kaihara-muted">Author</label>
                <input value={quoteAuthor} onChange={e => setQuoteAuthor(e.target.value)}
                  className="kaihara-input w-full text-xs mt-1" placeholder="Author name..." />
              </div>
            )}
          </div>
          <button onClick={() => handleGenerate(() => {
            if (socialType === 'instagram') return generateInstagramPost({ text: socialText || 'Hello!' })
            if (socialType === 'youtube') return generateYoutubeThumb({ title: socialText || 'Thumbnail' })
            return generateQuoteImage({ quote: socialText || 'Life is beautiful', author: quoteAuthor })
          })}
            disabled={loading}
            className="kaihara-btn text-xs mt-3 px-4 py-2">
            {loading ? 'Generating...' : `Generate ${socialType === 'instagram' ? 'Post' : socialType === 'youtube' ? 'Thumbnail' : 'Quote'}`}
          </button>
        </div>
      )}

      {/* Stock Tab */}
      {tab === 'stock' && (
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-3">STOCK MEDIA SEARCH (Pexels)</h4>
          <div className="flex gap-2 mb-3">
            <input value={stockQuery} onChange={e => setStockQuery(e.target.value)}
              className="kaihara-input flex-1 text-xs" placeholder="Search stock footage..."
              onKeyDown={e => e.key === 'Enter' && handleStockSearch()} />
            <select value={stockType} onChange={e => setStockType(e.target.value as any)}
              className="kaihara-input text-xs w-24">
              <option value="image">Images</option>
              <option value="video">Videos</option>
            </select>
            <button onClick={handleStockSearch} disabled={loading}
              className="kaihara-btn text-xs px-3">
              {loading ? '...' : 'Search'}
            </button>
          </div>
          {stockResults.length > 0 && (
            <div className="grid grid-cols-3 gap-2 max-h-64 overflow-auto">
              {stockResults.map((item: any, i: number) => (
                <div key={i} className="bg-kaihara-bg/50 border border-kaihara-border rounded p-1">
                  <img src={item.src?.medium || item.image || ''} alt=""
                    className="w-full h-24 object-cover rounded" />
                  <div className="text-[10px] text-kaihara-muted mt-1 truncate">
                    {item.photographer || `ID: ${item.id}`}
                  </div>
                </div>
              ))}
            </div>
          )}
          {stockResults.length === 0 && !loading && (
            <div className="text-[10px] text-kaihara-muted">Search for stock photos and videos from Pexels</div>
          )}
        </div>
      )}

      {/* Video Tab */}
      {tab === 'video' && (
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-3">VIDEO TOOLS</h4>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-kaihara-muted">Video Path</label>
                <input value={videoPath} onChange={e => setVideoPath(e.target.value)}
                  className="kaihara-input w-full text-xs mt-1" placeholder="/path/to/video.mp4" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-kaihara-muted">Start (s)</label>
                  <input type="number" value={videoStart} onChange={e => setVideoStart(Number(e.target.value))}
                    className="kaihara-input w-full text-xs mt-1" />
                </div>
                <div>
                  <label className="text-[10px] text-kaihara-muted">End (s)</label>
                  <input type="number" value={videoEnd} onChange={e => setVideoEnd(Number(e.target.value))}
                    className="kaihara-input w-full text-xs mt-1" />
                </div>
              </div>
            </div>
            <div>
              <label className="text-[10px] text-kaihara-muted">Text Overlay</label>
              <input value={videoText} onChange={e => setVideoText(e.target.value)}
                className="kaihara-input w-full text-xs mt-1" placeholder="Text to add..." />
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleGenerate(() => videoTrim(videoPath, videoStart, videoEnd, videoPath.replace('.mp4', '_trimmed.mp4')))}
                disabled={loading || !videoPath}
                className="kaihara-btn text-[10px] px-2 py-1">Trim</button>
              <button onClick={() => handleGenerate(() => videoAddText(videoPath, videoText || 'Sample Text', videoPath.replace('.mp4', '_text.mp4')))}
                disabled={loading || !videoPath}
                className="kaihara-btn text-[10px] px-2 py-1">Add Text</button>
              <button onClick={() => handleGenerate(() => videoExport(videoPath, videoPath.replace('.mp4', '_export.mp4')))}
                disabled={loading || !videoPath}
                className="kaihara-btn text-[10px] px-2 py-1">Export</button>
            </div>
          </div>
        </div>
      )}

      {/* Probe Tab */}
      {tab === 'probe' && (
        <div className="hud-panel">
          <h4 className="text-[10px] text-kaihara-muted mb-3">MEDIA PROBE</h4>
          <div className="flex gap-2 mb-3">
            <input value={probePath} onChange={e => setProbePath(e.target.value)}
              className="kaihara-input flex-1 text-xs" placeholder="/path/to/media.mp4"
              onKeyDown={e => e.key === 'Enter' && handleProbe()} />
            <button onClick={handleProbe} disabled={loading || !probePath}
              className="kaihara-btn text-xs px-3">
              {loading ? '...' : 'Probe'}
            </button>
          </div>
          {probeResult && (
            <pre className="text-[10px] text-kaihara-text bg-black/30 rounded p-2 max-h-48 overflow-auto font-mono">
              {JSON.stringify(probeResult, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Result / Error */}
      {result && (
        <div className="hud-panel border-kaihara-success/30">
          <div className="flex items-center gap-2">
            <span className="text-kaihara-success">✓</span>
            <span className="text-xs text-kaihara-text">{result}</span>
          </div>
        </div>
      )}
      {error && (
        <div className="hud-panel border-kaihara-danger/30">
          <div className="flex items-center gap-2">
            <span className="text-kaihara-danger">✗</span>
            <span className="text-xs text-kaihara-danger">{error}</span>
          </div>
        </div>
      )}
    </div>
  )
}
