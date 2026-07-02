// Shared UI components — the DESIGN_SYSTEM.md library.
import { useEffect, useRef, useState } from 'react'

// Animated numeric value (bars never jump — everything tweens)
export function useTween(target, duration = 600) {
  const [value, setValue] = useState(target)
  const fromRef = useRef(target)
  useEffect(() => {
    const from = fromRef.current
    if (from === target) return
    const t0 = performance.now()
    let raf
    const tick = (t) => {
      const p = Math.min((t - t0) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3) // ease-out cubic
      setValue(from + (target - from) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
      else fromRef.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])
  return value
}

// Segmented RPG bar (XP / HP / stats)
export function SegBar({ value, max, segments = 20, color, glow, thin, label, valueLabel }) {
  const animated = useTween(max > 0 ? value / max : 0)
  const filled = animated * segments
  return (
    <div>
      {label != null && (
        <div className="bar-label">
          <span>{label}</span>
          {valueLabel != null && <span className="val">{valueLabel}</span>}
        </div>
      )}
      <div
        className={`seg-bar${thin ? ' thin' : ''}`}
        style={{ '--seg-color': color, '--seg-glow': glow }}
        role="progressbar" aria-valuenow={Math.round(value)} aria-valuemax={max}
      >
        {Array.from({ length: segments }, (_, i) => {
          const cls = i + 1 <= filled ? 'on' : i < filled ? 'half' : ''
          return <span key={i} className={`seg ${cls}`} />
        })}
      </div>
    </div>
  )
}

export function VitalChip({ icon, num, cap, color }) {
  return (
    <div className="vital-chip">
      <div className="icon">{icon}</div>
      <div className="num" style={color ? { color } : undefined}>{num}</div>
      <div className="cap">{cap}</div>
    </div>
  )
}

const STAT_META = {
  stamina: { name: 'STAMINA', color: '#3ee6c1' },
  force: { name: 'FORCE', color: '#ffb347' },
  agilite: { name: 'AGILITÉ', color: '#ff4d8f' },
  vitalite: { name: 'VITALITÉ', color: '#7ee881' },
  discipline: { name: 'DISCIPLINE', color: '#8f7bff' },
}

export function StatRows({ sheet }) {
  return (
    <div>
      {Object.entries(STAT_META).map(([key, meta]) => (
        <div className="stat-row" key={key}>
          <span className="name">{meta.name}</span>
          <SegBar value={sheet[key] ?? 0} max={100} segments={16} thin color={meta.color} glow={`${meta.color}55`} />
          <span className="num">{sheet[key] ?? 0}</span>
        </div>
      ))}
    </div>
  )
}

// Floating +XP / damage numbers (universal RPG feedback code)
let floatSeq = 0
export function useFloaters() {
  const [floaters, setFloaters] = useState([])
  const spawn = (text, { dmg = false, x = 50, y = 40 } = {}) => {
    const id = ++floatSeq
    setFloaters((f) => [...f, { id, text, dmg, x, y }])
    setTimeout(() => setFloaters((f) => f.filter((i) => i.id !== id)), 950)
  }
  const layer = (
    <div className="float-layer">
      {floaters.map((f) => (
        <span key={f.id} className={`float-xp${f.dmg ? ' dmg' : ''}`} style={{ left: `${f.x}%`, top: `${f.y}%` }}>
          {f.text}
        </span>
      ))}
    </div>
  )
  return [layer, spawn]
}

export function LevelUpModal({ level, onClose }) {
  const particles = Array.from({ length: 26 }, (_, i) => {
    const angle = (i / 26) * Math.PI * 2
    const dist = 90 + (i % 5) * 26
    return (
      <span key={i} className="particle" style={{
        left: '50%', top: '42%',
        '--dx': `${Math.cos(angle) * dist}px`,
        '--dy': `${Math.sin(angle) * dist}px`,
        background: i % 3 === 0 ? '#3ee6c1' : i % 3 === 1 ? '#ffd166' : '#8f7bff',
        animationDelay: `${(i % 4) * 60}ms`,
      }} />
    )
  })
  return (
    <div className="overlay" onClick={onClose} role="dialog" aria-label="Niveau supérieur">
      <div className="levelup-card">
        {particles}
        <div className="levelup-title">LEVEL UP!</div>
        <div className="levelup-num"><RollingNumber target={level} /></div>
        <div style={{ color: 'var(--ink-dim)', fontSize: 13 }}>
          Ton palier monte — un nouveau boss t'attend dans les Quêtes.
        </div>
        <div style={{ marginTop: 18, fontFamily: 'var(--px)', fontSize: 9, color: 'var(--ink-dim)' }}>
          TAPER POUR CONTINUER
        </div>
      </div>
    </div>
  )
}

export function RollingNumber({ target, duration = 900 }) {
  const v = useTween(target, duration)
  return <>{Math.round(v)}</>
}

const TABS = [
  { id: 'tavern', icon: '🍺', label: 'TAVERNE' },
  { id: 'hero', icon: '🛡️', label: 'HÉROS' },
  { id: 'quests', icon: '🐉', label: 'QUÊTES' },
  { id: 'journal', icon: '📜', label: 'JOURNAL' },
]

export function TabBar({ active, onChange }) {
  return (
    <nav className="tab-bar">
      {TABS.map((t) => (
        <button key={t.id} className={active === t.id ? 'active' : ''} onClick={() => onChange(t.id)}>
          <span className="ticon">{t.icon}</span>
          <span className="tlabel">{t.label}</span>
        </button>
      ))}
    </nav>
  )
}
