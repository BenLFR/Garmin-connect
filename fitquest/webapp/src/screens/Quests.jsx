// Quêtes — tier boss (raid HP bar), weekly quests (rotation lundi),
// guild party & world boss: the MMO moment (Game UI Database: quest log,
// raid frames, party list).
import { SegBar } from '../components.jsx'
import { BossSprite, WorldBossSprite, HeroSprite } from '../sprites.jsx'

function QuestCard({ q }) {
  return (
    <div style={{ opacity: q.claimed ? 0.55 : 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: q.done ? 'var(--neon-vital)' : 'var(--ink)' }}>
          {q.done ? '✅' : '◻️'} {q.label}
        </span>
        <span className="font-px" style={{ fontSize: 8, color: 'var(--gold)', whiteSpace: 'nowrap' }}>
          +{q.rewardXp} XP
        </span>
      </div>
      <SegBar value={q.progress} max={q.target} segments={14} thin
        color={q.done ? 'var(--neon-vital)' : 'var(--neon-arc)'} glow="rgba(143,123,255,0.4)" />
      <div style={{ fontSize: 10, color: 'var(--ink-dim)', marginTop: 4, textAlign: 'right' }}>
        {q.progress} / {q.target}
      </div>
    </div>
  )
}

export default function Quests({ state }) {
  const { boss, quests, guild, worldBoss, player } = state
  const hpPct = boss.maxHp > 0 ? Math.round((boss.hp / boss.maxHp) * 100) : 0
  const wbPct = worldBoss.maxHp > 0 ? Math.round((worldBoss.hp / worldBoss.maxHp) * 100) : 0
  const bonusPct = Math.round((guild.diversityBonus - 1) * 100)

  return (
    <div className="screen stack">
      {/* ---- tier boss ---- */}
      <div className="px-panel boss" style={{ textAlign: 'center', paddingTop: 22 }}>
        <BossSprite size={104} />
        <div className="font-px" style={{ fontSize: 13, marginTop: 12, color: 'var(--neon-boss)' }}>
          {boss.name.toUpperCase()}
        </div>
        <div style={{ color: 'var(--ink-dim)', fontSize: 11, marginTop: 6 }}>
          Boss du palier {boss.level} · récompense +{boss.rewardXp.toLocaleString('fr-FR')} XP
        </div>
        <div style={{ marginTop: 14 }}>
          <SegBar value={boss.hp} max={boss.maxHp} segments={24}
            color="var(--neon-boss)" glow="rgba(255,77,143,0.5)"
            label="PV" valueLabel={`${boss.hp.toLocaleString('fr-FR')} / ${boss.maxHp.toLocaleString('fr-FR')} (${hpPct}%)`} />
        </div>
        <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginTop: 12 }}>
          Ton Training Load = tes dégâts · coup critique ×1.2 sur activité de classe
          · ta VITALITÉ amplifie tout · <b style={{ color: 'var(--neon-streak)' }}>dégâts
          plafonnés à 110 % de ta plus grosse séance du mois</b> : la constance tue
          le boss, pas l'héroïsme.
        </p>
      </div>

      {/* ---- weekly quests ---- */}
      <div className="px-panel">
        <h2 className="px" style={{ marginBottom: 14 }}>Défis de la semaine</h2>
        <div style={{ display: 'grid', gap: 16 }}>
          {quests.map((q) => <QuestCard key={q.id} q={q} />)}
        </div>
        <p style={{ fontSize: 10, color: 'var(--ink-dim)', marginTop: 12 }}>
          Rotation chaque lundi. Le 3ᵉ défi est toujours taillé pour ta classe.
        </p>
      </div>

      {/* ---- guild & world boss ---- */}
      <div className="px-panel boss" style={{ textAlign: 'center', paddingTop: 20 }}>
        <div className="font-px" style={{ fontSize: 9, color: 'var(--neon-arc)', marginBottom: 10 }}>
          ⚔️ RAID DE GUILDE — {guild.name.toUpperCase()}
        </div>
        <WorldBossSprite size={150} />
        <div className="font-px" style={{ fontSize: 12, marginTop: 10, color: 'var(--neon-arc)' }}>
          {worldBoss.name.toUpperCase()}
        </div>
        <div style={{ color: 'var(--ink-dim)', fontSize: 11, marginTop: 4 }}>
          World boss · rang {worldBoss.tier} · +{worldBoss.rewardXp.toLocaleString('fr-FR')} XP pour toute la guilde
        </div>
        <div style={{ marginTop: 14 }}>
          <SegBar value={worldBoss.hp} max={worldBoss.maxHp} segments={24}
            color="var(--neon-arc)" glow="rgba(143,123,255,0.5)"
            label="PV COLLECTIFS" valueLabel={`${worldBoss.hp.toLocaleString('fr-FR')} / ${worldBoss.maxHp.toLocaleString('fr-FR')} (${wbPct}%)`} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 14, marginTop: 16 }}>
          <div style={{ textAlign: 'center' }}>
            <HeroSprite playerClass={player.class} size={36} idle={false} />
            <div style={{ fontSize: 9, color: 'var(--gold)', marginTop: 3 }}>{player.name} (toi)</div>
          </div>
          {guild.members.map((m) => (
            <div key={m.name} style={{ textAlign: 'center' }}>
              <HeroSprite playerClass={m.class} size={36} idle={false} />
              <div style={{ fontSize: 9, color: 'var(--ink-dim)', marginTop: 3 }}>{m.name}</div>
            </div>
          ))}
        </div>
        <div className="font-px" style={{ fontSize: 8, color: 'var(--neon-vital)', marginTop: 12 }}>
          BONUS DE DIVERSITÉ : +{bonusPct}% DE DÉGÂTS ({new Set([player.class, ...guild.members.map((m) => m.class)]).size} classes)
        </div>

        {guild.log.length > 0 && (
          <div style={{ marginTop: 14, textAlign: 'left', fontSize: 11, color: 'var(--ink-dim)', display: 'grid', gap: 5 }}>
            {guild.log.map((h, i) => (
              <div key={i}>🗡️ <b style={{ color: 'var(--ink)' }}>{h.name}</b> inflige{' '}
                <span style={{ color: 'var(--neon-boss)' }}>-{h.damage} PV</span></div>
            ))}
          </div>
        )}
        <p style={{ fontSize: 10, color: 'var(--ink-dim)', marginTop: 12 }}>
          Compagnons simulés en mode démo — le vrai multijoueur branchera de vrais héros ici.
        </p>
      </div>
    </div>
  )
}
