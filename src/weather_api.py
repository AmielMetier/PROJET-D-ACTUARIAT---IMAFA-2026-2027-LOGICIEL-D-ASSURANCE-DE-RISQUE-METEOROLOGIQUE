"""
Module de récupération des données météorologiques en temps réel et historiques.
Utilise l'API Open-Meteo (libre d'accès, données mondiales et françaises fiables).
"""

from typing import Dict, Any, Optional, Tuple
import requests
import pandas as pd


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_coordinates(city_name: str) -> Optional[Tuple[float, float, str]]:
    """
    Récupère la latitude, longitude et nom officiel d'une ville via l'API de géocodage.
    """
    try:
        params = {"name": city_name, "count": 1, "language": "fr", "format": "json"}
        response = requests.get(GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            res = data["results"][0]
            label = f"{res.get('name')}, {res.get('admin1', '')} ({res.get('country_code', '')})"
            return float(res["latitude"]), float(res["longitude"]), label
    except Exception as e:
        print(f"Erreur géocodage pour {city_name}: {e}")
    return None


def fetch_historical_precipitation(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Télécharge la série journalière de précipitations (mm) pour une période donnée.
    Format de date: 'YYYY-MM-DD'.
    Retourne un DataFrame avec colonnes ['date', 'precipitation'].
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum",
        "timezone": "auto"
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    daily = data.get("daily", {})
    df = pd.DataFrame({
        "date": pd.to_datetime(daily.get("time", [])),
        "precipitation": daily.get("precipitation_sum", [])
    })
    df["precipitation"] = df["precipitation"].fillna(0.0)
    return df
