"""Tests du cache des téléchargements météo (en mémoire, durée de vie limitée)."""

from datetime import datetime

import pytest

from src import weather_api, weather_cache


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


PAYLOAD = {"daily": {"time": ["2020-01-01", "2020-01-02"], "precipitation_sum": [0.0, 7.5]}}


@pytest.fixture(autouse=True)
def empty_cache():
    weather_cache.fetch_precipitation_cached.clear()
    yield
    weather_cache.fetch_precipitation_cached.clear()


def test_second_call_is_served_from_cache(monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return FakeResponse(200, PAYLOAD)
    monkeypatch.setattr(weather_api.requests, "get", fake_get)

    df1, t1 = weather_cache.fetch_precipitation_cached(43.7, 7.27, "2020-01-01", "2020-01-02")
    df2, t2 = weather_cache.fetch_precipitation_cached(43.7, 7.27, "2020-01-01", "2020-01-02")
    assert len(calls) == 1                         # une seule requête à Open-Meteo
    assert df1.equals(df2) and t1 == t2            # mêmes données, même heure de récupération
    assert df1["precipitation"].tolist() == [0.0, 7.5]

    weather_cache.fetch_precipitation_cached(43.7, 7.27, "2019-01-01", "2019-01-02")
    assert len(calls) == 2                         # autre période : nouvelle requête


def test_errors_are_never_cached(monkeypatch):
    responses = [FakeResponse(400, {"reason": "refus"}), FakeResponse(200, PAYLOAD)]
    monkeypatch.setattr(weather_api.requests, "get", lambda *a, **k: responses.pop(0))

    with pytest.raises(weather_api.WeatherAPIError):
        weather_cache.fetch_precipitation_cached(43.7, 7.27, "2020-01-01", "2020-01-02")
    df, _ = weather_cache.fetch_precipitation_cached(43.7, 7.27, "2020-01-01", "2020-01-02")
    assert len(df) == 2                            # le calcul suivant a bien réessayé


def test_cache_expires_after_a_few_hours():
    ttl = weather_cache.fetch_precipitation_cached._info.ttl
    seconds = ttl.total_seconds() if hasattr(ttl, "total_seconds") else ttl
    assert seconds == weather_cache.CACHE_TTL_HOURS * 3600 == 6 * 3600


def test_fetched_label_is_readable():
    label = weather_cache.fetched_label(datetime(2026, 11, 16, 14, 5, tzinfo=weather_cache.PARIS))
    assert label == "Données météo récupérées le 16/11/2026 à 14 h 05 (gardées 6 h en cache)."
