// Quêtes — boss HP bar (raid code: damage per session, floating numbers
// handled app-side), reward preview.
import { SegBar } from '../components.jsx'
import { BossSprite } from '../sprites.jsx'

export default function Quests({ state }) {
  const { boss, player } = state
  const hpPct = boss.maxHp > 0 ? Math.round((boss.hp / boss.maxHp) * 100) : 0
  return (
    <div className="screen stack">
      <div className="px-panel boss" style={{ textAlign: 'center', paddingTop: 22 }}>
        <BossSprite size={120} />
        <div className="font-px" style={{ fontSize: 13, marginTop: 12, color: 'var(--neon-boss)' }}>
          {boss.name.toUpperCase()}
        </div>
        <div style={{ color: 'var(--ink-dim)', fontSize: 11, marginTop: 6 }}>
          Boss du palier {boss.level}
        </div>
        <div style={{ marginTop: 16 }}>
          <SegBar
            value={boss.hp} max={boss.maxHp} segments={24}
            color="var(--neon-boss)" glow="rgba(255,77,143,0.5)"
            label="PV" valueLabel={`${boss.hp.toLocaleString('fr-FR')} / ${boss.maxHp.toLocaleString('fr-FR')} (${hpPct}%)`}
          />
        </div>
        <p style={{ fontSize: 12, color: 'var(--ink-dim)', marginTop: 14, lineHeight: 1.5 }}>
          {boss.lore}
        </p>
        <div className="font-px" style={{ fontSize: 9, color: 'var(--gold)', marginTop: 12 }}>
          RÉCOMPENSE : +{boss.rewardXp.toLocaleString('fr-FR')} XP
        </div>
      </div>

      <div className="px-panel">
        <h2 className="px" style={{ marginBottom: 12 }}>Comment le vaincre</h2>
        <ul style={{ listStyle: 'none', fontSize: 13, color: 'var(--ink-dim)', display: 'grid', gap: 10 }}>
          <li>🗡️ Chaque séance inflige des dégâts égaux à ton Training Load.</li>
          <li>💚 Ta VITALITÉ amplifie les dégâts (×0.75 épuisé → ×1.25 reposé).</li>
          <li>📏 Ses PV = ~115 % de ta semaine type : un défi, jamais un mur.</li>
        </ul>
      </div>

      <div className="px-panel" style={{ fontSize: 12, color: 'var(--ink-dim)' }}>
        🛡️ <b style={{ color: 'var(--neon-arc)' }}>Bientôt :</b> world boss de guilde —
        toute ta party {player.className === 'Voyageur' ? 'de voyageurs' : 'mixte'} tape
        la même barre de vie. Recrute des profils variés, le bonus de diversité t'attend.
      </div>
    </div>
  )
}
