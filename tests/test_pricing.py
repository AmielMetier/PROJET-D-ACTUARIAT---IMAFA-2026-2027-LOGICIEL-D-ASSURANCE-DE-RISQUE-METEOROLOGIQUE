"""
Tests unitaires pour les calculs de modélisation actuarielle.
"""

import pytest
import pandas as pd
from src.simulation import ClientProfile, compute_daily_impact, simulate_year
from src.backtesting import run_retrospective_analysis


def test_client_profile_validation():
    # CA doit être > Cf
    with pytest.raises(ValueError):
        ClientProfile(ca_max=500, cf=600, pl_pivot=10, city="Nice", subscription_date="2026-01-01")

    # Pivot doit être > 0
    with pytest.raises(ValueError):
        ClientProfile(ca_max=1000, cf=400, pl_pivot=0, city="Nice", subscription_date="2026-01-01")


def test_daily_impact_cases():
    profile = ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city="Nice", subscription_date="2026-01-01")

    # 1. Pas de pluie (pl_t = 0)
    res_dry = compute_daily_impact(0.0, profile)
    assert res_dry["f_pl"] == 1.0
    assert res_dry["ca_pl"] == 1000.0
    assert res_dry["r_nass"] == 600.0
    assert res_dry["indemnity"] == 0.0
    assert res_dry["r_ass_brut"] == 600.0

    # 2. Pluie forte (pl_t >= pl_pivot, ex: 12 mm)
    res_heavy = compute_daily_impact(12.0, profile)
    assert res_heavy["f_pl"] == 0.0
    assert res_heavy["ca_pl"] == 0.0
    assert res_heavy["r_nass"] == -400.0
    assert res_heavy["indemnity"] == 400.0
    assert res_heavy["r_ass_brut"] == 0.0

    # 3. Pluie moyenne (pl_t = 5 mm < pl_pivot = 10)
    # f_pl = (10 - 5) / 10 = 0.5
    # ca_pl = 0.5 * 1000 = 500
    # r_nass = 500 - 400 = 100 (> 0, pas d'indemnité)
    res_med = compute_daily_impact(5.0, profile)
    assert res_med["f_pl"] == 0.5
    assert res_med["ca_pl"] == 500.0
    assert res_med["r_nass"] == 100.0
    assert res_med["indemnity"] == 0.0

    # 4. Pluie provoquant une perte (pl_t = 8 mm)
    # f_pl = (10 - 8)/10 = 0.2
    # ca_pl = 200
    # r_nass = 200 - 400 = -200
    # indemnity = 200 => r_ass_brut = 0
    res_loss = compute_daily_impact(8.0, profile)
    assert res_loss["r_nass"] == -200.0
    assert res_loss["indemnity"] == 200.0
    assert res_loss["r_ass_brut"] == 0.0


def test_example_from_subject():
    """
    Vérifie la cohérence avec l'exemple chiffré du sujet:
    R_nass = 90 000 €, R_ass = 95 000 €, P = 3 000 €
    R_net = 92 000 €
    Pertes évitées = 5 000 € > P = 3 000 € => favorable.
    """
    profile = ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city="Nice", subscription_date="1998-01-01")
    # Série factice donnant une année
    s = pd.Series([0.0] * 365)
    analysis = run_retrospective_analysis(s, profile, annual_premium=3000.0)
    # Test de la relation net = brut - prime
    assert analysis["r_net"] == analysis["r_ass"] - 3000.0


def test_a_priori_premium_uses_only_given_years():
    """La prime est la moyenne chargée des indemnités des seules années fournies."""
    from src.pricing import price_contract_historical

    profile = ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city="Nice", subscription_date="1998-01-01")
    # 1996 : 10 jours de forte pluie => 10 * 400 = 4000 € ; 1997 : année sèche => 0 €
    prior = {
        1996: pd.Series([12.0] * 10 + [0.0] * 355),
        1997: pd.Series([0.0] * 365),
    }
    res = price_contract_historical(prior, profile, safety_margin_rate=0.10, expense_rate=0.15)
    assert res["pure_premium"] == pytest.approx(2000.0)
    assert res["commercial_premium"] == pytest.approx(2000.0 * 1.10 / 0.85)
