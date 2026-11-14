"""
Correction du biais de la réanalyse Open-Meteo par quantiles (« quantile mapping »).

La réanalyse ERA5 compte trop de jours de bruine et lisse les épisodes intenses (voir le guide,
section 5). Pour une ville, on compare sur une période commune la distribution des pluies
journalières de la réanalyse à celle de la station au sol la plus proche, puis on remplace chaque
valeur de la réanalyse par la valeur de la station de même rang (même quantile) :

    x_corrigé = F_station^-1( F_réanalyse(x) )

Les petites pluies que la station ne voit pas deviennent 0 mm (jours secs) et les intensités autour
du seuil de perte sont recalées sur la station. Les tables de quantiles sont calculées une fois pour
toutes par scripts/calibrer_correction.py et stockées dans data/calibration_stations.json.
"""

import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

CALIBRATION_FILE = Path(__file__).resolve().parent.parent / "data" / "calibration_stations.json"
# Distance maximale entre le point demandé et le point de grille calé pour réutiliser une calibration
MAX_MATCH_KM = 15.0
# Grille de probabilités : plus fine dans la queue haute, là où se jouent les indemnités
PROBS = np.unique(np.concatenate([np.linspace(0, 0.9, 91), np.linspace(0.9, 0.999, 100), [1.0]]))


def fit_quantile_map(model: np.ndarray, observed: np.ndarray) -> Dict[str, list]:
    """Quantiles de la réanalyse et de la station sur la même grille de probabilités."""
    return {
        "probs": PROBS.round(4).tolist(),
        "q_model": np.quantile(np.asarray(model, float), PROBS).round(2).tolist(),
        "q_obs": np.quantile(np.asarray(observed, float), PROBS).round(2).tolist(),
    }


def apply_quantile_map(values, qmap: Dict[str, list]) -> np.ndarray:
    """
    Applique la correction à une série de pluies journalières (mm).
    Au-delà du plus fort quantile calé, la correction est prolongée par le rapport des maxima.
    """
    x = np.asarray(values, float)
    qm = np.asarray(qmap["q_model"], float)
    qo = np.asarray(qmap["q_obs"], float)
    probs = np.asarray(qmap["probs"], float)

    # Rang de chaque valeur dans la distribution de la réanalyse. Pour les paliers (en particulier
    # les nombreux 0 mm), on retient le haut du palier.
    levels, inverse = np.unique(qm, return_inverse=True)
    top = np.zeros(len(levels))
    np.maximum.at(top, inverse, probs)
    rank = np.interp(x, levels, top, left=0.0, right=1.0)
    corrected = np.interp(rank, probs, qo)

    # Extrapolation au-delà du maximum calé
    above = x > qm[-1]
    if above.any() and qm[-1] > 0:
        corrected[above] = x[above] * (qo[-1] / qm[-1])
    corrected[x <= 0] = 0.0
    return np.maximum(corrected, 0.0)


@lru_cache(maxsize=1)
def load_calibrations() -> Dict[str, Any]:
    if not CALIBRATION_FILE.exists():
        return {}
    return json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))


def _normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", name.strip().lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _distance_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_calibration(city: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Calibration disponible pour cette ville : par son nom, sinon par la proximité du point de grille
    (moins de 15 km d'un point déjà calé). None si aucune station n'a servi au calage près de là.
    """
    calibrations = load_calibrations()
    by_name = calibrations.get(_normalize(city))
    if by_name:
        return by_name
    if lat is None or lon is None:
        return None
    best = min(calibrations.values(), key=lambda c: _distance_km(lat, lon, c["grid_lat"], c["grid_lon"]), default=None)
    if best and _distance_km(lat, lon, best["grid_lat"], best["grid_lon"]) <= MAX_MATCH_KM:
        return best
    return None


def correct_dataframe(df: pd.DataFrame, calibration: Optional[Dict[str, Any]]) -> pd.DataFrame:
    """Copie du DataFrame ['date', 'precipitation', ...] avec la pluie corrigée (inchangé sans calibration)."""
    if not calibration:
        return df
    out = df.copy()
    out["precipitation"] = apply_quantile_map(out["precipitation"].to_numpy(), calibration["qmap"])
    return out
