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
from src.bias_correction import find_calibration, correct_dataframe  # noqa: E402

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

    calibration = find_calibration(CITY, lat, lon)
    corrected = correct_dataframe(grid, calibration)

    p_grid = split_into_coverage_periods(grid, 1, 1, FIRST_YEAR, LAST_YEAR)
    p_corr = split_into_coverage_periods(corrected, 1, 1, FIRST_YEAR, LAST_YEAR)
    p_station = split_into_coverage_periods(station, 1, 1, FIRST_YEAR, LAST_YEAR)
    common = sorted(set(p_grid) & set(p_station))
    p_grid = {y: p_grid[y] for y in common}
    p_corr = {y: p_corr[y] for y in common}
    p_station = {y: p_station[y] for y in common}
    missing = sum(p["missing_days"] for p in p_station.values())

    g, c, s = yearly_stats(p_grid), yearly_stats(p_corr), yearly_stats(p_station)
    price_g = price_contract_historical({y: p["precipitation"] for y, p in p_grid.items()}, PROFILE)
    price_c = price_contract_historical({y: p["precipitation"] for y, p in p_corr.items()}, PROFILE)
    price_s = price_contract_historical({y: p["precipitation"] for y, p in p_station.items()}, PROFILE)

    print(f"Open-Meteo : point de grille de {label} ({lat:.3f} ; {lon:.3f})")
    print(f"Station    : {STATION_ID} {STATION_LABEL} — {len(common)} années complètes "
          f"({common[0]}-{common[-1]}), {missing} jours manquants comptés à 0 mm")
    print()
    print(f"Correction : {'station ' + calibration['station_id'] if calibration else 'aucune calibration trouvée'}")
    print(f"{'Moyenne annuelle':38s} {'Open-Meteo':>12s} {'Corrigée':>12s} {'Station':>12s} {'Écart brut':>11s} {'Écart corr.':>11s}")
    lines = [
        ("Cumul de pluie (mm)", "cumul_mm", 0),
        ("Jours avec pluie (> 0 mm)", "jours_pluie", 0),
        ("Jours ≥ 1 mm", "jours_1mm", 0),
        ("Jours ≥ 6 mm (seuil de perte)", "jours_seuil", 1),
        ("Jours ≥ 10 mm (activité arrêtée)", "jours_pivot", 1),
        ("Pluie journalière maximale (mm)", "max_mm", 1),
    ]
    def row(name, a, b, ref, fmt):
        print(f"{name:38s} {fmt(a):>12s} {fmt(b):>12s} {fmt(ref):>12s} {(a / ref - 1):>+11.0%} {(b / ref - 1):>+11.0%}")
    for name, col, dec in lines:
        row(name, g[col].mean(), c[col].mean(), s[col].mean(), lambda v, d=dec: fmt_num(v, d))
    money = lambda v: fmt_eur(v, 0)
    row("Prime pure E[I]", price_g["pure_premium"], price_c["pure_premium"], price_s["pure_premium"], money)
    row("Prime commerciale", price_g["commercial_premium"], price_c["commercial_premium"], price_s["commercial_premium"], money)
    row("Résultat annuel non assuré", g["r_nass"].mean(), c["r_nass"].mean(), s["r_nass"].mean(), money)
    if calibration:
        v = calibration["validation"]
        print(f"\nValidation hors échantillon (correction calée sur {v['calibration_period']}, testée sur {v['period']}) : "
              f"indemnités brut {money(v['indemnity_model'])}, corrigé {money(v['indemnity_corrected'])}, "
              f"station {money(v['indemnity_station'])}")
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
