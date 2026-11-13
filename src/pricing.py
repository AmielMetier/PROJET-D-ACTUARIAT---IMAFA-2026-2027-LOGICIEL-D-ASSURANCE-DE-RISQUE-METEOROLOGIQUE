"""
Module de Pricing Actuariel (Département Tarification).
Calcule la prime d'assurance météorologique (prime pure, chargement de sécurité et prime commerciale).
"""

from datetime import date, timedelta
from typing import Dict, Any
import numpy as np
import pandas as pd
from .simulation import ClientProfile, simulate_year

# Part maximale de jours sans donnée tolérée dans une période historique (au-delà, la période est écartée)
MAX_MISSING_SHARE = 0.05
# Durée du contrat : 365 jours, y compris lorsque la période traverse un 29 février
COVERAGE_DAYS = 365


def coverage_start(year: int, month: int, day: int) -> pd.Timestamp:
    """Date de début de couverture pour une année donnée (un 29 février devient 28 février)."""
    if month == 2 and day == 29:
        day = 28
    return pd.Timestamp(year=year, month=month, day=day)


def split_into_coverage_periods(
    df: pd.DataFrame,
    month: int,
    day: int,
    first_year: int,
    last_year: int
) -> Dict[int, Dict[str, Any]]:
    """
    Découpe une série journalière ['date', 'precipitation', 'missing'] en périodes de couverture
    de 365 jours commençant chaque année au jour/mois de souscription (ex. du 13/11/2010 au 12/11/2011).
    Comme le contrat, chaque période compte exactement 365 jours, même si elle contient un 29 février.

    Seules les périodes complètes (toutes les dates présentes) et avec au plus
    MAX_MISSING_SHARE de jours sans donnée sont conservées.

    :return: {année de début: {"precipitation": Series, "start", "end", "missing_days"}}
    """
    periods = {}
    for year in range(first_year, last_year + 1):
        start = coverage_start(year, month, day)
        end = start + pd.Timedelta(days=COVERAGE_DAYS)  # borne exclue
        expected_days = COVERAGE_DAYS
        mask = (df["date"] >= start) & (df["date"] < end)
        window = df.loc[mask]
        if len(window) < expected_days:
            continue  # période incomplète (trop récente ou hors archive)
        missing_days = int(window["missing"].sum()) if "missing" in window else 0
        if missing_days > MAX_MISSING_SHARE * expected_days:
            continue
        periods[year] = {
            "precipitation": window["precipitation"].reset_index(drop=True),
            "start": start.date(),
            "end": (end - pd.Timedelta(days=1)).date(),
            "missing_days": missing_days,
        }
    return periods


def price_contract_historical(
    historical_precip_by_year: Dict[int, pd.Series],
    profile: ClientProfile,
    safety_beta: float = 0.30,
    expense_rate: float = 0.15
) -> Dict[str, Any]:
    """
    Tarifie le contrat annuel d'assurance météo à partir de plusieurs années d'historique.

    Principe de l'écart-type : prime chargée = E[I] + beta * sigma(I), où I est l'indemnité annuelle.
    Le chargement de sécurité croît donc avec la variabilité du risque (un client exposé à des années
    très irrégulières paie plus qu'un client au risque stable, à prime pure égale).

    :param historical_precip_by_year: Dictionnaire {année: pd.Series(pluie_journalière)}
    :param profile: Profil client (CA, Cf, pl_bar, etc.)
    :param safety_beta: Coefficient beta appliqué à l'écart-type des indemnités annuelles (ex: 0,30)
    :param expense_rate: Frais de gestion et acquisition en % de la prime commerciale (ex: 15%)
    :return: Métriques actuarielles (prime pure, prime commerciale, statistiques sinistres)
    """
    if not historical_precip_by_year:
        raise ValueError("Aucune année d'historique météo exploitable pour tarifer le contrat.")

    annual_indemnities = []
    annual_uninsured_results = []

    for year, series in historical_precip_by_year.items():
        sim_df = simulate_year(series, profile)
        annual_indemnities.append(float(sim_df["indemnity"].sum()))
        annual_uninsured_results.append(float(sim_df["r_nass"].sum()))

    indemnities_arr = np.array(annual_indemnities, dtype=float)

    # Statistiques actuarielles
    pure_premium = float(np.mean(indemnities_arr))
    std_indemnity = float(np.std(indemnities_arr, ddof=1)) if len(indemnities_arr) > 1 else 0.0
    max_loss = float(np.max(indemnities_arr))
    var_95 = float(np.percentile(indemnities_arr, 95))

    # Prime commerciale = (E[I] + beta * sigma) / (1 - Frais de gestion)
    safety_loading = safety_beta * std_indemnity
    commercial_premium = (pure_premium + safety_loading) / (1.0 - expense_rate)
    expense_loading = commercial_premium - pure_premium - safety_loading

    return {
        "pure_premium": pure_premium,
        "std_indemnity": std_indemnity,
        "max_historical_claim": max_loss,
        "var_95": var_95,
        "safety_beta": safety_beta,
        "safety_loading": safety_loading,
        "expense_rate": expense_rate,
        "expense_loading": expense_loading,
        "commercial_premium": commercial_premium,
        "n_years": len(indemnities_arr),
        "historical_indemnities": dict(zip(historical_precip_by_year.keys(), annual_indemnities)),
        "historical_uninsured_results": dict(zip(historical_precip_by_year.keys(), annual_uninsured_results)),
    }


def coverage_end(subscription_date: date) -> date:
    """Dernier jour couvert : 365 jours à partir de la date de souscription incluse."""
    return subscription_date + timedelta(days=364)
