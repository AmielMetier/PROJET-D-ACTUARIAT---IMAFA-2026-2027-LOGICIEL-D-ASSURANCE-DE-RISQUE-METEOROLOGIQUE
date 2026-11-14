"""Tests de la correction de biais par quantiles."""

import numpy as np
import pandas as pd
import pytest

from src import bias_correction as bc


@pytest.fixture
def synthetic():
    """Station : 76 % de jours secs ; réanalyse : 57 % de jours secs, bruine et intensités lissées."""
    rng = np.random.default_rng(1)
    obs = np.where(rng.random(9000) < 0.76, 0, rng.exponential(8, 9000))
    mod = np.where(rng.random(9000) < 0.57, 0, rng.gamma(0.6, 7, 9000))
    return mod, obs, bc.fit_quantile_map(mod, obs)


def test_correction_recovers_station_distribution(synthetic):
    mod, obs, qmap = synthetic
    corrected = bc.apply_quantile_map(mod, qmap)
    assert np.mean(corrected == 0) == pytest.approx(np.mean(obs == 0), abs=0.01)   # jours secs
    assert np.mean(corrected >= 6) == pytest.approx(np.mean(obs >= 6), abs=0.005)  # au-delà du seuil
    assert np.mean(corrected >= 10) == pytest.approx(np.mean(obs >= 10), abs=0.005)


def test_correction_keeps_dry_days_dry_and_order(synthetic):
    mod, _, qmap = synthetic
    x = np.array([0.0, 0.1, 0.5, 2.0, 5.0, 12.0, 40.0])
    y = bc.apply_quantile_map(x, qmap)
    assert y[0] == 0.0
    assert y[1] == 0.0                       # la bruine que la station ne voit pas devient un jour sec
    assert np.all(np.diff(y) >= 0)           # l'ordre des journées est conservé
    assert np.all(y >= 0)


def test_extrapolation_beyond_calibrated_maximum():
    qmap = bc.fit_quantile_map(np.linspace(0, 50, 1000), np.linspace(0, 100, 1000))
    assert bc.apply_quantile_map([75.0], qmap)[0] == pytest.approx(150.0)


def test_correct_dataframe_without_calibration_is_unchanged():
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3), "precipitation": [0.0, 1.2, 8.0], "missing": False})
    assert bc.correct_dataframe(df, None) is df


def test_find_calibration_by_name_and_by_distance(monkeypatch):
    fake = {"nice": {"city": "Nice", "grid_lat": 43.703, "grid_lon": 7.266}}
    monkeypatch.setattr(bc, "load_calibrations", lambda: fake)
    assert bc.find_calibration("  NICE ")["city"] == "Nice"                 # nom, casse et espaces ignorés
    assert bc.find_calibration("Nice centre", 43.70, 7.25)["city"] == "Nice"  # point de grille à 1,4 km
    assert bc.find_calibration("Cannes", 43.55, 7.01) is None                 # à plus de 15 km


def test_bundled_calibrations_are_consistent():
    calibrations = bc.load_calibrations()
    if not calibrations:
        pytest.skip("data/calibration_stations.json absent")
    for key, cal in calibrations.items():
        q = cal["qmap"]
        assert len(q["probs"]) == len(q["q_model"]) == len(q["q_obs"])
        assert np.all(np.diff(q["q_model"]) >= 0) and np.all(np.diff(q["q_obs"]) >= 0)
        assert cal["distance_km"] <= 25          # rayon de recherche du script de calibration
        assert cal["station_id"].startswith("FR")  # stations françaises uniquement
        v = cal["validation"]                       # activée par défaut seulement si elle aide hors échantillon
        helps = abs(v["indemnity_corrected"] - v["indemnity_station"]) < abs(v["indemnity_model"] - v["indemnity_station"])
        assert cal["recommended"] == helps
