"""
Tests des périodes de couverture (date de souscription), de la gestion des jours
sans donnée, des pannes de l'API météo et de la référence de devis.
"""

from datetime import date
import pandas as pd
import pytest
import requests

from src import weather_api
from src.pricing import split_into_coverage_periods, coverage_end
from src.simulation import ClientProfile
from src.pdf_generator import make_quote_ref, generate_devis_pdf
from src.pricing import price_contract_historical


def daily_df(start: str, end: str, rain: float = 0.0) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"date": dates, "precipitation": rain, "missing": False})


def test_periods_start_on_subscription_day():
    df = daily_df("2020-01-01", "2023-06-30")
    periods = split_into_coverage_periods(df, month=11, day=13, first_year=2019, last_year=2023)
    # 2019 commence avant les données, 2022 et 2023 finissent après : seules 2020 et 2021 sont complètes
    assert sorted(periods) == [2020, 2021]
    assert periods[2020]["start"] == date(2020, 11, 13)
    assert periods[2020]["end"] == date(2021, 11, 12)
    assert len(periods[2020]["precipitation"]) == 365


def test_period_starting_29_february():
    df = daily_df("2019-01-01", "2022-12-31")
    periods = split_into_coverage_periods(df, month=2, day=29, first_year=2020, last_year=2021)
    assert periods[2021]["start"] == date(2021, 2, 28)


def test_period_rain_is_taken_from_the_right_window():
    """Une pluie forte hors de la fenêtre de couverture ne doit pas être comptée."""
    df = daily_df("2020-01-01", "2021-12-31")
    df.loc[df["date"] == "2020-03-01", "precipitation"] = 50.0  # avant le 01/06/2020
    df.loc[df["date"] == "2020-07-01", "precipitation"] = 50.0  # dans la fenêtre
    periods = split_into_coverage_periods(df, month=6, day=1, first_year=2020, last_year=2020)
    assert (periods[2020]["precipitation"] > 0).sum() == 1


def test_periods_with_too_many_missing_days_are_dropped():
    df = daily_df("2020-01-01", "2021-12-31")
    df.loc[df["date"].dt.month == 3, "missing"] = True  # 31 jours manquants en 2020 et 2021
    df.loc[(df["date"].dt.year == 2021) & (df["date"].dt.month == 3), "missing"] = False
    periods = split_into_coverage_periods(df, month=1, day=1, first_year=2020, last_year=2021)
    assert 2020 not in periods
    assert periods[2021]["missing_days"] == 0


def test_coverage_end_is_365_days_later():
    assert coverage_end(date(2026, 11, 13)) == date(2027, 11, 12)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_missing_values_are_flagged(monkeypatch):
    payload = {"daily": {"time": ["2020-01-01", "2020-01-02", "2020-01-03"], "precipitation_sum": [1.5, None, 0.0]}}
    monkeypatch.setattr(weather_api.requests, "get", lambda *a, **k: FakeResponse(200, payload))
    df = weather_api.fetch_historical_precipitation(43.7, 7.26, "2020-01-01", "2020-01-03")
    assert df["missing"].tolist() == [False, True, False]
    assert df["precipitation"].tolist() == [1.5, 0.0, 0.0]


def test_network_failure_raises_readable_error(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(weather_api.requests, "get", boom)
    monkeypatch.setattr(weather_api.time, "sleep", lambda s: None)
    with pytest.raises(weather_api.WeatherAPIError, match="3 tentatives"):
        weather_api.fetch_historical_precipitation(43.7, 7.26, "2020-01-01", "2020-01-03")


def test_refused_request_is_not_retried(monkeypatch):
    calls = []

    def refuse(*a, **k):
        calls.append(1)
        return FakeResponse(400, {"reason": "Date invalide"})
    monkeypatch.setattr(weather_api.requests, "get", refuse)
    with pytest.raises(weather_api.WeatherAPIError, match="Date invalide"):
        weather_api.get_coordinates("Nice")
    assert len(calls) == 1


def test_unknown_city_returns_none(monkeypatch):
    monkeypatch.setattr(weather_api.requests, "get", lambda *a, **k: FakeResponse(200, {}))
    assert weather_api.get_coordinates("Villeinexistante") is None


def test_quote_ref_depends_on_client_data():
    p1 = ClientProfile(1000.0, 400.0, 10.0, "Nice", "2026-11-13")
    p2 = ClientProfile(1000.0, 450.0, 10.0, "Nice", "2026-11-13")
    issued = date(2026, 11, 13)
    assert make_quote_ref(p1, issued) == make_quote_ref(p1, issued)
    assert make_quote_ref(p1, issued) != make_quote_ref(p2, issued)
    assert make_quote_ref(p1, issued).startswith("DEV-20261113-")


def test_devis_pdf_is_generated():
    profile = ClientProfile(1000.0, 400.0, 10.0, "Nice", "2026-11-13")
    res = price_contract_historical({2020: pd.Series([12.0] * 5 + [0.0] * 360)}, profile)
    pdf = generate_devis_pdf(profile, res, station_label="Nice", history_label="2020 (1 année)")
    assert pdf.startswith(b"%PDF")
