"""
Tests des améliorations : périodes de 365 jours, géocodage, rétrospective pluriannuelle,
formatage français et contenu du devis.
"""

from datetime import date
import io
import pandas as pd
import pytest

from src import weather_api
from src.backtesting import run_multi_year_backtest
from src.formatting import fmt_eur, fmt_pct
from src.pdf_generator import generate_devis_pdf
from src.pricing import price_contract_historical, split_into_coverage_periods, COVERAGE_DAYS
from src.simulation import ClientProfile


PROFILE = ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city="Nice", subscription_date="2026-11-13")


def daily_df(start: str, end: str) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame({"date": dates, "precipitation": 0.0, "missing": False})


# --- Périodes de 365 jours ---------------------------------------------------

def test_leap_year_period_has_365_days_like_the_contract():
    df = daily_df("2020-01-01", "2021-12-31")
    periods = split_into_coverage_periods(df, month=1, day=1, first_year=2020, last_year=2020)
    assert len(periods[2020]["precipitation"]) == COVERAGE_DAYS == 365
    assert periods[2020]["end"] == date(2020, 12, 30)  # 2020 est bissextile


# --- Géocodage ---------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


def test_geocoding_searches_france_first_and_keeps_most_populated(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params.get("countryCode"))
        return FakeResponse({"results": [
            {"name": "Nice", "admin1": "Lieu-dit", "country": "France", "latitude": 1, "longitude": 1, "population": 20},
            {"name": "Nice", "admin1": "Provence-Alpes-Côte d'Azur", "country": "France",
             "latitude": 43.7, "longitude": 7.27, "population": 342_000},
        ]})
    monkeypatch.setattr(weather_api.requests, "get", fake_get)
    lat, lon, label = weather_api.get_coordinates("Nice")
    assert calls == ["FR"]
    assert (lat, lon) == (43.7, 7.27)
    assert label == "Nice, Provence-Alpes-Côte d'Azur, France"


def test_geocoding_falls_back_to_world_when_not_in_france(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params.get("countryCode"))
        if params.get("countryCode") == "FR":
            return FakeResponse({})
        return FakeResponse({"results": [{"name": "Genève", "country": "Suisse", "latitude": 46.2, "longitude": 6.14}]})
    monkeypatch.setattr(weather_api.requests, "get", fake_get)
    assert weather_api.get_coordinates("Genève")[2] == "Genève, Suisse"
    assert calls == ["FR", None]


# --- Rétrospective pluriannuelle ----------------------------------------------

def make_calendar_periods(heavy_days_by_year):
    """Années synthétiques : n jours de forte pluie (indemnité 400 € chacun), le reste sec."""
    return {
        year: {"precipitation": pd.Series([12.0] * n + [0.0] * (365 - n)), "missing_days": 0}
        for year, n in heavy_days_by_year.items()
    }


def test_multi_year_backtest_prices_each_year_a_priori():
    periods = make_calendar_periods({2000: 5, 2001: 5, 2002: 5, 2003: 20, 2004: 0})
    out = run_multi_year_backtest(periods, PROFILE, [2002, 2003, 2004], hist_years=10,
                                  safety_beta=0.0, expense_rate=0.0)
    table = out["table"].set_index("annee")

    # 2002 : tarifée sur 2000-2001 (2 000 € chacune) -> prime 2 000 €, indemnités 2 000 € -> pas favorable
    assert table.loc[2002, "prime"] == pytest.approx(2000.0)
    assert not table.loc[2002, "favorable"]
    # 2003 : années très pluvieuses -> indemnités 8 000 € > prime 2 000 € -> favorable
    assert table.loc[2003, "indemnites"] == pytest.approx(8000.0)
    assert table.loc[2003, "favorable"]
    # 2004 : la prime intègre 2003 (connue au 1er janvier 2004) mais pas 2004
    assert table.loc[2004, "prime"] == pytest.approx((2000 * 3 + 8000) / 4)

    summary = out["summary"]
    assert summary["n_years"] == 3
    assert summary["loss_ratio"] == pytest.approx(10000.0 / (2000 + 2000 + 3500))
    assert summary["share_favorable"] == pytest.approx(1 / 3)


def test_multi_year_backtest_skips_years_without_history():
    periods = make_calendar_periods({2000: 5, 2001: 5})
    out = run_multi_year_backtest(periods, PROFILE, [2000, 2001], hist_years=10, safety_beta=0.3, expense_rate=0.15)
    assert out["summary"] is None  # moins de 2 années d'historique avant chaque année


# --- Formatage et devis ---------------------------------------------------------

def test_french_number_format():
    assert fmt_eur(12478.666) == "12 478,67 €"
    assert fmt_eur(1500, 0, signed=True) == "+1 500 €"
    assert fmt_pct(0.873) == "87 %"


def test_devis_contains_client_insurer_and_signature():
    pypdf = pytest.importorskip("pypdf")
    res = price_contract_historical({2020: pd.Series([12.0] * 5 + [0.0] * 360),
                                     2021: pd.Series([0.0] * 365)}, PROFILE)
    pdf = generate_devis_pdf(PROFILE, res, client_name="Marie Dupont", company_name="SARL Les Glaces du Port",
                             issued=date(2026, 11, 13))
    text = pypdf.PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    for expected in ("Marie Dupont", "SARL Les Glaces du Port", "Météo Assur", "Bon pour accord",
                     "Signature", "13/12/2026"):
        assert expected in text, expected
