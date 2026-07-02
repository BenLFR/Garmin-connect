// Héros — RPG character sheet (Game UI Database codes: segmented stat bars,
// big central sprite, trophies).
import { StatRows } from '../components.jsx'
import { HeroSprite } from '../sprites.jsx'

export default function Hero({ state }) {
  const { player, level, characterSheet, prCount, weekStreak } = state
  return (
    <div className="screen stack">
      <div className="px-panel" style={{ textAlign: 'center', paddingTop: 24 }}>
        <HeroSprite playerClass={player.class} size={128} halo={`${player.classColor}66`} />
        <div className="font-px" style={{ fontSize: 14, marginTop: 14 }}>{player.name}</div>
        <div style={{ color: player.classColor, fontSize: 12, marginTop: 6, textTransform: 'uppercase', letterSpacing: 2 }}>
          {player.className} niv. {level.level}
        </div>
        <div style={{ color: 'var(--ink-dim)', fontSize: 11, marginTop: 6 }}>
          {level.totalXp.toLocaleString('fr-FR')} XP au total
        </div>
      </div>

      <div className="px-panel">
        <h2 className="px" style={{ marginBottom: 14 }}>Attributs</h2>
        <StatRows sheet={characterSheet} />
        <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginTop: 14, lineHeight: 1.5 }}>
          Recalculés chaque nuit depuis tes vraies données Garmin.
          La <b style={{ color: 'var(--neon-vital)' }}>VITALITÉ</b> monte quand tu dors et récupères —
          elle amplifie tes dégâts contre les boss.
        </p>
      </div>

      <div className="px-panel">
        <h2 className="px" style={{ marginBottom: 12 }}>Hauts faits</h2>
        <div className="trophy-grid">
          <div className="trophy">🏆<div className="tcap">{prCount} records</div></div>
          <div className="trophy">🔥<div className="tcap">{weekStreak} semaines</div></div>
          <div className="trophy">⭐<div className="tcap">niveau {level.level}</div></div>
        </div>
      </div>
    </div>
  )
}
