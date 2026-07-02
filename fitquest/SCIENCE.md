# FitQuest — Fondations scientifiques (v2 du moteur)

Synthèse opérationnelle de l'audit scientifique complet
([`docs/AUDIT_SCIENTIFIQUE.md`](docs/AUDIT_SCIENTIFIQUE.md)) et de son
application dans le code. **Règle du projet : toute mécanique qui influence le
comportement d'entraînement doit citer sa source.** Si un test de
`tests/test_engine.py` échoue, c'est le code *ou* cette page qu'il faut
ré-examiner — jamais supprimer le test.

## Verdicts de l'audit et application

| Mécanique v1 | Verdict | Application v2 (code) |
|--------------|---------|----------------------|
| XP = Training Load brut + bonus PR | ⚠️ À modifier — récompenser le load brut incite au surentraînement ; les objectifs de **processus** surpassent les objectifs de résultat (d = 1.36 vs 0.09, méta-analyse) | XP **par minute d'activité** (`XP_PER_MINUTE`), identique en Z1 et Z3. Records = trophée, **zéro XP** (`xp_for_activity`) |
| Boss à 115 % de la semaine type | ❌ Contredite — « Single-Session Spike » : une séance dépassant de 10-30 % la plus longue du mois ↑ le risque de blessure de 52-64 % (Frandsen et al., BJSM 2025, n = 5 200). L'ACWR comme prédicteur est invalidé (Impellizzeri et al.) | Boss HP = **100 %** d'une semaine type ; **dégâts par séance plafonnés à 110 % du pic des 30 derniers jours** (`anti_spike_cap`, `damage_boss`) — l'héroïsme ne paie pas, la constance oui |
| Streak quotidien (bonus 7 j consécutifs) | ❌ Contredite — remodelage tendineux/osseux exige 1-2 jours off/sem. ; la rupture d'un streak déclenche l'Abstinence Violation Effect → abandon (Marlatt & Gordon) | **Streak hebdomadaire** : une semaine réussie = **3-5 jours actifs** (7/7 = échec), cap ×1.2 à 4 semaines (`is_successful_week`, `week_streak_multiplier`). **Le repos rapporte de l'XP** (`recovery_xp_for_rest_day`) |
| Vitalité (HRV + sommeil + readiness) | ✅ Validée — l'entraînement guidé par HRV bat les plans fixes (Manresa-Rocamora 2021, méta-analyse) ; < 8 h de sommeil ≈ risque de blessure ×1.7 (Milewski 2014) | Conservée, méthodo **SWC** : moyenne glissante LnRMSSD 7 j vs baseline 60 j ± 0.5 SD (`vitality_swc`), sommeil court pénalise la readiness (`readiness_from_swc`) |

## Garde-fous supplémentaires issus de l'audit

- **Budget d'intensité (§B5, B7)** : les modèles pyramidal/polarisé battent le
  "tout seuil" (Casado 2022) et la dose de HIIT doit rester ≈ 20 % du volume.
  → au-delà de 20 % de minutes intenses dans la semaine, l'XP des séances
  intenses est décotée ×0.6 (`tid_factor`). Une séance facile n'est **jamais**
  décotée.
- **Métriques Garmin/Firstbeat (§A4)** : proxys corrects de la charge
  métabolique, mais **aveugles à la charge biomécanique** (impacts, tendons).
  D'où le plafond anti-spike basé sur le volume de séance, pas sur l'EPOC.
- **Règle des 10 % (§A3)** : invalidée (GRONORUN, Buist et al. — 20.8 % vs
  20.3 % de blessures). On ne l'utilise nulle part.

## Mécaniques proscrites (registre des risques, §G)

1. **Streak punitif** (perte de statut après 24-48 h off) → AVE, exercice
   compulsif. Notre streak est hebdomadaire et le repos est récompensé.
2. **Récompense du volume brut** → grinding métabolique, sabotage de la
   distribution d'intensité. Notre XP est au temps, pas au load.
3. **Leaderboards de Training Load** → comparaison sociale anxiogène,
   imitation de charges hors de son plafond biomécanique. Les futurs
   classements de guilde seront des classements de **constance** (processus),
   jamais de charge absolue.

## Backlog scientifique

- [ ] Brancher la vraie série HRV Garmin (`get_hrv_data`) sur `vitality_swc`
  (le provider réel utilise la readiness constructeur en attendant).
- [ ] Séances prescrites (plan pyramidal → polarisé pré-objectif, §B5) avec
  XP d'adhérence à la zone prescrite — l'étape suivante du "process XP".
- [ ] Questionnaire blessures à l'onboarding (antécédent = OR ~1.6-1.9, §C11)
  pour moduler le plafond anti-spike.
- [ ] 1-2 séances de force/pliométrie hebdo à valoriser (Lauersen : RR 0.315
  sur les blessures ; Llanos-Lagos 2024 : économie de course ES ~0.3-0.47) —
  quête récurrente dédiée.
