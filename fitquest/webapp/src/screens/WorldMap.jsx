// Carte du Royaume — exploration first: the REAL map (OSM), but hidden.
// The world is dark; tiles are only revealed inside the hexes you have
// actually run through. The frontier is half-glimpsed, weekly beacons
// mark unexplored zones to go claim. Your city emerges as you run.
// A toggle shows the full map (with past tracks & segment quests).
import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api'
import { SegBar } from '../components.jsx'

const M_PER_DEG_LAT = 111320
const NEIGHBOURS = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]]

// pointy-top hex corners around a (lat, lon) centre, radius in metres
function hexCorners(lat, lon, radiusM) {
  const corners = []
  for (let i = 0; i < 6; i++) {
    const angle = ((60 * i - 30) * Math.PI) / 180
    const dx = radiusM * Math.cos(angle)
    const dy = radiusM * Math.sin(angle)
    corners.push([
      lat + dy / M_PER_DEG_LAT,
      lon + dx / (M_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180)),
    ])
  }
  return corners
}

function hexKeyToLatLon(h) { return [h.lat, h.lon] }

// Canvas fog-of-war: one dark veil, clearings erased with composite
// 'destination-out'. Unlike an SVG polygon-with-holes (where overlapping
// holes re-fill under the evenodd rule), overlapping erases are invisible
// by construction — no hex tiling ever shows.
function makeFogLayer(explored, frontier, radiusM) {
  const Fog = L.Layer.extend({
    onAdd(map) {
      this._map = map
      this._canvas = L.DomUtil.create('canvas', 'fog-canvas')
      this._canvas.style.pointerEvents = 'none'
      map.getPanes().overlayPane.appendChild(this._canvas)
      map.on('move zoom viewreset resize', this._redraw, this)
      this._redraw()
      return this
    },
    onRemove(map) {
      map.off('move zoom viewreset resize', this._redraw, this)
      L.DomUtil.remove(this._canvas)
      return this
    },
    _tracePath(ctx, cells) {
      const map = this._map
      cells.forEach(({ lat, lon }) => {
        const c = map.latLngToContainerPoint([lat, lon])
        const edge = map.latLngToContainerPoint([
          lat, lon + radiusM / (M_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180)),
        ])
        const rpx = Math.hypot(edge.x - c.x, edge.y - c.y) * 1.04
        for (let i = 0; i < 6; i++) {
          const a = ((60 * i - 30) * Math.PI) / 180
          const x = c.x + rpx * Math.cos(a)
          const y = c.y + rpx * Math.sin(a)
          i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
        }
        ctx.closePath()
      })
    },
    _redraw() {
      const map = this._map
      const size = map.getSize()
      const canvas = this._canvas
      canvas.width = size.x
      canvas.height = size.y
      L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]))
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = 'rgba(11, 14, 26, 0.94)'
      ctx.fillRect(0, 0, size.x, size.y)
      ctx.globalCompositeOperation = 'destination-out'
      ctx.filter = 'blur(6px)' // soft clearing edges, organic look
      ctx.beginPath()
      this._tracePath(ctx, explored)
      ctx.globalAlpha = 1
      ctx.fill() // your territory: fully revealed
      ctx.beginPath()
      this._tracePath(ctx, frontier)
      ctx.globalAlpha = 0.4
      ctx.fill() // the frontier: half-glimpsed, come claim it
      ctx.filter = 'none'
      ctx.globalAlpha = 1
      ctx.globalCompositeOperation = 'source-over'
    },
  })
  return new Fog()
}

const playerIcon = L.divIcon({
  className: 'player-marker',
  html: '<div class="player-dot"></div>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

const beaconIcon = L.divIcon({
  className: 'beacon-marker',
  html: '<div class="beacon-star">⭐</div>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
})

export default function WorldMap() {
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const layersRef = useRef({}) // { fog, frontier, history }
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    api.map().then(setData).catch((e) => setError(String(e.message || e)))
  }, [])

  useEffect(() => {
    if (!data || !mapEl.current || mapRef.current) return

    const map = L.map(mapEl.current, { zoomControl: false, attributionControl: true })
    mapRef.current = map
    L.control.zoom({ position: 'bottomright' }).addTo(map)

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      className: 'grimoire-tiles',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map)

    const explored = data.hexes.filter((h) => h.lat != null)
    const visitedKeys = new Set(explored.map((h) => `${h.q},${h.r}`))
    const byKey = Object.fromEntries(explored.map((h) => [`${h.q},${h.r}`, h]))

    // frontier: unexplored neighbours of explored hexes (positions derived
    // from a neighbour's centre, offset in hex-space via the server radius)
    const frontier = []
    const seen = new Set()
    explored.forEach((h) => {
      NEIGHBOURS.forEach(([dq, dr]) => {
        const key = `${h.q + dq},${h.r + dr}`
        if (visitedKeys.has(key) || seen.has(key)) return
        seen.add(key)
        // approximate the neighbour centre from this hex's latlon
        const R = data.hexRadiusM
        const dx = R * Math.sqrt(3) * (dq + dr / 2)
        const dy = R * 1.5 * dr
        frontier.push({
          lat: h.lat + dy / M_PER_DEG_LAT,
          lon: h.lon + dx / (M_PER_DEG_LAT * Math.cos((h.lat * Math.PI) / 180)),
        })
      })
    })

    // -- FOG OF WAR: one canvas veil, clearings erased (no visible tiling) --
    const center = data.player
      ? [data.player.lat, data.player.lon]
      : explored.length ? hexKeyToLatLon(explored[0]) : [48.8566, 2.3522]
    const fog = makeFogLayer(explored, frontier, data.hexRadiusM)

    // gold rim on hexes revealed this week — visible progress
    const newThisWeek = L.layerGroup(
      explored.filter((h) => h.newThisWeek).map((h) =>
        L.polygon(hexCorners(h.lat, h.lon, data.hexRadiusM * 0.9), {
          color: '#ffd166', weight: 1.5, fill: false, interactive: false,
        })
      )
    )

    // -- HISTORY LAYER (full-map mode): past tracks + segment quests --------
    const historyItems = []
    data.tracks.forEach((t) => {
      if (t.points.length > 1) {
        historyItems.push(L.polyline(t.points, { color: '#3ee6c1', weight: 3, opacity: 0.5 }))
      }
    })
    data.segments.forEach((seg) => {
      if (seg.points.length < 2) return
      const color = seg.doneThisWeek ? '#7ee881' : '#ffd166'
      const line = L.polyline(seg.points, { color, weight: 5, opacity: 0.9 })
      line.bindPopup(
        `<div class="seg-popup"><b>⚔️ ${seg.name}</b><br/>` +
        `${seg.distanceKm} km · couru le ${seg.date}<br/>` +
        (seg.doneThisWeek
          ? '<span style="color:#7ee881">✓ reparcouru cette semaine</span>'
          : '<span style="color:#ffd166">Quête : reparcours cet itinéraire</span>') +
        '</div>'
      )
      historyItems.push(line)
    })
    const history = L.layerGroup(historyItems)

    // -- beacons: weekly unexplored targets, always visible -----------------
    ;(data.explorationTargets || []).forEach((t) => {
      L.marker([t.lat, t.lon], { icon: beaconIcon })
        .addTo(map)
        .bindPopup('<div class="seg-popup"><b>⭐ Zone inexplorée</b><br/>' +
          'Cours jusqu\'ici pour révéler la carte (quête Cartographe).</div>')
    })

    if (data.player) {
      L.marker([data.player.lat, data.player.lon], { icon: playerIcon })
        .addTo(map)
        .bindPopup('<b>Tu es ici</b> (fin de ta dernière sortie)')
    }

    layersRef.current = { fog, newThisWeek, history }
    fog.addTo(map)
    newThisWeek.addTo(map)

    map.setView(center, 13)
    return () => { map.remove(); mapRef.current = null }
  }, [data])

  // exploration mode ⇄ full map
  useEffect(() => {
    const map = mapRef.current
    const { fog, history } = layersRef.current
    if (!map || !fog) return
    if (showAll) {
      map.removeLayer(fog); history.addTo(map)
    } else {
      history.remove(); map.addLayer(fog)
    }
  }, [showAll])

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
      <div ref={mapEl} style={{ width: '100%', height: 'calc(100vh - 64px)' }} />
      <div
        className="px-panel map-hud"
        style={{
          position: 'absolute', top: 10, left: 10, right: 10, zIndex: 1000,
          background: 'rgba(21,26,46,0.92)', fontSize: 11, color: 'var(--ink-dim)',
        }}
      >
        {!data ? (
          <span className="font-px" style={{ fontSize: 10 }}>DÉCHIFFRAGE DE LA CARTE…</span>
        ) : (
          <>
            <div className="font-px" style={{ fontSize: 10, color: 'var(--ink)', marginBottom: 6 }}>
              🗺️ TERRES CONNUES : {data.hexes.length} hexagone{data.hexes.length > 1 ? 's' : ''}
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
            {(data.explorationTargets || []).length > 0 && !showAll && (
              <div style={{ marginBottom: 6 }}>
                ⭐ {data.explorationTargets.length} zone{data.explorationTargets.length > 1 ? 's' : ''} inexplorée{data.explorationTargets.length > 1 ? 's' : ''} balisée{data.explorationTargets.length > 1 ? 's' : ''} cette semaine — cours jusqu'aux étoiles pour dissiper la nuit.
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <a
                onClick={() => setShowAll(!showAll)}
                style={{ color: 'var(--neon-xp)', textDecoration: 'underline', cursor: 'pointer' }}
              >
                {showAll ? '🌫️ Revenir au mode exploration' : '🌍 Tout afficher (traces & segments)'}
              </a>
              {data.pendingActivities > 0 && (
                <span>⏳ {data.pendingActivities} trace{data.pendingActivities > 1 ? 's' : ''} en déchiffrage</span>
              )}
              {data.demo && <span>Carte simulée (mode démo)</span>}
            </div>
            {data.hexes.length === 0 && !data.pendingActivities && (
              <div style={{ marginTop: 6 }}>Le monde entier est encore dans la nuit : sors courir, chaque sortie révèle la carte.</div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
