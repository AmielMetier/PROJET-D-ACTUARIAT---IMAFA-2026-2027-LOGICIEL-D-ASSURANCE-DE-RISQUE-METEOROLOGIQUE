"""
Module de récupération des données météorologiques en temps réel et historiques.
Utilise l'API Open-Meteo (libre d'accès, données mondiales et françaises fiables).
"""

import time
from typing import Optional, Tuple
import requests
import pandas as pd


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Nombre de tentatives en cas de coupure réseau ou d'erreur serveur (5xx)
MAX_ATTEMPTS = 3


class WeatherAPIError(Exception):
    """Erreur lisible levée quand le service météo est injoignable ou refuse la requête."""


def _get_json(url: str, params: dict, timeout: int) -> dict:
    """
    Requête GET avec nouvelles tentatives sur les erreurs passagères.
    Lève WeatherAPIError avec un message compréhensible par l'utilisateur.
    """
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as e:
            last_error = f"service météo injoignable ({type(e).__name__})"
        else:
            if response.status_code < 400:
                return response.json()
            if response.status_code < 500:
                # Requête refusée : inutile de réessayer
                try:
                    reason = response.json().get("reason", "")
                except ValueError:
                    reason = ""
                raise WeatherAPIError(
                    f"Le service météo a refusé la requête (code {response.status_code}). {reason}".strip()
                )
            last_error = f"le service météo est en erreur (code {response.status_code})"
        if attempt < MAX_ATTEMPTS:
            time.sleep(attempt)
    raise WeatherAPIError(
        f"Impossible de récupérer les données météo après {MAX_ATTEMPTS} tentatives : {last_error}. "
        "Vérifiez la connexion Internet puis réessayez."
    )


def get_coordinates(city_name: str) -> Optional[Tuple[float, float, str]]:
    """
    Récupère la latitude, longitude et nom officiel d'une ville via l'API de géocodage.
    Retourne None si la ville est introuvable ; lève WeatherAPIError si le service est injoignable.
    """
    params = {"name": city_name, "count": 1, "language": "fr", "format": "json"}
    data = _get_json(GEOCODING_URL, params, timeout=10)
    results = data.get("results") or []
    if not results:
        return None
    res = results[0]
    label = f"{res.get('name')}, {res.get('admin1', '')} ({res.get('country_code', '')})"
    return float(res["latitude"]), float(res["longitude"]), label


def fetch_historical_precipitation(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Télécharge la série journalière de précipitations (mm) pour une période donnée.
    Format de date: 'YYYY-MM-DD'.
    Retourne un DataFrame avec colonnes ['date', 'precipitation', 'missing'] :
    les jours sans donnée sont marqués missing=True et comptés à 0 mm.
    Lève WeatherAPIError si le service est injoignable.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum",
        "timezone": "auto"
    }
    data = _get_json(ARCHIVE_URL, params, timeout=30)

    daily = data.get("daily", {})
    df = pd.DataFrame({
        "date": pd.to_datetime(daily.get("time", [])),
        "precipitation": pd.to_numeric(pd.Series(daily.get("precipitation_sum", []), dtype="object"), errors="coerce"),
    })
    df["missing"] = df["precipitation"].isna()
    df["precipitation"] = df["precipitation"].fillna(0.0).astype(float)
    return df
