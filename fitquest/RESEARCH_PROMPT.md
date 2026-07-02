# Prompt de recherche scientifique — fondations sportives de FitQuest

> Prompt à donner à un agent de recherche approfondie (deep research) pour auditer
> les mécaniques d'entraînement de l'app contre la littérature scientifique.
> Le résultat alimentera une révision sourcée de `server/game/engine.py`.

---

# Mission de recherche : fondations scientifiques d'une app de course à pied gamifiée

## Contexte

Je développe **FitQuest**, une application qui transforme l'entraînement de course à pied
en RPG : les séances rapportent de l'expérience (XP), font monter de niveau et débloquent
des défis ("boss"). Les mécaniques de jeu sont actuellement basées sur l'intuition.
**Ta mission : les auditer contre la littérature scientifique** pour que chaque mécanique
qui influence le comportement d'entraînement repose sur des preuves, pas sur du game design.

Mécaniques actuelles à auditer (source de données : montres Garmin — Training Load,
Training Effect, Training Readiness, HRV, VO2max estimée, sommeil) :
1. **XP = Training Load × 1.5 (si activité de spécialité) × bonus de régularité
   (jusqu'à +35% à 7 jours consécutifs) × plafond de fatigue** (×0.3 si readiness < 25,
   ×0.7 si < 50) + 200 XP par record personnel battu.
2. **Boss** : objectif-défi calibré à ~115% de la charge hebdomadaire moyenne des
   4 dernières semaines.
3. **Streak** : bonus de jours consécutifs d'activité (plafonné à 7 jours).
4. **Stat "Vitalité"** dérivée de HRV + sommeil + readiness, qui récompense le repos.

## Questions de recherche (traite chacune séparément)

### A. Quantification de la charge d'entraînement
1. Quelles méthodes de quantification de charge sont validées : TRIMP (Banister, Edwards,
   Lucia), sRPE (Foster), TSS, charge aiguë/chronique ? Fiabilité comparée ?
2. Le **ratio charge aiguë:chronique (ACWR)** : état actuel du débat scientifique
   (Gabbett vs critiques méthodologiques d'Impellizzeri et al.). Existe-t-il une "zone
   optimale" (0.8–1.3) défendable pour calibrer une progression hebdomadaire ?
3. La "règle des 10%" de progression hebdomadaire : mythe ou preuve ? (cf. essais sur
   coureurs novices, Buist et al.)
4. Les métriques propriétaires Garmin/Firstbeat (Training Load, Training Effect,
   Training Readiness) : quelles validations indépendantes publiées existent ?
   Limites connues ?

### B. Méthodes d'entraînement efficaces en course à pied
5. **Distribution d'intensité** : preuves comparées entraînement polarisé vs pyramidal
   vs seuil (Seiler, Stöggl & Sperlich, Casado et al.) — pour débutants ET confirmés.
   Le "80/20" est-il applicable à un coureur amateur à 3 séances/semaine ?
6. Déterminants physiologiques de la performance (VO2max, économie de course, seuil
   lactique/vitesse critique) : lesquels sont les plus entraînables, avec quels types
   de séances, et quels effets dose-réponse chiffrés (méta-analyses) ?
7. Intervalles à haute intensité vs volume continu à basse intensité : tailles d'effet,
   populations étudiées, risques.
8. Renforcement musculaire et pliométrie pour coureurs : effets sur économie de course
   et prévention des blessures (méta-analyses récentes).

### C. Récupération, surentraînement et blessure
9. **HRV comme outil de pilotage** : les protocoles d'entraînement guidé par HRV
   (Kiviniemi, Javaloyes, Vesterinen) font-ils mieux que les plans fixes ? Conditions
   de validité de la mesure (moment, position, moyennes 7 jours vs valeur du jour) ?
10. Sommeil et performance/blessure chez l'athlète : ampleur des effets documentés.
11. Facteurs de risque de blessure en course à pied validés par cohortes prospectives
    (charge, progression, historique de blessure, cadence...) : lesquels une app
    peut-elle réellement surveiller ?
12. **Jours de repos** : que dit la littérature sur la fréquence minimale de repos ?
    Un bonus de "streak" quotidien est-il défendable ou faut-il récompenser un
    pattern hebdomadaire (ex. 3-5 jours actifs + repos) ?

### D. Science comportementale de l'exercice
13. Gamification et activité physique : que disent les méta-analyses (efficacité
    réelle, durabilité de l'effet, risque d'éviction de la motivation intrinsèque —
    théorie de l'autodétermination, Deci & Ryan appliquée au fitness) ?
14. Streaks, badges, niveaux : preuves spécifiques sur l'adhérence à long terme et
    effets pervers documentés (exercice compulsif, culpabilité, abandon après rupture
    de streak).
15. Fixation d'objectifs : objectifs de processus vs de résultat, objectifs calibrés
    individuellement — qu'est-ce qui maximise l'adhérence chez le sportif amateur ?

## Contraintes méthodologiques — IMPORTANT
- **Hiérarchise les preuves** : méta-analyses/revues systématiques > RCT > cohortes >
  études transversales > opinions d'experts. Indique le niveau de preuve pour chaque
  affirmation.
- **Cite précisément** : auteur, année, journal, DOI. Pas d'affirmation sans source.
- **Rapporte les tailles d'effet** et les populations étudiées (élites vs amateurs vs
  novices — la transférabilité compte : mes utilisateurs sont des amateurs).
- **Signale les controverses** : quand la littérature est contradictoire ou faible
  (ex. ACWR), dis-le explicitement au lieu de trancher artificiellement.
- **Distingue** ce qui est validé, ce qui est plausible mais non prouvé, et ce qui est
  contredit par les données.

## Livrable attendu
1. **Synthèse par question** (A1→D15) avec niveau de preuve et références.
2. **Tableau d'audit** : chaque mécanique actuelle de l'app (1-4 ci-dessus) →
   verdict (validée / à modifier / contredite) → correction proposée sourcée.
3. **Formules opérationnelles recommandées** : comment calculer la charge, calibrer
   la progression hebdomadaire, définir les seuils de repos, et structurer les défis
   pour un coureur amateur — chaque paramètre justifié par une référence.
4. **Liste des risques** : les mécaniques de gamification à proscrire au regard de la
   littérature (avec sources).
