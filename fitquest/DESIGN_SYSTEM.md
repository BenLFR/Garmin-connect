# FitQuest — Design System « Néon Grimoire »

Pixel art fantasy × dark mode néon. Composants modulaires (logique Figma
Community : tout est token + variant).

## 1. Tokens couleur

| Token | Valeur | Usage |
|-------|--------|-------|
| `--bg-abyss` | `#0b0e1a` | fond app |
| `--bg-panel` | `#151a2e` | cartes / panneaux |
| `--bg-raised` | `#1e2542` | éléments surélevés, tab bar |
| `--ink` | `#e8ecff` | texte principal |
| `--ink-dim` | `#8891b8` | texte secondaire |
| `--neon-xp` | `#3ee6c1` | XP, progression, succès |
| `--neon-boss` | `#ff4d8f` | boss, danger, HP |
| `--neon-streak` | `#ffb347` | streak, feu |
| `--neon-vital` | `#7ee881` | récupération, readiness OK |
| `--neon-arc` | `#8f7bff` | magie, classe, accents |
| `--gold` | `#ffd166` | récompenses, niveaux |

Chaque néon a une variante `-glow` (même teinte, opacité 35 %) pour les
`box-shadow` lumineux.

## 2. Typographie

- **Display / chiffres RPG** : `"Press Start 2P"` (embarquée localement,
  fallback `monospace`) — titres, niveaux, LEVEL UP.
- **Corps** : system stack (`-apple-system, Segoe UI, Roboto…`) — lisibilité
  des textes longs. Le pixel partout fatigue : on le réserve à l'ornement.
- Échelle : 10 / 12 / 14 / 16 / 20 / 28.

## 3. La grammaire "pixel"

- **Bordures pixel** : pas de `border-radius` sur les composants RPG ;
  cadres en marches d'escalier via `clip-path` (`--px-frame`).
- **Sprites** : matrices 16×16 rendues en SVG `<rect>`, upscalées avec
  `image-rendering: pixelated`. Un sprite = un composant `<PixelSprite map=…>`.
- **Barres segmentées** : progression en segments de 8 px espacés de 2 px
  (jamais de barre lisse pour les stats).
- **Ombres** : dures (0 blur, offset 3px) pour le pixel ; glow néon
  (blur 24px) réservé aux éléments "magiques" (XP, level up).

## 4. Composants (bibliothèque)

| Composant | Variants | Notes |
|-----------|----------|-------|
| `PixelPanel` | default / raised / boss | cadre pixel + titre optionnel |
| `XPBar` | xp / hp / stat | segmentée, tween 600 ms ease-out |
| `StatRow` | 5 stats | barre + valeur + delta ▲▼ |
| `PixelSprite` | héros ×5 classes, boss, trophée | idle 2 frames (400 ms) |
| `PixelButton` | primary / ghost / danger | press = translate 2px (tactile) |
| `VitalChip` | streak / readiness / badge | icône + valeur |
| `FloatingXP` | +N XP | monte + fade 900 ms |
| `LevelUpModal` | — | particules + compteur animé |
| `ClassCard` | 5 classes | carrousel onboarding, état recommandé |
| `TabBar` | 4 onglets | icônes pixel, actif = glow |

## 5. Animation

| Nom | Durée | Easing | Usage |
|-----|-------|--------|-------|
| `tween-bar` | 600 ms | cubic-bezier(.22,1,.36,1) | remplissage barres |
| `float-xp` | 900 ms | ease-out | nombres flottants |
| `slide-screen` | 200 ms | ease-out | navigation |
| `sprite-idle` | 800 ms steps(2) | — | respiration des sprites |
| `levelup-burst` | 1200 ms | ease-out | particules étoiles |
| `scanline` | 1400 ms linear loop | — | écran d'analyse onboarding |

Tout est désactivable via `prefers-reduced-motion` (les valeurs finales
s'appliquent sans transition).

## 6. Layout

- Mobile-first 390 px, centré en colonne max 430 px sur desktop (rendu
  "app mobile" même dans le navigateur).
- Grille 8 px. Safe-area bottom pour la tab bar.
- 1 CTA principal max par écran, pleine largeur, hauteur 52 px.
