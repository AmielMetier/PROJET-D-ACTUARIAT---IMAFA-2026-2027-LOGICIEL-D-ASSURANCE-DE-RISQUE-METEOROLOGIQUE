"""
Module de Pricing Actuariel (Département Tarification).
Calcule la prime d'assurance météorologique (prime pure, chargement de sécurité et prime commerciale).
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from .simulation import ClientProfile, simulate_year


def price_contract_historical(
    historical_precip_by_year: Dict[int, pd.Series],
    profile: ClientProfile,
    safety_margin_rate: float = 0.10,
    expense_rate: float = 0.15
) -> Dict[str, Any]:
    """
    Tarifie le contrat annuel d'assurance météo à partir de plusieurs années d'historique.
    
    :param historical_precip_by_year: Dictionnaire {année: pd.Series(pluie_journalière)}
    :param profile: Profil client (CA, Cf, pl_bar, etc.)
    :param safety_margin_rate: Chargement de sécurité (ex: 10% ou multiple de l'écart-type)
    :param expense_rate: Frais de gestion et acquisition (ex: 15%)
    :return: Métriques actuarielles (prime pure, prime commerciale, statistiques sinistres)
    """
    annual_indemnities = []
    annual_uninsured_results = []
    annual_insured_gross = []

    for year, series in historical_precip_by_year.items():
        sim_df = simulate_year(series, profile)
        total_indemnity = sim_df["indemnity"].sum()
        annual_indemnities.append(total_indemnity)
        annual_uninsured_results.append(sim_df["r_nass"].sum())
        annual_insured_gross.append(sim_df["r_ass_brut"].sum())

    indemnities_arr = np.array(annual_indemnities, dtype=float)
    
    # Statistiques actuarielles
    pure_premium = float(np.mean(indemnities_arr))
    std_indemnity = float(np.std(indemnities_arr, ddof=1)) if len(indemnities_arr) > 1 else 0.0
    max_loss = float(np.max(indemnities_arr)) if len(indemnities_arr) > 0 else 0.0
    var_95 = float(np.percentile(indemnities_arr, 95)) if len(indemnities_arr) > 0 else 0.0

    # Calcul de la prime commerciale
    # Formule standard: Prime commerciale = (Prime pure + Chargement sécurité) / (1 - Frais de gestion)
    safety_loading = safety_margin_rate * pure_premium
    commercial_premium = (pure_premium + safety_loading) / (1.0 - expense_rate)

    return {
        "pure_premium": pure_premium,
        "std_indemnity": std_indemnity,
        "max_historical_claim": max_loss,
        "var_95": var_95,
        "safety_loading": safety_loading,
        "expense_rate": expense_rate,
        "commercial_premium": commercial_premium,
        "historical_indemnities": dict(zip(historical_precip_by_year.keys(), annual_indemnities)),
        "historical_uninsured_results": dict(zip(historical_precip_by_year.keys(), annual_uninsured_results)),
    }
