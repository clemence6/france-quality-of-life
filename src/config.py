"""
Configuration centrale du projet : chemins, variables d'environnement.

⚠️ Aucune clé API ne doit être écrite en dur ici — tout passe par .env
(voir .env.example à la racine du projet).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Chemins ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# --- Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# --- Clés API tierces ---
# OpenAQ v3 : OBLIGATOIRE pour src/extract/atmo.py. Clé gratuite sur
# https://explore.openaq.org/register — ne jamais la mettre en dur ici.
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")

# Geod'Air (Atmo France officiel) : optionnelle, selon la région.
ATMO_API_KEY = os.getenv("ATMO_API_KEY", "")

# INSEE : non utilisée par le pipeline principal actuellement (voir
# extras/insee_local_analysis/ pour l'enrichissement population/revenus).
INSEE_API_KEY = os.getenv("INSEE_API_KEY", "")

REQUEST_TIMEOUT = 15  # secondes, pour les appels API
