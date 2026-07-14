// Carte du Royaume — the REAL map (Strava-like): OSM tiles darkened to the
// Néon Grimoire palette, your actual tracks, your position, and your past
// routes pinned as re-runnable segment quests. The hex fog of war remains
// as an optional overlay (it drives the "reveal new hexes" quests).
import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { api } from '../api'
import { SegBar } from '../components.jsx'

const SQRT3 = Math.sqrt(3)
const M_PER_DEG_LAT = 111320

function visitColor(visits) {
  if (visits >= 4) return '#2b8f7a'
  if (visits >= 2) return '#1d5f63'
  return '#16324a'
}

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

const playerIcon = L.divIcon({
  className: 'player-marker',
  html: '<div class="player-dot"></div>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})

export default function WorldMap() {
  const mapEl = useRef(null)
  const mapRef = useRef(null)
  const fogLayerRef = useRef(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [fog, setFog] = useState(false)

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
      className: 'grimoire-tiles', // CSS dark filter (styles.css)
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map)

    // Past tracks — the territory you actually covered
    data.tracks.forEach((t) => {
      if (t.points.length > 1) {
        L.polyline(t.points, { color: '#3ee6c1', weight: 3, opacity: 0.55 }).addTo(map)
      }
    })

    // Segments — past routes as quests on the map
    data.segments.forEach((seg) => {
      if (seg.points.length < 2) return
      const color = seg.doneThisWeek ? '#7ee881' : '#ffd166'
      const line = L.polyline(seg.points, { color, weight: 5, opacity: 0.9 }).addTo(map)
      line.bindPopup(
        `<div class="seg-popup"><b>⚔️ ${seg.name}</b><br/>` +
        `${seg.distanceKm} km · couru le ${seg.date}<br/>` +
        (seg.doneThisWeek
          ? '<span style="color:#7ee881">✓ reparcouru cette semaine</span>'
          : '<span style="color:#ffd166">Quête : reparcours cet itinéraire</span>') +
        '</div>'
      )
    })

    // Player position — end of the latest track
    if (data.player) {
      L.marker([data.player.lat, data.player.lon], { icon: playerIcon })
        .addTo(map)
        .bindPopup('<b>Tu es ici</b> (fin de ta dernière sortie)')
    }

    // Fog of war overlay (toggle) — the hexes behind the geo quests
    const fogLayer = L.layerGroup(
      data.hexes
        .filter((h) => h.lat != null)
        .map((h) =>
          L.polygon(hexCorners(h.lat, h.lon, data.hexRadiusM * 0.96), {
            color: h.newThisWeek ? '#ffd166' : '#0b0e1a',
            weight: h.newThisWeek ? 2 : 1,
            fillColor: visitColor(h.visits),
            fillOpacity: 0.4,
          })
        )
    )
    fogLayerRef.current = fogLayer

    const focus = data.player
      ? [data.player.lat, data.player.lon]
      : data.tracks.length
        ? data.tracks[data.tracks.length - 1].points[0]
        : data.origin
          ? [data.origin.lat, data.origin.lon]
          : [48.8566, 2.3522]
    map.setView(focus, 13)

    return () => { map.remove(); mapRef.current = null }
  }, [data])

  useEffect(() => {
    const map = mapRef.current
    const layer = fogLayerRef.current
    if (!map || !layer) return
    if (fog) layer.addTo(map)
    else layer.remove()
  }, [fog])

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
  const pendingSegs = data?.segments?.filter((s) => !s.doneThisWeek).length || 0

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
              🗺️ CARTE DU ROYAUME
              {data.segments.length > 0 && (
                <span style={{ color: 'var(--gold)' }}> · {pendingSegs} segment{pendingSegs > 1 ? 's' : ''} à reparcourir</span>
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
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <a
                onClick={() => setFog(!fog)}
                style={{ color: fog ? 'var(--neon-xp)' : 'var(--ink-dim)', textDecoration: 'underline', cursor: 'pointer' }}
              >
                {fog ? '🌫️ Voile d\'exploration : visible' : '🌫️ Afficher le voile d\'exploration'}
              </a>
              {data.pendingActivities > 0 && (
                <span>⏳ {data.pendingActivities} trace{data.pendingActivities > 1 ? 's' : ''} en déchiffrage</span>
              )}
              {data.demo && <span>Carte simulée (mode démo)</span>}
            </div>
            {data.tracks.length === 0 && !data.pendingActivities && (
              <div style={{ marginTop: 6 }}>Aucune trace GPS pour l'instant : sors courir, la carte naîtra de tes pas.</div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
