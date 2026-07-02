# ⚔️ FitQuest

**Ton corps est ton personnage.** RPG pixel-art fantasy par-dessus les données
Garmin Connect : chaque séance de sport rapporte de l'XP, fait monter de niveau
et inflige des dégâts au boss du palier.

| Docs | Contenu |
|------|---------|
| [`GAME_DESIGN.md`](GAME_DESIGN.md) | règles du jeu : classes, formule d'XP, niveaux, boss, feuille de perso |
| [`UX_FLOWS.md`](UX_FLOWS.md) | écrans & parcours (patterns Duolingo / NRC / Strava / Game UI Database) |
| [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) | design system « Néon Grimoire » : tokens, composants, animations |

## Lancer l'app

```bash
# 1. Backend deps
pip install -r server/requirements.txt

# 2. Build du frontend (une fois)
cd webapp && npm install && npm run build && cd ..

# 3. Tout-en-un : FastAPI sert l'API + la webapp buildée
cd server && uvicorn main:app --port 8000
# → http://localhost:8000
```

Mode dev frontend avec hot-reload : `cd webapp && npm run dev` (proxy `/api`
vers `:8000`).

## Modes de données

- **Démo** (défaut) : historique simulé de 4 semaines, aucun compte requis.
  Le CTA « Simuler une séance » alimente la boucle de jeu.
- **Garmin réel** : utilise la lib `garminconnect` de ce repo. Générer d'abord
  les tokens avec `example.py` (racine du repo), puis choisir « Connecter
  Garmin » à l'onboarding.

## Tests

```bash
cd server && python -m pytest tests/        # règles du moteur (15 tests)
cd webapp && node e2e.mjs                   # parcours complet navigateur
# (e2e.mjs nécessite le serveur lancé sur :8000 et un profil vierge :
#  curl -X POST localhost:8000/api/reset)
```

## Architecture

```
fitquest/
├── server/            FastAPI
│   ├── main.py        API (onboarding, state, sync) + sert webapp/dist
│   └── game/
│       ├── engine.py          moteur : XP, niveaux, classes, reco, stats, boss
│       ├── demo_data.py       provider démo (historique simulé)
│       ├── garmin_provider.py provider réel (lib garminconnect)
│       └── state.py           persistance JSON (MVP mono-joueur)
└── webapp/            React + Vite, pixel art « Néon Grimoire »
    └── src/
        ├── screens/   Onboarding S0→S5, Taverne, Héros, Quêtes, Journal
        ├── sprites.jsx     sprites 16×16 (5 classes + boss) en SVG
        └── components.jsx  XPBar segmentée, LevelUpModal, FloatingXP…
```
