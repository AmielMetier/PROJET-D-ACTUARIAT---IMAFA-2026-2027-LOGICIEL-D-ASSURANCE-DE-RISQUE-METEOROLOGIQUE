"""
Calcule la correction de biais (quantile mapping) pour les villes du menu déroulant.

Pour chaque ville :
1. point de grille Open-Meteo de la ville (comme dans l'application) ;
2. station GHCN-Daily (NCEI) la plus proche, à moins de 30 km, avec des relevés de pluie
   complets à au moins 90 % sur 2001-2025 ;
3. table de quantiles réanalyse / station sur 2001-2025, stockée dans data/calibration_stations.json ;
4. validation hors échantillon : correction calée sur 2001-2013 seulement, puis comparaison des
   indemnités annuelles moyennes sur 2014-2025 (réanalyse brute, réanalyse corrigée, station).

Usage, depuis la racine du projet (quelques minutes, connexion Internet nécessaire) :
    python scripts/calibrer_correction.py
"""

import io
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.bias_correction import fit_quantile_map, apply_quantile_map, _normalize, CALIBRATION_FILE  # noqa: E402
from src.cities import CITY_CHOICES                                                                  # noqa: E402
from src.pricing import split_into_coverage_periods                                                  # noqa: E402
from src.simulation import ClientProfile, simulate_year                                              # noqa: E402
from src.weather_api import get_coordinates, fetch_historical_precipitation, WeatherAPIError         # noqa: E402


def patient(func, *args):
    """Appel à Open-Meteo qui attend et réessaie si la limite de requêtes par minute est atteinte."""
    for attempt in range(5):
        try:
            time.sleep(2)
            return func(*args)
        except WeatherAPIError as e:
            if "429" not in str(e):
                raise
            time.sleep(65)
    raise RuntimeError("Open-Meteo refuse toujours les requêtes")

FIRST, LAST, SPLIT = 2001, 2025, 2013          # calage 2001-2013, validation 2014-2025
MAX_KM, MIN_COMPLETENESS = 35.0, 0.85
FIRST_RECORD_MAX = 2005    # la station doit avoir des relevés avant 2005
GHCN = "https://www.ncei.noaa.gov/pub/data/ghcn/daily"
NCEI_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
PROFILE = ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city="-", subscription_date="2026-01-01")


def get(url, **kw):
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=180, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"échec du téléchargement : {url}")


def pretty_station_name(raw):
    """Nom GHCN (anglais, majuscules) rendu lisible : « COTE D AZUR » -> « Côte d'Azur »."""
    import re
    n = re.sub(r"D (?=[A-Z])", "d'", raw.strip().title())
    n = n.replace("Cote d'Azur", "Côte d'Azur").replace("Marseilles", "Marseille").replace("Pte De", "Pointe de")
    n = re.sub(r"(De|Du|Des|La|Le|Les)", lambda m: m.group(1).lower(), n)
    return n[0].upper() + n[1:]


def km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


def candidate_stations():
    """Stations avec des relevés de pluie couvrant 2001-2025."""
    inv = pd.read_fwf(io.StringIO(get(f"{GHCN}/ghcnd-inventory.txt").text), header=None,
                      colspecs=[(0, 11), (12, 20), (21, 30), (31, 35), (36, 40), (41, 45)],
                      names=["id", "lat", "lon", "element", "first", "last"])
    inv = inv[(inv["element"] == "PRCP") & (inv["first"] <= FIRST_RECORD_MAX) & (inv["last"] >= LAST)]
    names = pd.read_fwf(io.StringIO(get(f"{GHCN}/ghcnd-stations.txt").text), header=None,
                        colspecs=[(0, 11), (41, 71)], names=["id", "name"])
    return inv.merge(names, on="id")


def station_series(station_id):
    params = {"dataset": "daily-summaries", "stations": station_id, "dataTypes": "PRCP",
              "startDate": f"{FIRST}-01-01", "endDate": f"{LAST}-12-31", "format": "csv", "units": "metric"}
    raw = pd.read_csv(io.StringIO(get(NCEI_URL, params=params).text), parse_dates=["DATE"])
    if raw.empty or "PRCP" not in raw:
        return None
    return raw.rename(columns={"DATE": "date", "PRCP": "station"})[["date", "station"]].dropna()


def mean_annual_indemnity(df, column, years):
    """Indemnités annuelles moyennes du profil par défaut, années civiles de 365 jours."""
    days = pd.DataFrame({"date": pd.date_range(f"{years[0]}-01-01", f"{years[-1]}-12-31")})
    data = days.merge(pd.DataFrame({"date": df["date"], "precipitation": df[column]}), on="date", how="left")
    data["missing"] = data["precipitation"].isna()      # jours sans relevé à la station
    data["precipitation"] = data["precipitation"].fillna(0.0)
    periods = split_into_coverage_periods(data, 1, 1, years[0], years[-1])
    values = [simulate_year(p["precipitation"], PROFILE)["indemnity"].sum() for y, p in periods.items() if y in years]
    return float(np.mean(values)) if values else float("nan")


def calibrate_city(city, stations):
    lat, lon, label = patient(get_coordinates, city)
    stations = stations.assign(dist=[km(lat, lon, a, b) for a, b in zip(stations["lat"], stations["lon"])])
    for _, st in stations[stations["dist"] <= MAX_KM].sort_values("dist").head(3).iterrows():
        obs = station_series(st["id"])
        if obs is None:
            continue
        completeness = len(obs) / len(pd.date_range(f"{FIRST}-01-01", f"{LAST}-12-31"))
        if completeness < MIN_COMPLETENESS:
            continue
        grid = patient(fetch_historical_precipitation, lat, lon, f"{FIRST}-01-01", f"{LAST}-12-31")
        both = grid.merge(obs, on="date")              # jours où la station a un relevé
        both = both[~both["missing"]]
        first_obs_year = int(both["date"].dt.year.min())
        calib, valid = both[both["date"].dt.year <= SPLIT], both[both["date"].dt.year > SPLIT]

        # Validation hors échantillon : correction calée sur 2001-2013, évaluée sur 2014-2025
        q_split = fit_quantile_map(calib["precipitation"], calib["station"])
        valid = valid.assign(corrige=apply_quantile_map(valid["precipitation"], q_split))
        test_years = list(range(SPLIT + 1, LAST + 1))
        v_model = mean_annual_indemnity(valid, "precipitation", test_years)
        v_corr = mean_annual_indemnity(valid, "corrige", test_years)
        v_obs = mean_annual_indemnity(valid, "station", test_years)
        # Méthode concurrente : rapport des indemnités station / réanalyse observé sur la période de calage
        calib_years = list(range(max(FIRST, first_obs_year), SPLIT + 1))
        ratio = mean_annual_indemnity(calib, "station", calib_years) / mean_annual_indemnity(calib, "precipitation", calib_years)
        v_ratio = v_model * ratio
        full_years = list(range(max(FIRST, first_obs_year), LAST + 1))
        full_ratio = mean_annual_indemnity(both, "station", full_years) / mean_annual_indemnity(both, "precipitation", full_years)

        return _normalize(city), {
            "city": city, "grid_label": label, "grid_lat": round(lat, 4), "grid_lon": round(lon, 4),
            "station_id": st["id"], "station_name": pretty_station_name(st["name"]),
            "station_lat": float(st["lat"]), "station_lon": float(st["lon"]),
            "distance_km": round(float(st["dist"]), 1),
            "period": f"{max(FIRST, first_obs_year)}-{LAST}", "n_days": int(len(both)), "completeness": round(completeness, 3),
            "wet_days_model": round(float((both["precipitation"] > 0).mean() * 365), 1),
            "wet_days_station": round(float((both["station"] > 0).mean() * 365), 1),
            "validation": {
                "period": f"{SPLIT + 1}-{LAST}", "calibration_period": f"{FIRST}-{SPLIT}",
                "indemnity_model": round(v_model), "indemnity_corrected": round(v_corr), "indemnity_station": round(v_obs),
                "indemnity_ratio_method": round(v_ratio),
            },
            "indemnity_ratio": round(full_ratio, 4),
            "qmap": fit_quantile_map(both["precipitation"], both["station"]),
        }
    return _normalize(city), None


def main():
    stations = candidate_stations()
    print(f"{len(stations)} stations GHCN avec des relevés de pluie {FIRST}-{LAST}")
    result, skipped = {}, []
    for city in CITY_CHOICES:
        key, cal = calibrate_city(city, stations)
        if cal is None:
            skipped.append(city)
            print(f"{city:18s} : aucune station complète à moins de {MAX_KM:.0f} km")
            continue
        result[key] = cal
        v = cal["validation"]
        print(f"{city:18s} : {cal['station_name']:28s} {cal['distance_km']:5.1f} km | indemnités 2014-2025 "
              f"brut {v['indemnity_model']:6d} / quantiles {v['indemnity_corrected']:6d} / rapport {v['indemnity_ratio_method']:6d} / station {v['indemnity_station']:6d} €")
    CALIBRATION_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    # Bilan de la validation hors échantillon
    err_raw = [c["validation"]["indemnity_model"] / c["validation"]["indemnity_station"] - 1 for c in result.values()]
    err_cor = [c["validation"]["indemnity_corrected"] / c["validation"]["indemnity_station"] - 1 for c in result.values()]
    err_rat = [c["validation"]["indemnity_ratio_method"] / c["validation"]["indemnity_station"] - 1 for c in result.values()]
    print(f"\n{len(result)} villes calées, {len(skipped)} sans station : {', '.join(skipped) or 'aucune'}")
    print(f"Écart des indemnités 2014-2025 à la station — brut : moyen {np.mean(err_raw):+.1%}, "
          f"absolu moyen {np.mean(np.abs(err_raw)):.1%} | corrigé : moyen {np.mean(err_cor):+.1%}, "
          f"absolu moyen {np.mean(np.abs(err_cor)):.1%} | rapport : moyen {np.mean(err_rat):+.1%}, "
          f"absolu moyen {np.mean(np.abs(err_rat)):.1%}")
    print(f"Fichier écrit : {CALIBRATION_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
