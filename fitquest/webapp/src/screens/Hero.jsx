// Héros — RPG character sheet (Game UI Database codes: segmented stat bars,
// big central sprite, trophies) + cosmetic collection (equip/unequip).
import { useState } from 'react'
import { api } from '../api'
import { StatRows } from '../components.jsx'
import { HeroSprite, GEAR_MAPS, PixelSprite } from '../sprites.jsx'

const SLOT_ICONS = { title: '📜', halo: '✨', gear: '🗡️' }

export function equippedVisuals(cosmetics) {
  const items = cosmetics?.items || []
  const equipped = cosmetics?.equipped || {}
  const byId = Object.fromEntries(items.map((i) => [i.id, i]))
  return {
    title: byId[equipped.title]?.name || null,
    haloColor: byId[equipped.halo]?.color || null,
    gear: equipped.gear || null,
  }
}

function CollectionItem({ item, equipped, busy, onToggle }) {
  const locked = !item.unlocked
  return (
    <div
      className="trophy"
      onClick={() => !locked && !busy && onToggle(item)}
      style={{
        cursor: locked ? 'default' : 'pointer',
        opacity: locked ? 0.35 : 1,
        outline: equipped ? '2px solid var(--gold)' : 'none',
        width: 88,
      }}
      title={locked ? item.unlockLabel : equipped ? 'Équipé — clique pour retirer' : 'Clique pour équiper'}
    >
      {item.slot === 'gear' && GEAR_MAPS[item.id] ? (
        <PixelSprite map={GEAR_MAPS[item.id].map} palette={GEAR_MAPS[item.id].palette} size={40} idle={false} />
      ) : item.slot === 'halo' ? (
        <span style={{ fontSize: 20, textShadow: `0 0 10px ${item.color}` }}>✨</span>
      ) : (
        <span style={{ fontSize: 20 }}>📜</span>
      )}
      <div className="tcap" style={{ color: equipped ? 'var(--gold)' : undefined }}>
        {locked ? `🔒 ${item.unlockLabel}` : item.name}
      </div>
    </div>
  )
}

export default function Hero({ state, onState }) {
  const { player, level, characterSheet, prCount, weekStreak, cosmetics } = state
  const [busy, setBusy] = useState(false)
  const visuals = equippedVisuals(cosmetics)
  const equipped = cosmetics?.equipped || {}

  const toggle = async (item) => {
    setBusy(true)
    try {
      const next = equipped[item.slot] === item.id ? null : item.id
      const res = await api.equip(item.slot, next)
      onState?.(res)
    } catch (e) {
      console.error(e)
    } finally {
      setBusy(false)
    }
  }

  const unlockedCount = (cosmetics?.items || []).filter((i) => i.unlocked).length

  return (
    <div className="screen stack">
      <div className="px-panel" style={{ textAlign: 'center', paddingTop: 24 }}>
        <HeroSprite
          playerClass={player.class} size={128} gear={visuals.gear}
          halo={visuals.haloColor ? `${visuals.haloColor}88` : `${player.classColor}66`}
        />
        <div className="font-px" style={{ fontSize: 14, marginTop: 14 }}>{player.name}</div>
        {visuals.title && (
          <div style={{ color: 'var(--gold)', fontSize: 11, marginTop: 6, letterSpacing: 1 }}>
            « {visuals.title} »
          </div>
        )}
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

      {cosmetics && (
        <div className="px-panel">
          <h2 className="px" style={{ marginBottom: 12 }}>
            Collection {unlockedCount}/{cosmetics.items.length}
          </h2>
          {['title', 'halo', 'gear'].map((slot) => (
            <div key={slot} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10, color: 'var(--ink-dim)', letterSpacing: 2, marginBottom: 6 }}>
                {SLOT_ICONS[slot]} {slot === 'title' ? 'TITRES' : slot === 'halo' ? 'HALOS' : 'ÉQUIPEMENT'}
              </div>
              <div className="trophy-grid">
                {cosmetics.items.filter((i) => i.slot === slot).map((item) => (
                  <CollectionItem
                    key={item.id} item={item} busy={busy}
                    equipped={equipped[item.slot] === item.id}
                    onToggle={toggle}
                  />
                ))}
              </div>
            </div>
          ))}
          <p style={{ fontSize: 11, color: 'var(--ink-dim)', marginTop: 6, lineHeight: 1.5 }}>
            Le butin se gagne aux niveaux, aux boss et aux quêtes — jamais au volume :
            aucune séance monstre ne débloque quoi que ce soit.
          </p>
        </div>
      )}

      <div className="px-panel">
        <h2 className="px" style={{ marginBottom: 12 }}>Hauts faits</h2>
        <div className="trophy-grid">
          <div className="trophy">🏆<div className="tcap">{prCount} records</div></div>
          <div className="trophy">🔥<div className="tcap">{weekStreak} semaines</div></div>
          <div className="trophy">⭐<div className="tcap">niveau {level.level}</div></div>
          {cosmetics && <div className="trophy">⚔️<div className="tcap">{cosmetics.counters.bossKills} boss</div></div>}
        </div>
      </div>
    </div>
  )
}
