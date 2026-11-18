"""Jours de fermeture hebdomadaire du commerce."""
import pandas as pd
import pytest

from src.simulation import ClientProfile, simulate_year, open_days_count
from src.pricing import split_into_coverage_periods, price_contract_historical
from src.pdf_generator import make_quote_ref


def profile(closed=()):
    return ClientProfile(ca_max=1000.0, cf=400.0, pl_pivot=10.0, city="Nice",
                         subscription_date="2026-01-01", closed_weekdays=closed)


def rainy_year(start="2025-01-06", days=365, rain=12.0):
    # 2025-01-06 est un lundi
    return pd.Series([rain] * days, index=pd.date_range(start, periods=days, freq="D"))


def test_closed_day_has_no_revenue_cost_or_indemnity():
    sim = simulate_year(rainy_year(), profile(closed=(6,)))
    sundays = sim.index.dayofweek == 6
    assert sim.loc[sundays, ["ca_pl", "r_nass", "indemnity", "r_ass_brut"]].abs().sum().sum() == 0
    assert (sim.loc[~sundays, "indemnity"] == 400.0).all()
    assert sim["open"].sum() == (~sundays).sum()


def test_no_closed_day_keeps_previous_results():
    s = rainy_year()
    with_dates = simulate_year(s, profile())
    without_dates = simulate_year(s.reset_index(drop=True), profile())
    assert with_dates["indemnity"].sum() == pytest.approx(without_dates["indemnity"].sum())
    assert with_dates["open"].all()


def test_closing_sunday_reduces_premium_proportionally_for_uniform_rain():
    years = {y: rainy_year(start=f"{y}-01-01") for y in (2020, 2021, 2022)}
    p7 = price_contract_historical(years, profile())
    p6 = price_contract_historical(years, profile(closed=(6,)))
    open_share = sum(open_days_count(f"{y}-01-01", 365, profile((6,))) for y in years) / (3 * 365)
    assert p6["pure_premium"] == pytest.approx(p7["pure_premium"] * open_share, rel=0.02)
    assert p6["pure_premium"] < p7["pure_premium"]


def test_coverage_periods_are_indexed_by_date():
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", "2023-12-31"), "precipitation": 0.0, "missing": False})
    periods = split_into_coverage_periods(df, 3, 15, 2020, 2022)
    s = periods[2020]["precipitation"]
    assert isinstance(s.index, pd.DatetimeIndex)
    assert s.index[0] == pd.Timestamp("2020-03-15") and len(s) == 365


def test_closed_days_require_dated_series():
    with pytest.raises(ValueError):
        simulate_year(pd.Series([0.0] * 10), profile(closed=(6,)))


def test_invalid_closed_days():
    with pytest.raises(ValueError):
        profile(closed=tuple(range(7)))
    with pytest.raises(ValueError):
        profile(closed=(7,))


def test_open_days_count_and_quote_ref():
    assert open_days_count("2026-01-01", 365, profile()) == 365
    assert open_days_count("2026-01-01", 365, profile((6,))) == 313  # 52 dimanches en 2026
    assert make_quote_ref(profile()) != make_quote_ref(profile((6,)))
