"""Module de tarification actuarielle de la prime d'assurance météorologique.
Conforme à la Section II [Département tarification] du sujet IMAFA 2026-2027.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from .model import ProfilClient


def indemnites_annuelles_historiques(
    client: ProfilClient,
    historique_pluie: Dict[int, pd.Series]
) -> pd.DataFrame:
    """Calcule pour chaque année de l'historique :
    - Le montant total des indemnités versées (pertes prises en charge L)
    - Le résultat annuel non assuré
    - Le nombre de jours de perte
    """
    records = []
    for annee, serie in historique_pluie.items():
        if len(serie) < 300:
            continue
        indemnites = client.indemnite_journaliere(serie.values)
        res_non_ass = client.resultat_journalier(serie.values)
        perte_totale = float(np.sum(indemnites))
        res_total = float(np.sum(res_non_ass))
        nb_jours_perte = int(np.sum(indemnites > 0))

        records.append({
            "annee": annee,
            "perte_totale": perte_totale,
            "resultat_non_assure": res_total,
            "nb_jours_perte": nb_jours_perte,
            "pluie_totale_mm": float(serie.sum()),
        })

    return pd.DataFrame(records).sort_values("annee").reset_index(drop=True)


def calculer_prime_assurance(
    client: ProfilClient,
    historique_pluie: Dict[int, pd.Series],
    coeff_securite: float = 0.15,
    taux_frais: float = 0.10,
    annee_courante: Optional[int] = None
) -> Dict[str, float]:
    """Calcule la prime d'assurance annuelle prospective :
    - Prime pure (E[L]) : espérance mathématique des indemnités annuelles
    - Chargement de sécurité (beta * sigma(L)) : marge de prudence pour volatilité climatique
    - Chargement pour frais (alpha * E[L]) : gestion de contrat et distribution
    - Prime commerciale finale P = P_pure + m_sec + m_frais
    """
    df_hist = indemnites_annuelles_historiques(client, historique_pluie)
    if df_hist.empty:
        raise ValueError("L'historique pluviométrique fourni est vide ou insuffisant.")

    pertes = df_hist["perte_totale"].values
    prime_pure = float(np.mean(pertes))
    ecart_type = float(np.std(pertes, ddof=1)) if len(pertes) > 1 else 0.0

    chargement_securite = coeff_securite * ecart_type
    chargement_frais = taux_frais * prime_pure
    prime_totale = prime_pure + chargement_securite + chargement_frais

    return {
        "prime_pure": round(prime_pure, 2),
        "chargement_securite": round(chargement_securite, 2),
        "chargement_frais": round(chargement_frais, 2),
        "prime_totale": round(prime_totale, 2),
        "ecart_type_pertes": round(ecart_type, 2),
        "perte_minimale_historique": round(float(np.min(pertes)), 2),
        "perte_maximale_historique": round(float(np.max(pertes)), 2),
        "nb_jours_sinistre_moyen": round(float(df_hist["nb_jours_perte"].mean()), 1),
        "nb_annees_observees": int(len(df_hist)),
    }
