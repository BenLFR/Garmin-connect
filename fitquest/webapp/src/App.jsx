import { useEffect, useState } from 'react'
import { api } from './api'
import { TabBar, LevelUpModal, useFloaters } from './components.jsx'
import Onboarding from './screens/Onboarding.jsx'
import Tavern from './screens/Tavern.jsx'
import Hero from './screens/Hero.jsx'
import Quests from './screens/Quests.jsx'
import Journal from './screens/Journal.jsx'

export default function App() {
  const [state, setState] = useState(null) // null = loading
  const [needsOnboarding, setNeedsOnboarding] = useState(false)
  const [tab, setTab] = useState('tavern')
  const [lastEvent, setLastEvent] = useState(null)
  const [levelUp, setLevelUp] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [floatLayer, spawnFloat] = useFloaters()

  const refresh = async () => {
    const res = await api.getState()
    if (res.onboardingRequired) setNeedsOnboarding(true)
    else { setState(res); setNeedsOnboarding(false) }
  }

  useEffect(() => { refresh().catch(console.error) }, [])

  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await api.sync()
      const ev = res.newActivities?.[0]
      if (ev) {
        setLastEvent({ ...ev, questRewards: res.questRewards || [], recoveryReward: res.recoveryReward })
        if (res.recoveryReward) {
          setTimeout(() => spawnFloat(`REPOS +${res.recoveryReward.xp} XP`, { x: 30, y: 56 }), 1100)
        }
        spawnFloat(`+${ev.activity.xpBreakdown.xp} XP`, { x: 42, y: 38 })
        if (ev.bossDamage > 0) {
          const critTag = ev.critical ? ' CRIT!' : ''
          setTimeout(() => spawnFloat(`-${ev.bossDamage} PV${critTag}`, { dmg: true, x: 58, y: 30 }), 350)
        }
        ;(res.questRewards || []).forEach((qr, i) =>
          setTimeout(() => spawnFloat(`QUÊTE +${qr.rewardXp} XP`, { x: 38, y: 50 }), 800 + i * 300))
      }
      setState(res.state)
      if (res.leveledUp) setTimeout(() => setLevelUp(res.levelAfter), 700)
    } catch (e) {
      console.error(e)
    } finally {
      setSyncing(false)
    }
  }

  if (needsOnboarding) {
    return (
      <div className="app-shell">
        <Onboarding onDone={refresh} />
      </div>
    )
  }

  if (!state) {
    return (
      <div className="app-shell" style={{ justifyContent: 'center', textAlign: 'center' }}>
        <div className="font-px" style={{ color: 'var(--ink-dim)', fontSize: 11 }}>CHARGEMENT…</div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      {tab === 'tavern' && <Tavern state={state} lastEvent={lastEvent} onSync={handleSync} syncing={syncing} />}
      {tab === 'hero' && <Hero state={state} />}
      {tab === 'quests' && <Quests state={state} />}
      {tab === 'journal' && <Journal />}
      <TabBar active={tab} onChange={setTab} />
      {floatLayer}
      {levelUp && <LevelUpModal level={levelUp} onClose={() => setLevelUp(null)} />}
    </div>
  )
}
