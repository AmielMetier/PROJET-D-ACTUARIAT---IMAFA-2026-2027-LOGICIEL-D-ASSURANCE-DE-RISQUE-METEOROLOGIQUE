"""
Module d'Analyse Rétrospective (Département R&D).
Compare pour une année 'a' quelconque dans le passé:
- R_nass (Résultat annuel non assuré)
- R_ass (Résultat annuel protégé par l'assurance)
- P_a (Tarif annuel calculé a priori)
- R_net = R_ass - P_a (Résultat annuel net de la prime)
"""

from typing import Dict, Any
import pandas as pd
from .simulation import ClientProfile, simulate_year


def run_retrospective_analysis(
    year_precip_series: pd.Series,
    profile: ClientProfile,
    annual_premium: float
) -> Dict[str, Any]:
    """
    Exécute l'analyse rétrospective complète sur une année passée 'a'.
    
    :param year_precip_series: Série des précipitations journalières sur l'année 'a'.
    :param profile: Profil du commerçant.
    :param annual_premium: Prime annuelle P_a calculée a priori.
    :return: Dictionnaire avec métriques annuelles et séries temporelles journalières.
    """
    sim_df = simulate_year(year_precip_series, profile)

    # Agrégations annuelles
    r_nass_total = float(sim_df["r_nass"].sum())
    r_ass_total = float(sim_df["r_ass_brut"].sum())
    total_indemnities = float(sim_df["indemnity"].sum())
    r_net_total = r_ass_total - annual_premium

    # Pertes évitées grâce à l'assurance:
    pertes_evitees = abs(r_ass_total - r_nass_total)
    gain_net_assurance = r_net_total - r_nass_total
    est_favorable = gain_net_assurance > 0  # ou pertes_evitees > annual_premium

    # Cumuls temporels journaliers pour les graphiques
    sim_df["cum_r_nass"] = sim_df["r_nass"].cumsum()
    sim_df["cum_r_ass"] = sim_df["r_ass_brut"].cumsum()
    # Répartition journalière de la prime sur 365 jours pour visualiser la courbe nette
    sim_df["cum_r_net"] = sim_df["cum_r_ass"] - (annual_premium * (sim_df.reset_index().index + 1) / len(sim_df))

    return {
        "r_nass": r_nass_total,
        "r_ass": r_ass_total,
        "premium": annual_premium,
        "r_net": r_net_total,
        "indemnities": total_indemnities,
        "pertes_evitees": pertes_evitees,
        "gain_net_client": gain_net_assurance,
        "est_favorable": est_favorable,
        "details_journaliers": sim_df
    }
