// Journal — Strava-style feed + full XP-math transparency ("pourquoi j'ai
// gagné ça") so the formula never feels arbitrary.
import { useEffect, useState } from 'react'
import { api } from '../api'
import { ACTIVITY_ICONS } from '../sprites.jsx'

function XpDetail({ bd }) {
  if (!bd) return null
  const parts = [`load ${bd.baseLoad}`]
  if (bd.classMultiplier > 1) parts.push(`classe ×${bd.classMultiplier}`)
  if (bd.streakMultiplier > 1) parts.push(`streak ×${bd.streakMultiplier}`)
  if (bd.readinessCap < 1) parts.push(`fatigue ×${bd.readinessCap}`)
  if (bd.prBonus > 0) parts.push(`record +${bd.prBonus}`)
  return <div className="xp-detail">{parts.join(' · ')}</div>
}

export default function Journal() {
  const [acts, setActs] = useState(null)
  useEffect(() => {
    api.activities().then((d) => setActs(d.activities)).catch(() => setActs([]))
  }, [])

  if (acts === null) {
    return <div className="screen" style={{ color: 'var(--ink-dim)', textAlign: 'center', padding: 40 }}>Chargement du grimoire…</div>
  }

  return (
    <div className="screen">
      <h2 className="px" style={{ marginBottom: 8 }}>Journal de campagne</h2>
      {acts.map((a) => (
        <div className="act-row" key={a.activityId}>
          <span className="aicon">{ACTIVITY_ICONS[a.activityType] || '⚔️'}</span>
          <div style={{ flex: 1 }}>
            <div className="atitle">
              {a.activityName}
              {a.isPR && <span className="pr-tag">★ RECORD</span>}
            </div>
            <div className="asub">{a.startDate} · {a.durationMinutes} min</div>
            <XpDetail bd={a.xpBreakdown} />
          </div>
          <span className="axp">+{a.xpBreakdown?.xp ?? 0} XP</span>
        </div>
      ))}
    </div>
  )
}
