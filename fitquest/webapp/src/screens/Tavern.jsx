// Taverne (home) — NRC pattern: today's state first, one primary CTA.
import { useState } from 'react'
import { SegBar, VitalChip } from '../components.jsx'
import { HeroSprite, ACTIVITY_ICONS } from '../sprites.jsx'

function ReminderPanel() {
  const supported = typeof Notification !== 'undefined'
  const [enabled, setEnabled] = useState(
    () => supported && Notification.permission === 'granted' && localStorage.getItem('fq_notify') === '1'
  )
  if (!supported) return null
  const enable = async () => {
    const perm = await Notification.requestPermission()
    if (perm === 'granted') {
      localStorage.setItem('fq_notify', '1')
      setEnabled(true)
    }
  }
  const disable = () => {
    localStorage.removeItem('fq_notify')
    setEnabled(false)
  }
  return (
    <div className="px-panel" style={{ fontSize: 11, color: 'var(--ink-dim)' }}>
      {enabled ? (
        <>🔔 <b style={{ color: 'var(--neon-vital)' }}>Rappel matinal activé.</b>{' '}
          Ton énergie du jour s'affiche à l'ouverture de FitQuest.{' '}
          <a onClick={disable} style={{ color: 'var(--ink-dim)', textDecoration: 'underline', cursor: 'pointer' }}>Désactiver</a></>
      ) : (
        <>
          <a onClick={enable} style={{ color: 'var(--neon-xp)', textDecoration: 'underline', cursor: 'pointer', fontWeight: 700 }}>
            🔔 Activer le rappel matinal
          </a>{' '}
          — une notification locale avec ton énergie du jour, à l'ouverture de l'app
          (pas de serveur de push ; sur iPhone : installe d'abord FitQuest sur l'écran d'accueil, iOS 16.4+).
        </>
      )}
    </div>
  )
}

export default function Tavern({ state, lastEvent, onSync, syncing }) {
  const { player, level, weekStreak, weekPattern, wellness, boss, intensity, spikeGuard } = state
  const readiness = wellness.readiness
  const readinessColor = readiness < 25 ? 'var(--neon-boss)' : readiness < 50 ? 'var(--neon-streak)' : 'var(--neon-vital)'
  const lastAct = lastEvent?.activity
  const days = weekPattern.activeDaysThisWeek
  const overTraining = days > weekPattern.healthyMax

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
        <VitalChip icon="🔥" num={weekStreak} cap="semaines" color="var(--neon-streak)" />
        <VitalChip icon="⚡" num={readiness} cap="énergie" color={readinessColor} />
        <VitalChip icon="😴" num={wellness.sleepScore} cap="sommeil" color="var(--neon-arc)" />
      </div>

      <div className="px-panel" style={{ fontSize: 12, color: 'var(--ink-dim)' }}>
        📅 <b style={{ color: overTraining ? 'var(--neon-boss)' : 'var(--ink)' }}>
        {days} jour{days > 1 ? 's' : ''} actif{days > 1 ? 's' : ''} cette semaine</b>
        {' '}(cible : {weekPattern.healthyMin}-{weekPattern.healthyMax} + repos).
        {overTraining
          ? ' Trop de jours sans repos : la semaine ne comptera pas dans ton streak — tes tendons se reconstruisent les jours off.'
          : ' Les jours de repos rapportent de l’XP de récupération.'}
      </div>

      {intensity && intensity.totalMinutes > 0 && (
        <div className="px-panel">
          <SegBar
            value={intensity.intenseMinutes}
            max={Math.max(intensity.budgetMinutes, intensity.intenseMinutes, 1)}
            segments={16} thin
            label="BUDGET D'INTENSITÉ"
            valueLabel={`${intensity.intenseMinutes} / ${intensity.budgetMinutes} min`}
            color={intensity.over ? 'var(--neon-boss)' : 'var(--neon-arc)'}
          />
          <div style={{ fontSize: 11, color: 'var(--ink-dim)', marginTop: 8 }}>
            {intensity.over
              ? `⚠️ Plus de ${Math.round(intensity.target * 100)} % de tes minutes en haute intensité : l'XP des séances intenses est réduite ×0.6. Le volume facile reconstruit le budget.`
              : `~${Math.round(intensity.target * 100)} % de tes minutes hebdo peuvent être intenses à plein tarif — la structure pyramidale qui fait progresser.`}
            {spikeGuard?.cap != null && (
              <> {' '}🛡️ Plafond anti-spike : {Math.round(spikeGuard.cap)} de load max par séance (110 % de ta plus grosse sortie sur 30 j).</>
            )}
          </div>
        </div>
      )}

      {readiness < 50 && (
        <div className="px-panel" style={{ fontSize: 12, color: 'var(--ink-dim)' }}>
          ⚠️ <b style={{ color: readinessColor }}>Énergie basse (HRV sous ta zone normale).</b>{' '}
          L'XP est plafonnée à ×{readiness < 25 ? '0.3' : '0.7'} aujourd'hui.
          Une séance facile en Z1 ou du repos te rendra plus fort. Récupérer, c'est jouer.
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
              {lastEvent.spikeCapped && <b style={{ color: 'var(--neon-streak)' }}> (plafonnés — séance bien plus grosse que ton habitude)</b>}
              {lastEvent.bossDefeated && <b style={{ color: 'var(--gold)' }}> — BOSS VAINCU ! +{lastEvent.bossRewardXp} XP</b>}
            </div>
          )}
          {lastEvent.recoveryReward && (
            <div className="xp-detail" style={{ color: 'var(--neon-vital)' }}>
              🌙 Jour de repos respecté hier : +{lastEvent.recoveryReward.xp} XP de récupération
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

      <ReminderPanel />
    </div>
  )
}
