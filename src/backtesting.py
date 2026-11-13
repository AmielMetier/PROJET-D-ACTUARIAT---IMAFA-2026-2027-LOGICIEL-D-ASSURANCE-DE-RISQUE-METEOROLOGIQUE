"""
Module d'Analyse Rétrospective (Département R&D).
Compare pour une année 'a' quelconque dans le passé:
- R_nass (Résultat annuel non assuré)
- R_ass (Résultat annuel protégé par l'assurance)
- P_a (Tarif annuel calculé a priori)
- R_net = R_ass - P_a (Résultat annuel net de la prime)
"""

from typing import Dict, Any, List
import pandas as pd
from .simulation import ClientProfile, simulate_year
from .pricing import price_contract_historical


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
    # La prime est payée en une fois à la souscription (début d'année) : elle pèse dès le premier jour
    sim_df["cum_r_net"] = sim_df["cum_r_ass"] - annual_premium

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


def run_multi_year_backtest(
    calendar_periods: Dict[int, Dict[str, Any]],
    profile: ClientProfile,
    years: List[int],
    hist_years: int,
    safety_beta: float,
    expense_rate: float,
) -> Dict[str, Any]:
    """
    Rejoue le contrat sur plusieurs années passées, chacune tarifée a priori.

    Pour chaque année a : la prime P_a est calculée au 1er janvier de a avec les `hist_years`
    années complètes qui précèdent (et elles seules), puis comparée aux indemnités réellement
    versées pendant a. C'est le point de vue de l'assureur comme celui du client.

    :param calendar_periods: sortie de split_into_coverage_periods en années civiles (1er janvier)
    :param years: années à rejouer
    :return: {"table": DataFrame par année, "summary": indicateurs agrégés}
    """
    rows = []
    for a in years:
        if a not in calendar_periods:
            continue
        prior_years = [y for y in sorted(calendar_periods) if a - hist_years <= y < a]
        if len(prior_years) < 2:
            continue  # pas assez d'historique pour tarifer cette année
        pricing = price_contract_historical(
            {y: calendar_periods[y]["precipitation"] for y in prior_years},
            profile,
            safety_beta=safety_beta,
            expense_rate=expense_rate,
        )
        sim_df = simulate_year(calendar_periods[a]["precipitation"], profile)
        premium = pricing["commercial_premium"]
        indemnities = float(sim_df["indemnity"].sum())
        rows.append({
            "annee": a,
            "prime": premium,
            "prime_pure": pricing["pure_premium"],
            "indemnites": indemnities,
            "r_nass": float(sim_df["r_nass"].sum()),
            "r_ass": float(sim_df["r_ass_brut"].sum()),
            "r_net": float(sim_df["r_ass_brut"].sum()) - premium,
            "gain_client": indemnities - premium,
            "favorable": indemnities > premium,
            "annees_historique": len(prior_years),
        })

    table = pd.DataFrame(rows)
    if table.empty:
        return {"table": table, "summary": None}

    total_premiums = float(table["prime"].sum())
    total_indemnities = float(table["indemnites"].sum())
    summary = {
        "n_years": len(table),
        "total_premiums": total_premiums,
        "total_indemnities": total_indemnities,
        # Ratio sinistres / primes (S/P) : < 100 % => le produit est rentable pour l'assureur
        "loss_ratio": total_indemnities / total_premiums if total_premiums > 0 else float("nan"),
        "share_favorable": float(table["favorable"].mean()),
        "cumulative_client_gain": float(table["gain_client"].sum()),
    }
    return {"table": table, "summary": summary}
