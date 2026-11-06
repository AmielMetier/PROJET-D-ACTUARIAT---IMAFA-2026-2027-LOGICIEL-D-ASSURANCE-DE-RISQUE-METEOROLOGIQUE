"""Module de récupération des données météorologiques historiques et temps réel.
Utilise l'API Open-Meteo (open-source, sans clé API requise) avec cache local.
Conforme aux exigences "Real time" et climatologie (Infoclimat / NOAA / NCEI).
"""

import json
import os
import urllib.request
import urllib.parse
from typing import Dict, Tuple
import pandas as pd


# Coordonnées des principales villes françaises pour un accès direct hors-ligne
COORDONNEES_DEFAUT = {
    "nice": (43.7031, 7.2661),
    "cannes": (43.5528, 7.0174),
    "antibes": (43.5804, 7.1251),
    "marseille": (43.2965, 5.3698),
    "paris": (48.8566, 2.3522),
    "lyon": (45.7640, 4.8357),
    "toulouse": (43.6047, 1.4442),
    "bordeaux": (44.8378, -0.5792),
    "lille": (50.6292, 3.0573),
    "strasbourg": (48.5734, 7.7521),
    "nantes": (47.2184, -1.5536),
    "montpellier": (43.6108, 3.8767),
    "toulon": (43.1242, 5.9280),
}


def obtenir_coordonnees_ville(ville: str) -> Tuple[float, float]:
    """Résout le nom d'une ville en latitude et longitude via l'API Geocoding d'Open-Meteo
    avec fallback sur le dictionnaire local.
    """
    cle = ville.strip().lower()
    if cle in COORDONNEES_DEFAUT:
        return COORDONNEES_DEFAUT[cle]

    try:
        url = (
            f"https://geocoding-api.open-meteo.com/v1/search?"
            f"name={urllib.parse.quote(ville)}&count=1&language=fr"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "ProjetActuariatIMAFA/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if "results" in data and len(data["results"]) > 0:
                res = data["results"][0]
                return float(res["latitude"]), float(res["longitude"])
    except Exception:
        pass

    # Défaut Nice si introuvable
    return COORDONNEES_DEFAUT["nice"]


def recuperer_pluviometrie_annuelle(
    ville: str,
    annee: int,
    cache_dir: str = "data",
    forcer_mise_a_jour: bool = False
) -> pd.Series:
    """Récupère la série journalière des précipitations (en mm) pour une année donnée.
    Cherche d'abord dans le cache local (fichier CSV), sinon interroge l'API Open-Meteo Historical.
    """
    os.makedirs(cache_dir, exist_ok=True)
    ville_clean = ville.strip().lower().replace(" ", "_")
    fichier_cache = os.path.join(cache_dir, f"{ville_clean}_{annee}_rain.csv")

    if not forcer_mise_a_jour and os.path.exists(fichier_cache):
        df = pd.read_csv(fichier_cache, parse_dates=["date"], index_col="date")
        return df["precipitation_sum"]

    lat, lon = obtenir_coordonnees_ville(ville)
    start_date = f"{annee}-01-01"
    end_date = f"{annee}-12-31"

    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat:.4f}&longitude={lon:.4f}&"
        f"start_date={start_date}&end_date={end_date}&"
        f"daily=precipitation_sum&timezone=auto"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ProjetActuariatIMAFA/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            daily = data.get("daily", {})
            dates = pd.to_datetime(daily.get("time", []))
            rain = daily.get("precipitation_sum", [])
            s = pd.Series(rain, index=dates, name="precipitation_sum", dtype=float)
            s = s.fillna(0.0)

            # Sauvegarde en cache
            s.to_frame(name="precipitation_sum").to_csv(fichier_cache, index_label="date")
            return s
    except Exception as e:
        # Si échec réseau et aucun cache, lever une erreur explicative
        if os.path.exists(fichier_cache):
            df = pd.read_csv(fichier_cache, parse_dates=["date"], index_col="date")
            return df["precipitation_sum"]
        raise RuntimeError(
            f"Impossible de récupérer les données météo pour {ville} ({annee}) : {e}"
        )


def recuperer_historique_pluviometrie(
    ville: str,
    annee_debut: int,
    annee_fin: int,
    cache_dir: str = "data"
) -> Dict[int, pd.Series]:
    """Récupère l'historique annuel de pluviométrie sur une plage d'années [annee_debut, annee_fin]."""
    historique = {}
    for annee in range(annee_debut, annee_fin + 1):
        try:
            historique[annee] = recuperer_pluviometrie_annuelle(ville, annee, cache_dir=cache_dir)
        except Exception as e:
            print(f"Avertissement : échec pour l'année {annee} ({e})")
    return historique


def recuperer_previsions_temps_reel(ville: str) -> pd.DataFrame:
    """Récupère les prévisions météorologiques temps réel à 7-14 jours pour la ville choisie."""
    lat, lon = obtenir_coordonnees_ville(ville)
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat:.4f}&longitude={lon:.4f}&"
        f"daily=precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min&"
        f"timezone=auto"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "ProjetActuariatIMAFA/1.0"})
    with urllib.request.urlopen(req, timeout=8) as response:
        data = json.loads(response.read().decode("utf-8"))
        daily = data.get("daily", {})
        df = pd.DataFrame(daily)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        return df
