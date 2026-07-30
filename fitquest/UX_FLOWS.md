# FitQuest — Écrans & Parcours utilisateurs

Parcours conçus d'après les patterns éprouvés des bibliothèques de référence :

- **Mobbin / PageFlows** — flux d'onboarding et architecture d'apps fitness
  (Nike Run Club, Strava) et gamifiées (Duolingo).
- **Dribbble / Behance** — direction artistique : dark mode, néons, flat sportif.
- **Game UI Database** — codes UI de jeux vidéo : barres d'XP, feuilles de stats,
  pop-ups de succès, barres de vie de boss.
- **Figma Community** — logique de composants modulaires réutilisables.

---

## 1. Onboarding (pattern Duolingo : investir AVANT de demander)

Leçon Mobbin/Duolingo : les meilleurs onboardings font *vivre le produit*
avant tout engagement. Ici, le "aha moment" est la **recommandation de classe
personnalisée** : le jeu te connaît déjà.

```
[S0 Splash]      Logo pixel + tagline. Auto-transition (800 ms).
    ↓
[S1 Bienvenue]   Pitch en 1 écran : « Ton corps est ton personnage. »
    ↓             CTA unique (pattern NRC : 1 action par écran).
[S2 Connexion]   Deux portes : « Connecter Garmin » / « Mode démo » (essai
    ↓             sans friction — pattern PageFlows "try before signup").
[S3 Analyse]     Écran de "scan" animé : on lit les 4 dernières semaines.
    ↓             (progress bar pixel — le temps d'attente devient du jeu)
[S4 Révélation]  « D'après tes données, tu es à 72 % un RÔDEUR. »
    ↓             Carrousel des 5 classes, la recommandée pré-sélectionnée,
    ↓             stats d'affinité par classe (pattern "personality quiz result").
[S5 Confirmation] Fiche de la classe choisie + « Commencer l'aventure ».
    ↓
[Dashboard]
```

Règles reprises de Mobbin :
- 1 idée par écran, CTA unique en bas, zone de pouce.
- Progression visible (dots) — jamais plus de 5 étapes.
- Le choix n'est pas bloquant (respec 1×/saison, annoncé dès S4 → réduit
  l'anxiété de décision).

## 2. Architecture de l'app (pattern Strava/NRC : 4 onglets max)

```
┌────────────────────────────────────────────┐
│  [Taverne]  [Héros]  [Quêtes]  [Journal]   │  ← tab bar pixel, 4 onglets
└────────────────────────────────────────────┘
```

| Onglet | Rôle | Références |
|--------|------|------------|
| **Taverne** (home) | XP bar, niveau, streak, readiness, dernière activité, CTA sync | NRC home (état du jour au centre), Duolingo (streak flame) |
| **Héros** | Feuille de perso : avatar pixel, 5 stats, records | Game UI Database : character sheet RPG (barres segmentées + valeurs) |
| **Quêtes** | Boss de palier avec barre de vie, défis hebdo | Game UI Database : boss HP bar, quest log |
| **Journal** | Feed des activités avec détail du calcul d'XP | Strava feed, transparence du "pourquoi j'ai gagné ça" |

## 3. Écran Taverne (home)

Hiérarchie (pattern NRC : l'état du jour d'abord) :

1. **Header héros** : avatar pixel animé (idle 2 frames), nom, classe, niveau.
2. **Barre d'XP** : segmentée façon RPG, remplissage animé (ease-out), libellé
   `1 240 / 2 100 XP → Niv. 8`.
3. **Rangée de vitaux** : 🔥 streak (pattern Duolingo), ⚡ readiness en jauge
   d'énergie (le "mana" du perso), 🏅 dernier badge.
4. **Carte "dernière séance"** : type, load, XP gagnée avec détail du multiplicateur.
5. **CTA principal** : « Synchroniser » (ou « Simuler une séance » en démo).

## 4. Écran Héros (character sheet)

Codes Game UI Database :
- Avatar central grand format (sprite 16×16 upscalé, `image-rendering: pixelated`).
- 5 barres de stats **segmentées** (pas de barres lisses : lisibilité RPG),
  valeur numérique à droite, delta hebdo (+2 ▲) en vert néon.
- Emblème de classe + niveau en médaillon.
- Section « Hauts faits » : records perso = trophées pixel.

## 5. Écran Quêtes / Boss

- **Boss du palier** : sprite du boss, nom généré (« Golem des Contreforts »),
  **barre de vie rouge segmentée** qui descend à chaque séance (le load inflige
  les dégâts). Pattern raid : dégâts affichés en nombres flottants.
- Récompense annoncée (XP + badge) — pattern quest log MMO.
- Défis hebdo secondaires (3 max, rotation lundi).

## 6. Pop-up LEVEL UP (pattern succès Duolingo × RPG)

- Overlay plein écran, fond assombri.
- Burst de particules pixel (étoiles), sprite du héros qui "flash".
- `LEVEL UP!` en typographie pixel néon, niveau affiché en compteur animé.
- Gains listés (stats débloquées, nouveau boss révélé).
- Dismiss par tap — jamais de timer forcé.

## 7. Feedback & animations (règles transverses)

- Toute XP gagnée apparaît en **nombre flottant** `+247 XP` (code universel RPG).
- Transitions d'écrans : slide 200 ms ease-out ; jamais > 300 ms.
- Les barres ne "sautent" jamais : toujours un tween (600 ms ease-out).
- Respect de `prefers-reduced-motion` : toutes les animations sont dégradables.
- Dark mode par défaut (Dribbble fitness trend), accents néon : cyan (XP),
  magenta (boss), ambre (streak), vert (récup).
