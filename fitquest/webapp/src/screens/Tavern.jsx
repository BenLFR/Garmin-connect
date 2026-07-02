// Taverne (home) — NRC pattern: today's state first, one primary CTA.
import { useState } from 'react'
import { SegBar, VitalChip } from '../components.jsx'
import { HeroSprite, ACTIVITY_ICONS } from '../sprites.jsx'

export default function Tavern({ state, lastEvent, onSync, syncing }) {
  const { player, level, streakDays, wellness, boss } = state
  const readiness = wellness.readiness
  const readinessColor = readiness < 25 ? 'var(--neon-boss)' : readiness < 50 ? 'var(--neon-streak)' : 'var(--neon-vital)'
  const lastAct = lastEvent?.activity

  return (
    <div className="screen stack">
      <header className="hero-header">
        <HeroSprite playerClass={player.class} size={64} halo={`${player.classColor}55`} />
        <div>
          <div className="hname">{player.name}</div>
          <div className="hclass" style={{ color: player.classColor }}>{player.className} · {player.archetype}</div>
        </div>
        <div className="lvl-medal">
          <div className="n">{level.level}</div>
          <div className="t">NIVEAU</div>
        </div>
      </header>

      <div className="px-panel">
        <SegBar
          value={level.xpInLevel} max={level.xpToNext} segments={22}
          label={`NIVEAU ${level.level}`}
          valueLabel={`${level.xpInLevel.toLocaleString('fr-FR')} / ${level.xpToNext.toLocaleString('fr-FR')} XP`}
        />
      </div>

      <div className="vitals">
        <VitalChip icon="🔥" num={streakDays} cap="streak" color="var(--neon-streak)" />
        <VitalChip icon="⚡" num={readiness} cap="énergie" color={readinessColor} />
        <VitalChip icon="😴" num={wellness.sleepScore} cap="sommeil" color="var(--neon-arc)" />
      </div>

      {readiness < 50 && (
        <div className="px-panel" style={{ fontSize: 12, color: 'var(--ink-dim)' }}>
          ⚠️ <b style={{ color: readinessColor }}>Énergie basse.</b> Ton corps réclame du repos :
          l'XP est plafonnée à ×{readiness < 25 ? '0.3' : '0.7'} aujourd'hui. Récupérer, c'est jouer.
        </div>
      )}

      {lastAct ? (
        <div className="px-panel raised">
          <h2 className="px" style={{ marginBottom: 10 }}>Dernière séance</h2>
          <div className="act-row" style={{ border: 'none', padding: 0 }}>
            <span className="aicon">{ACTIVITY_ICONS[lastAct.activityType] || '⚔️'}</span>
            <div style={{ flex: 1 }}>
              <div className="atitle">
                {lastAct.activityName}
                {lastAct.isPR && <span className="pr-tag">★ RECORD</span>}
              </div>
              <div className="asub">{lastAct.durationMinutes} min · load {lastAct.trainingLoad}</div>
            </div>
            <span className="axp">+{lastAct.xpBreakdown.xp} XP</span>
          </div>
          {lastEvent.bossDamage > 0 && (
            <div className="xp-detail" style={{ marginTop: 8 }}>
              🗡️ {lastEvent.bossDamage} dégâts à {boss.name}
              {lastEvent.critical && <b style={{ color: 'var(--neon-boss)' }}> COUP CRITIQUE ×1.2 !</b>}
              {lastEvent.bossDefeated && <b style={{ color: 'var(--gold)' }}> — BOSS VAINCU ! +{lastEvent.bossRewardXp} XP</b>}
            </div>
          )}
          {lastEvent.worldBossDamage > 0 && (
            <div className="xp-detail">
              🐉 {lastEvent.worldBossDamage} dégâts au world boss (bonus de guilde inclus)
              {lastEvent.worldBossDefeated && <b style={{ color: 'var(--gold)' }}> — RAID VICTORIEUX ! +{lastEvent.worldBossRewardXp} XP</b>}
            </div>
          )}
          {(lastEvent.questRewards || []).map((qr) => (
            <div className="xp-detail" key={qr.label} style={{ color: 'var(--gold)' }}>
              📜 Quête accomplie : {qr.label} (+{qr.rewardXp} XP)
            </div>
          ))}
        </div>
      ) : (
        <div className="px-panel" style={{ fontSize: 13, color: 'var(--ink-dim)' }}>
          🍺 Bienvenue à la taverne, {player.name}. Synchronise ta prochaine séance
          pour engranger de l'XP et attaquer <b style={{ color: 'var(--neon-boss)' }}>{boss.name}</b>.
        </div>
      )}

      <button className="px-btn" onClick={onSync} disabled={syncing}>
        {syncing ? 'SYNCHRONISATION…' : player.mode === 'demo' ? '⚔️ SIMULER UNE SÉANCE' : '⌚ SYNCHRONISER GARMIN'}
      </button>
    </div>
  )
}
