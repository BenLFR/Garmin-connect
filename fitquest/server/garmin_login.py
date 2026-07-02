#!/usr/bin/env python3
"""FitQuest — connexion Garmin clé-en-main.

Crée les tokens OAuth (valables ~1 an) puis vérifie que les données réelles
couvrent tout ce dont le moteur v2 a besoin. À lancer UNE fois :

    cd fitquest/server
    python garmin_login.py

Identifiants : demandés interactivement, ou via les variables d'environnement
GARMIN_EMAIL / GARMIN_PASSWORD. Le code MFA est demandé si le compte l'exige.
Les tokens vont dans $GARMINTOKENS (défaut ~/.garminconnect) — aucun mot de
passe n'est stocké.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

TOKENSTORE = os.getenv("GARMINTOKENS", "~/.garminconnect")

# Champs consommés par le moteur v2 (engine.py / garmin_provider.py)
REQUIRED_ACTIVITY_FIELDS = [
    "activityId", "activityType", "startTimeLocal", "duration",
]
OPTIONAL_ACTIVITY_FIELDS = [
    "activityTrainingLoad",   # dégâts de boss (plafonnés anti-spike)
    "aerobicTrainingEffect",  # classification intensité (budget TID)
    "anaerobicTrainingEffect",
    "elevationGain",          # affinité Paladin
    "activityName",
]


def login():
    from garminconnect import Garmin

    store = Path(TOKENSTORE).expanduser()
    if store.exists():
        print(f"→ Tokens trouvés dans {store}, tentative de reprise…")
        try:
            api = Garmin()
            api.login(TOKENSTORE)
            print(f"✓ Connecté en tant que : {api.full_name}")
            return api
        except Exception as exc:
            print(f"  Tokens expirés/invalides ({exc}), reconnexion complète.")

    email = os.getenv("GARMIN_EMAIL") or input("Email Garmin : ").strip()
    password = os.getenv("GARMIN_PASSWORD") or getpass("Mot de passe Garmin : ")

    api = Garmin(
        email=email, password=password, is_cn=False,
        prompt_mfa=lambda: input("Code MFA reçu (email/SMS/app) : ").strip(),
    )
    api.login()
    api.garth.dump(TOKENSTORE)
    print(f"✓ Connecté en tant que : {api.full_name}")
    print(f"✓ Tokens sauvegardés dans {Path(TOKENSTORE).expanduser()} (valables ~1 an)")
    return api


def field_coverage_report(api) -> bool:
    """Pull 4 weeks of real activities and check the engine's field needs."""
    end = date.today()
    start = end - timedelta(weeks=4)
    print(f"\n→ Lecture des activités du {start} au {end}…")
    acts = api.get_activities_by_date(start.isoformat(), end.isoformat())
    print(f"✓ {len(acts)} activités trouvées")
    if not acts:
        print("  (Aucune activité sur 4 semaines : l'onboarding recommandera "
              "Voyageur — c'est prévu.)")
        return True

    ok = True
    print("\nCouverture des champs requis par le moteur :")
    for field in REQUIRED_ACTIVITY_FIELDS:
        present = sum(1 for a in acts if a.get(field) is not None)
        flag = "✓" if present == len(acts) else "✗"
        if present < len(acts):
            ok = False
        print(f"  {flag} {field:<28} {present}/{len(acts)}")
    print("Champs optionnels (dégradation gracieuse si absents) :")
    for field in OPTIONAL_ACTIVITY_FIELDS:
        present = sum(1 for a in acts if a.get(field) is not None)
        flag = "✓" if present else "·"
        print(f"  {flag} {field:<28} {present}/{len(acts)}")

    sample = acts[0]
    print(f"\nDernière activité : {sample.get('activityName')} — "
          f"type {((sample.get('activityType') or {}).get('typeKey'))}, "
          f"{round((sample.get('duration') or 0) / 60)} min, "
          f"load {sample.get('activityTrainingLoad')}")

    print("\n→ Test des données bien-être (Vitalité)…")
    today = end.isoformat()
    for name, fn in [("training_readiness", api.get_training_readiness),
                     ("sleep_data", api.get_sleep_data),
                     ("hrv_data", api.get_hrv_data)]:
        try:
            data = fn(today)
            print(f"  ✓ {name}: {'ok' if data else 'vide (pas bloquant)'}")
        except Exception as exc:
            print(f"  · {name}: indisponible ({type(exc).__name__}) — "
                  "le provider a des valeurs de repli")
    return ok


if __name__ == "__main__":
    try:
        api = login()
    except Exception as exc:
        print(f"\n✗ Échec de connexion : {exc}")
        print("  Vérifie tes identifiants ; si le réseau passe par un proxy "
              "d'entreprise, sso.garmin.com et connectapi.garmin.com doivent "
              "être autorisés.")
        sys.exit(1)
    ok = field_coverage_report(api)
    print("\n" + ("✓ Tout est prêt : lance l'app (uvicorn main:app --port 8000) "
                  "et choisis « Connecter Garmin » à l'onboarding."
                  if ok else
                  "⚠ Champs requis manquants — envoie ce rapport pour ajuster "
                  "le mapping du provider."))
