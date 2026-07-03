// Carte du Royaume — MMO-style hex map over the player's REAL territory.
// Fog of war: only hexes crossed during activities exist; the frontier
// (unexplored neighbours) hints at what a future run would reveal.
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { SegBar } from '../components.jsx'

const SQRT3 = Math.sqrt(3)
const NEIGHBOURS = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]]

// visits → teal ramp (deeper = more familiar territory)
function visitColor(visits) {
  if (visits >= 4) return '#2b8f7a'
  if (visits >= 2) return '#1d5f63'
  return '#16324a'
}

// hex centre in "hex units" (pointy-top axial); pixel scale applied at draw
function hexCenter(q, r) {
  return { x: SQRT3 * (q + r / 2), y: 1.5 * r }
}

function drawHex(ctx, cx, cy, size, fill, stroke, lineWidth = 1) {
  ctx.beginPath()
  for (let i = 0; i < 6; i++) {
    const angle = ((60 * i - 30) * Math.PI) / 180
    const px = cx + size * Math.cos(angle)
    const py = cy + size * Math.sin(angle)
    if (i === 0) ctx.moveTo(px, py)
    else ctx.lineTo(px, py)
  }
  ctx.closePath()
  if (fill) { ctx.fillStyle = fill; ctx.fill() }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lineWidth; ctx.stroke() }
}

export default function WorldMap() {
  const canvasRef = useRef(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  // view: pixels per hex-unit + offset (in canvas px)
  const viewRef = useRef({ scale: 26, ox: 0, oy: 0, centered: false })
  const [, forceDraw] = useState(0)

  useEffect(() => {
    api.map().then(setData).catch((e) => setError(String(e.message || e)))
  }, [])

  // -- rendering ------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !data) return
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.imageSmoothingEnabled = false

    const view = viewRef.current
    if (!view.centered) {
      // first draw: center on the player (or the map's centroid)
      const target = data.player || data.hexes[0] || { q: 0, r: 0 }
      const c = hexCenter(target.q, target.r)
      view.ox = rect.width / 2 - c.x * view.scale
      view.oy = rect.height / 2 - c.y * view.scale
      view.centered = true
    }

    ctx.fillStyle = getComputedStyle(document.documentElement)
      .getPropertyValue('--bg-abyss').trim() || '#0b0e1a'
    ctx.fillRect(0, 0, rect.width, rect.height)

    const visited = new Set(data.hexes.map((h) => `${h.q},${h.r}`))
    const frontier = new Set()
    data.hexes.forEach((h) => {
      NEIGHBOURS.forEach(([dq, dr]) => {
        const key = `${h.q + dq},${h.r + dr}`
        if (!visited.has(key)) frontier.add(key)
      })
    })

    const size = view.scale // hex circumradius in px (hex units: R=1)
    const toPx = (q, r) => {
      const c = hexCenter(q, r)
      return { x: c.x * size + view.ox, y: c.y * size + view.oy }
    }

    // frontier first (under the visited hexes visually)
    frontier.forEach((key) => {
      const [q, r] = key.split(',').map(Number)
      const { x, y } = toPx(q, r)
      if (x < -size * 2 || y < -size * 2 || x > rect.width + size * 2 || y > rect.height + size * 2) return
      drawHex(ctx, x, y, size * 0.96, '#11162a', '#1c2340')
    })

    data.hexes.forEach((h) => {
      const { x, y } = toPx(h.q, h.r)
      if (x < -size * 2 || y < -size * 2 || x > rect.width + size * 2 || y > rect.height + size * 2) return
      drawHex(ctx, x, y, size * 0.96, visitColor(h.visits), '#0b0e1a', 2)
      if (h.newThisWeek) drawHex(ctx, x, y, size * 0.82, null, '#ffd166', 1.5)
    })

    if (data.player) {
      const { x, y } = toPx(data.player.q, data.player.r)
      drawHex(ctx, x, y, size * 0.6, null, '#3ee6c1', 3)
      ctx.fillStyle = '#3ee6c1'
      ctx.beginPath()
      ctx.arc(x, y, Math.max(size * 0.14, 2.5), 0, Math.PI * 2)
      ctx.fill()
    }
  })

  // -- pan & zoom -------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const view = viewRef.current
    const pointers = new Map()
    let lastPinch = null

    const redraw = () => forceDraw((n) => n + 1)

    const onDown = (e) => {
      canvas.setPointerCapture(e.pointerId)
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
    }
    const onMove = (e) => {
      const prev = pointers.get(e.pointerId)
      if (!prev) return
      const cur = { x: e.clientX, y: e.clientY }
      pointers.set(e.pointerId, cur)
      if (pointers.size === 1) {
        view.ox += cur.x - prev.x
        view.oy += cur.y - prev.y
        redraw()
      } else if (pointers.size === 2) {
        const [a, b] = [...pointers.values()]
        const dist = Math.hypot(a.x - b.x, a.y - b.y)
        if (lastPinch) {
          const factor = dist / lastPinch
          const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
          const rect = canvas.getBoundingClientRect()
          zoomAt(mid.x - rect.left, mid.y - rect.top, factor)
        }
        lastPinch = dist
      }
    }
    const onUp = (e) => {
      pointers.delete(e.pointerId)
      if (pointers.size < 2) lastPinch = null
    }
    const zoomAt = (cx, cy, factor) => {
      const next = Math.min(Math.max(view.scale * factor, 5), 90)
      const real = next / view.scale
      view.ox = cx - (cx - view.ox) * real
      view.oy = cy - (cy - view.oy) * real
      view.scale = next
      redraw()
    }
    const onWheel = (e) => {
      e.preventDefault()
      const rect = canvas.getBoundingClientRect()
      zoomAt(e.clientX - rect.left, e.clientY - rect.top, e.deltaY < 0 ? 1.12 : 1 / 1.12)
    }

    canvas.addEventListener('pointerdown', onDown)
    canvas.addEventListener('pointermove', onMove)
    canvas.addEventListener('pointerup', onUp)
    canvas.addEventListener('pointercancel', onUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })
    return () => {
      canvas.removeEventListener('pointerdown', onDown)
      canvas.removeEventListener('pointermove', onMove)
      canvas.removeEventListener('pointerup', onUp)
      canvas.removeEventListener('pointercancel', onUp)
      canvas.removeEventListener('wheel', onWheel)
    }
  }, [data])

  if (error) {
    return (
      <div className="screen stack">
        <div className="px-panel" style={{ color: 'var(--neon-boss)', fontSize: 12 }}>
          Carte indisponible : {error}
        </div>
      </div>
    )
  }

  const geoQuest = data?.geoQuests?.[0]

  return (
    <div className="screen" style={{ position: 'relative', padding: 0, overflow: 'hidden' }}>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%', height: 'calc(100vh - 64px)', display: 'block',
          touchAction: 'none', cursor: 'grab',
        }}
      />
      <div
        className="px-panel"
        style={{
          position: 'absolute', top: 10, left: 10, right: 10,
          background: 'rgba(21,26,46,0.92)', fontSize: 11, color: 'var(--ink-dim)',
        }}
      >
        {!data ? (
          <span className="font-px" style={{ fontSize: 10 }}>DÉCHIFFRAGE DE LA CARTE…</span>
        ) : (
          <>
            <div className="font-px" style={{ fontSize: 10, color: 'var(--ink)', marginBottom: 6 }}>
              🗺️ CARTE DU ROYAUME — {data.hexes.length} hexagone{data.hexes.length > 1 ? 's' : ''} révélé{data.hexes.length > 1 ? 's' : ''}
              {data.newHexesThisWeek > 0 && (
                <span style={{ color: 'var(--gold)' }}> · +{data.newHexesThisWeek} cette semaine</span>
              )}
            </div>
            {geoQuest && (
              <div style={{ marginBottom: 6 }}>
                <SegBar
                  value={geoQuest.progress} max={geoQuest.target} segments={10} thin
                  label={geoQuest.label} valueLabel={`${geoQuest.progress}/${geoQuest.target}`}
                  color="var(--gold)"
                />
              </div>
            )}
            {data.pendingActivities > 0 && (
              <div>⏳ {data.pendingActivities} trace{data.pendingActivities > 1 ? 's' : ''} en cours de
                déchiffrage — rouvre la carte ou synchronise pour continuer.</div>
            )}
            {data.demo && <div>Carte simulée (mode démo) — connecte Garmin pour explorer ton vrai territoire.</div>}
            {data.hexes.length === 0 && !data.pendingActivities && (
              <div>Aucune trace GPS pour l'instant : sors courir, la carte naîtra de tes pas.</div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
