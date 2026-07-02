# FitQuest — Game Design Document

> RPG de fitness par-dessus les données Garmin Connect : **faire du sport = jouer**.
> Esthétique : **pixel art fantasy, dark mode, néons**. Boucle validée : solo XP + niveaux,
> effort relatif, guildes mixtes en phase 2.

---

## 1. Pilier central : l'effort relatif

L'XP n'est **jamais** basée sur la performance brute (km, allure absolue).
Elle est basée sur les métriques Garmin **normalisées à l'individu** :
Training Load, Training Effect, Training Readiness, Body Battery.

Conséquences de design :

- Un débutant et un athlète gagnent autant d'XP pour un effort équivalent *pour eux*.
- Le repos fait partie du jeu (la Vitalité récompense la récupération).
- Le surentraînement est **puni par la mécanique** (plafond d'XP par readiness),
  pas par un pop-up moralisateur.

## 2. Les classes

Choisies à la première connexion, **recommandées d'après l'historique Garmin**
(analyse des 4 dernières semaines). Respec possible 1×/saison.

| Classe | Archétype | XP favorisée | Signaux Garmin |
|--------|-----------|--------------|----------------|
| **Rôdeur** | Endurance — le marathonien infatigable | Volume aérobie, longues sorties, zones basses tenues | Endurance Score, temps Z2-Z3, distance hebdo |
| **Assassin** | Sprint — explosif, létal sur la courte | Intervalles, pics d'intensité, puissance max | VO2max, Anaerobic TE, vitesse max |
| **Guerrier** | Force — le tank | Musculation, charge, reps | Strength activities, muscle load |
| **Paladin** | Grimpeur — dompteur de montagnes | Dénivelé, côtes | Hill Score, total ascent, étages |
| **Voyageur** | Explorateur — le nomade | Variété d'activités, nouveaux lieux | Types d'activités uniques, GPS |

**Règle clé** : la classe accélère l'XP dans son domaine (×1.5) mais l'XP hors-classe
reste à ×1.0 — le cross-training n'est jamais puni.

## 3. Le moteur d'XP

Pour chaque activité synchronisée :

```
xpBrute   = activityTrainingLoad            # charge physiologique Garmin
mClasse   = activité colle à la classe ? 1.5 : 1.0
mStreak   = 1 + min(streakJours, 7) × 0.05  # jusqu'à +35 % à 7 jours
bonusPR   = nouveau record perso ? +200 XP flat : 0
plafond   = readiness < 25 ? 0.3            # rouge → XP quasi coupée
          : readiness < 50 ? 0.7
          : 1.0

XP = round(xpBrute × mClasse × mStreak × plafond) + bonusPR
```

Mécaniques qui sauvent le design :

- **Bonus PR perso** : le débutant bat ses records en permanence → flot d'XP au début.
- **Plafond readiness** : impossible de "farmer" en se détruisant.

## 4. Courbe de niveaux

```
XP_pour_passer_du_niveau_n_au_niveau_n+1 = 100 × n^1.5
```

| Niveau | XP cumulée | Rythme réel (~900 XP/sem. active) |
|--------|-----------|------------------------------------|
| 2 | 100 | 1ʳᵉ séance |
| 5 | ~1 700 | ~2 semaines (ou immédiat avec le backfill d'historique) |
| 10 | ~11 100 | ~1 saison |
| 25 | ~119 000 | année 1 bien remplie |
| 50 | ~690 000 | légende du long cours |

À l'onboarding, l'historique analysé est **backfillé en XP** (« ton passé
compte ») : un joueur actif démarre déjà niveau 4-6 — le hook des premiers
niveaux sans tricher sur la courbe. Prestige au-delà du soft-cap saisonnier.

## 5. Feuille de personnage

5 attributs sur 0–100, recalculés chaque nuit à partir des vraies données —
**ton perso est ton corps** :

| Stat | Source Garmin (lib `garminconnect`) |
|------|--------------------------------------|
| STAMINA | `get_endurance_score` + volume aérobie 4 sem |
| FORCE | charge muscu + effet anaérobie |
| AGILITÉ | `get_max_metrics` (VO2max) + PRs d'allure |
| VITALITÉ | `get_hrv_data` + `get_sleep_data` + `get_training_readiness` |
| DISCIPLINE | streak + régularité hebdo |

**VITALITÉ** est la mécanique anti-surentraînement : elle monte quand on récupère
bien et conditionne la puissance en combat de boss.

## 6. La boucle quotidienne

```
Sport → sync Garmin → pull activités → calcul XP
  → animation de gain (+ éventuel LEVEL UP!)
  → la nuit : recalcul feuille de perso + readiness (jauge d'énergie)
  → au réveil : « Vitalité 82/100, prêt à en découdre »
```

## 7. Les boss (phase 2)

Un boss = défi **calibré sur les stats actuelles du joueur** (stretch atteignable,
jamais absolu), avec une **barre de vie** entamée sur plusieurs séances (raid)
ou en un gros run (fight final).

- Boss Rôdeur : « tiens la Z3 pendant 45 min » / « +10 % vs ta plus longue sortie du mois »
- Boss Assassin : « nouveau PR sur 1 km » / « X watts pendant 30 s »
- **World boss** (guilde) : barre de vie collective = somme des loads de la guilde
  sur la semaine — le moment MMO.

## 8. Guildes (phase 2)

**Party mixte** avec bonus de diversité : une guilde couvrant plusieurs classes est
plus forte → pousse à recruter des profils variés (tank/heal/DPS d'un raid MMO).

## 9. Saisons (phase 3)

Saisons de ~3 mois (ladder/battle pass) avec reset partiel : les stats "corps"
persistent, le classement compétitif reset. Personne n'est distancé pour toujours.

---

## 10. Périmètre MVP (ce que livre l'app actuelle)

- ✅ Onboarding : connexion (mode démo ou Garmin réel), analyse d'historique,
  recommandation de classe, choix confirmé.
- ✅ Moteur XP complet (formule ci-dessus) + niveaux.
- ✅ Feuille de personnage 5 stats.
- ✅ Dashboard : XP bar animée, streak, readiness, feed d'activités avec détail du calcul.
- ✅ Boss de palier (barre de vie calibrée, coup critique ×1.2 sur activité de classe).
- ✅ Popup LEVEL UP animée.
- ✅ **Phase 2 (livrée)** — Défis hebdo : 3 quêtes à rotation le lundi, dont une
  taillée pour la classe, récompensées à la sync. Guilde « party mixte » avec
  bonus de diversité (+5 %/classe distincte, cap +20 %) et **world boss** à
  barre de vie collective ; en mode démo la party est simulée par des
  compagnons PNJ qui infligent leurs dégâts quotidiens — les formes de données
  sont le contrat du vrai multijoueur.
- 🔜 Multijoueur réel (guildes persistantes), saisons, respec de classe.
