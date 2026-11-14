"""
Compare les précipitations utilisées par le logiciel (Open-Meteo, réanalyse ERA5 au point de grille
de la ville) aux relevés d'une station au sol (NCEI, réseau GHCN-Daily), puis l'effet sur la prime.

Usage, depuis la racine du projet :
    python scripts/comparaison_station.py

Sorties : un tableau dans le terminal et la figure report/figures/comparaison_station_nice.png.
Station par défaut : FRE00104120, Nice (aéroport), relevés Météo-France diffusés par NCEI.
"""

import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.simulation import ClientProfile, simulate_year              # noqa: E402
from src.weather_api import get_coordinates, fetch_historical_precipitation  # noqa: E402
from src.pricing import split_into_coverage_periods, price_contract_historical  # noqa: E402
from src.formatting import fmt_eur, fmt_num                           # noqa: E402

CITY = "Nice"
STATION_ID, STATION_LABEL = "FRE00104120", "Nice (aéroport)"
FIRST_YEAR, LAST_YEAR = 2001, 2025
PROFILE = ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city=CITY, subscription_date="2026-01-01")
NCEI_URL = "https://www.ncei.noaa.gov/access/services/data/v1"


def fetch_station():
    params = {
        "dataset": "daily-summaries", "stations": STATION_ID, "dataTypes": "PRCP",
        "startDate": f"{FIRST_YEAR}-01-01", "endDate": f"{LAST_YEAR}-12-31",
        "format": "csv", "units": "metric",
    }
    response = requests.get(NCEI_URL, params=params, timeout=120)
    response.raise_for_status()
    raw = pd.read_csv(io.StringIO(response.text), parse_dates=["DATE"])
    # Calendrier complet : les jours absents du fichier sont marqués manquants
    days = pd.DataFrame({"date": pd.date_range(f"{FIRST_YEAR}-01-01", f"{LAST_YEAR}-12-31", freq="D")})
    df = days.merge(raw.rename(columns={"DATE": "date", "PRCP": "precipitation"})[["date", "precipitation"]],
                    on="date", how="left")
    df["missing"] = df["precipitation"].isna()
    df["precipitation"] = df["precipitation"].fillna(0.0)
    return df


def yearly_stats(periods):
    rows = []
    for year, p in sorted(periods.items()):
        rain = p["precipitation"]
        sim = simulate_year(rain, PROFILE)
        rows.append({
            "annee": year,
            "cumul_mm": rain.sum(),
            "jours_pluie": int((rain > 0).sum()),
            "jours_1mm": int((rain >= 1).sum()),
            "jours_seuil": int((rain >= 6).sum()),     # seuil critique du profil : 6 mm
            "jours_pivot": int((rain >= 10).sum()),
            "max_mm": rain.max(),
            "indemnites": sim["indemnity"].sum(),
            "r_nass": sim["r_nass"].sum(),
        })
    return pd.DataFrame(rows).set_index("annee")


def main():
    lat, lon, label = get_coordinates(CITY)
    grid = fetch_historical_precipitation(lat, lon, f"{FIRST_YEAR}-01-01", f"{LAST_YEAR}-12-31")
    station = fetch_station()

    p_grid = split_into_coverage_periods(grid, 1, 1, FIRST_YEAR, LAST_YEAR)
    p_station = split_into_coverage_periods(station, 1, 1, FIRST_YEAR, LAST_YEAR)
    common = sorted(set(p_grid) & set(p_station))
    p_grid = {y: p_grid[y] for y in common}
    p_station = {y: p_station[y] for y in common}
    missing = sum(p["missing_days"] for p in p_station.values())

    g, s = yearly_stats(p_grid), yearly_stats(p_station)
    price_g = price_contract_historical({y: p["precipitation"] for y, p in p_grid.items()}, PROFILE)
    price_s = price_contract_historical({y: p["precipitation"] for y, p in p_station.items()}, PROFILE)

    print(f"Open-Meteo : point de grille de {label} ({lat:.3f} ; {lon:.3f})")
    print(f"Station    : {STATION_ID} {STATION_LABEL} — {len(common)} années complètes "
          f"({common[0]}-{common[-1]}), {missing} jours manquants comptés à 0 mm")
    print()
    print(f"{'Moyenne annuelle':38s} {'Open-Meteo':>12s} {'Station':>12s} {'Écart':>8s}")
    lines = [
        ("Cumul de pluie (mm)", "cumul_mm", 0),
        ("Jours avec pluie (> 0 mm)", "jours_pluie", 0),
        ("Jours ≥ 1 mm", "jours_1mm", 0),
        ("Jours ≥ 6 mm (seuil de perte)", "jours_seuil", 1),
        ("Jours ≥ 10 mm (activité arrêtée)", "jours_pivot", 1),
        ("Pluie journalière maximale (mm)", "max_mm", 1),
    ]
    for name, col, dec in lines:
        a, b = g[col].mean(), s[col].mean()
        print(f"{name:38s} {fmt_num(a, dec):>12s} {fmt_num(b, dec):>12s} {(a / b - 1):>+8.0%}")
    print(f"{'Prime pure E[I]':38s} {fmt_eur(price_g['pure_premium'], 0):>12s} {fmt_eur(price_s['pure_premium'], 0):>12s} "
          f"{(price_g['pure_premium'] / price_s['pure_premium'] - 1):>+8.0%}")
    print(f"{'Prime commerciale':38s} {fmt_eur(price_g['commercial_premium'], 0):>12s} "
          f"{fmt_eur(price_s['commercial_premium'], 0):>12s} "
          f"{(price_g['commercial_premium'] / price_s['commercial_premium'] - 1):>+8.0%}")
    print(f"{'Résultat annuel non assuré':38s} {fmt_eur(g['r_nass'].mean(), 0):>12s} {fmt_eur(s['r_nass'].mean(), 0):>12s} "
          f"{(g['r_nass'].mean() / s['r_nass'].mean() - 1):>+8.0%}")
    corr = np.corrcoef(g["indemnites"], s["indemnites"])[0, 1]
    print(f"\nCorrélation des indemnités annuelles entre les deux sources : {fmt_num(corr, 2)}")

    # Figure : indemnités annuelles selon la source
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [2.2, 1]})
    x = np.arange(len(common))
    ax1.bar(x - 0.2, g["indemnites"], 0.4, label="Open-Meteo (point de grille)", color="#2B6CB0")
    ax1.bar(x + 0.2, s["indemnites"], 0.4, label=f"Station {STATION_LABEL}", color="#ED8936")
    ax1.set_xticks(x[::2], [str(y) for y in common[::2]], rotation=45)
    ax1.set_ylabel("Indemnités annuelles (€)")
    ax1.set_title("Indemnités annuelles selon la source de pluie")
    ax1.legend(frameon=False, loc="upper left", ncol=2)
    ax1.set_ylim(0, ax1.get_ylim()[1] * 1.12)
    labels = ["> 0 mm", "≥ 1 mm", "≥ 6 mm", "≥ 10 mm"]
    cols = ["jours_pluie", "jours_1mm", "jours_seuil", "jours_pivot"]
    xx = np.arange(len(labels))
    ax2.bar(xx - 0.2, [g[c].mean() for c in cols], 0.4, color="#2B6CB0")
    ax2.bar(xx + 0.2, [s[c].mean() for c in cols], 0.4, color="#ED8936")
    ax2.set_xticks(xx, labels)
    ax2.set_ylabel("Jours par an (moyenne)")
    ax2.set_title("Nombre de jours de pluie")
    for ax in (ax1, ax2):
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"Nice, {common[0]}-{common[-1]} : réanalyse Open-Meteo contre station au sol", fontweight="bold")
    fig.tight_layout()
    out = ROOT / "report" / "figures" / "comparaison_station_nice.png"
    fig.savefig(out, dpi=130)
    print(f"Figure enregistrée : {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
