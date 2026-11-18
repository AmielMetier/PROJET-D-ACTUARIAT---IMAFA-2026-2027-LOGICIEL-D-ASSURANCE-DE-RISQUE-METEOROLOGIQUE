"""
Cache des téléchargements météo : en mémoire, avec une durée de vie limitée.

Les données sont récupérées en temps réel auprès d'Open-Meteo, puis gardées quelques heures :
l'archive n'est de toute façon mise à jour qu'une fois par jour, et les années passées ne changent plus.
Le cache évite de retélécharger 15 à 40 ans de données à chaque clic, accélère les calculs et protège
l'application de la limite de requêtes d'Open-Meteo (le cache est partagé par tous les visiteurs de
l'application en ligne).

Choix volontaires :
- rien n'est écrit sur le disque, donc aucune donnée ne peut rester périmée indéfiniment ;
- une erreur (panne réseau, refus du service) n'est jamais mise en cache : le calcul suivant réessaie ;
- l'heure de récupération est renvoyée avec les données, pour l'afficher dans l'application.
"""

from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from .weather_api import fetch_historical_precipitation

CACHE_TTL_HOURS = 6
PARIS = ZoneInfo("Europe/Paris")


@st.cache_data(ttl=CACHE_TTL_HOURS * 3600, max_entries=200, show_spinner=False)
def fetch_precipitation_cached(latitude: float, longitude: float,
                               start_date: str, end_date: str) -> Tuple[pd.DataFrame, datetime]:
    """Pluie journalière (comme fetch_historical_precipitation) et heure de son téléchargement."""
    df = fetch_historical_precipitation(latitude, longitude, start_date, end_date)
    return df, datetime.now(PARIS)


def fetched_label(fetched_at: datetime) -> str:
    """« Données météo récupérées le 16/11/2026 à 14 h 05 (gardées 6 h en cache). »"""
    return (f"Données météo récupérées le {fetched_at:%d/%m/%Y} à {fetched_at:%H} h {fetched_at:%M} "
            f"(gardées {CACHE_TTL_HOURS} h en cache).")
