"""
Module de récupération des données météorologiques en temps réel et historiques.
Utilise l'API Open-Meteo (libre d'accès, sans clé).

Les précipitations historiques proviennent de réanalyses (ERA5 / ERA5-Land) : ce sont des valeurs
calculées sur un point de grille d'environ 10 à 25 km, et non les relevés d'une station au sol.
"""

import time
from typing import Optional, Tuple
import requests
import pandas as pd


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Nombre de tentatives en cas de coupure réseau ou d'erreur serveur (5xx)
MAX_ATTEMPTS = 3
# Pays recherché en priorité (les clients sont des commerçants français)
DEFAULT_COUNTRY = "FR"


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


def _search(city_name: str, country_code: Optional[str]) -> list:
    params = {"name": city_name.strip(), "count": 10, "language": "fr", "format": "json"}
    if country_code:
        params["countryCode"] = country_code
    return _get_json(GEOCODING_URL, params, timeout=10).get("results") or []


def get_coordinates(
    city_name: str,
    country_code: Optional[str] = DEFAULT_COUNTRY
) -> Optional[Tuple[float, float, str]]:
    """
    Récupère la latitude, longitude et nom complet d'une ville via l'API de géocodage.

    La recherche se fait d'abord en France, ce qui évite de tomber sur une ville homonyme étrangère
    (ex. « Nice » aux États-Unis) ; à défaut, elle est étendue au monde entier. Parmi les résultats,
    la localité la plus peuplée est retenue (une commune plutôt qu'un lieu-dit du même nom).

    Retourne None si la ville est introuvable ; lève WeatherAPIError si le service est injoignable.
    """
    results = _search(city_name, country_code) if country_code else []
    if not results:
        results = _search(city_name, None)
    if not results:
        return None
    res = max(results, key=lambda r: r.get("population") or 0)
    parts = [res.get("name"), res.get("admin1"), res.get("country")]
    label = ", ".join(p for p in parts if p)
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
