"""
Test de non-régression sur données réelles, sans connexion Internet.

data/nice_1998_rain.csv contient les précipitations journalières brutes de Nice en 1998, identiques
à celles qu'Open-Meteo renvoie pour le point de grille de Nice. Ce test vérifie que le modèle redonne
exactement les résultats de l'application pour cette année, avec la correction par station désactivée.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.simulation import ClientProfile, simulate_year
from src.backtesting import run_retrospective_analysis

CSV = Path(__file__).resolve().parent.parent / "data" / "nice_1998_rain.csv"


@pytest.fixture(scope="module")
def nice_1998():
    df = pd.read_csv(CSV, parse_dates=["date"])
    assert len(df) == 365 and df["date"].dt.year.eq(1998).all()
    return df["precipitation_sum"]


def test_real_rainfall_nice_1998(nice_1998):
    assert nice_1998.sum() == pytest.approx(585.5)
    assert nice_1998.max() == pytest.approx(44.5)


def test_model_on_real_data_matches_application(nice_1998):
    profile = ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city="Nice", subscription_date="1998-01-01")
    sim = simulate_year(nice_1998, profile)
    assert int((sim["indemnity"] > 0).sum()) == 29          # jours indemnisés
    assert sim["r_nass"].sum() == pytest.approx(178_010.0)  # résultat non assuré
    assert sim["indemnity"].sum() == pytest.approx(8_530.0)  # pertes évitées

    # Prime a priori de l'application pour 1998 sans correction (1983-1997, β = 0,30, frais 15 %)
    analysis = run_retrospective_analysis(nice_1998, profile, annual_premium=14_593.31)
    assert analysis["r_ass"] == pytest.approx(186_540.0)
    assert analysis["r_net"] == pytest.approx(171_946.69)
    assert not analysis["est_favorable"]
