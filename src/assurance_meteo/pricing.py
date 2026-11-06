"""Module de tarification actuarielle de la prime d'assurance météorologique.
Conforme à la Section II [Département tarification] du sujet IMAFA 2026-2027.
"""

from typing import Dict
import pandas as pd
from .model import ProfilClient


def indemnites_annuelles_historiques(
    client: ProfilClient,
    historique_pluie: Dict[int, pd.Series]
) -> pd.DataFrame:
    """Calcule pour chaque année de l'historique :
    - Les indemnités annuelles totales versées (pertes subies L)
    - Le résultat annuel non assuré
    - Le nombre de jours d'intempéries indemnisés
    TODO: À implémenter par l'étudiant.
    """
    raise NotImplementedError("À compléter par l'étudiant.")


def calculer_prime_assurance(
    client: ProfilClient,
    historique_pluie: Dict[int, pd.Series],
    coeff_securite: float = 0.15,
    taux_frais: float = 0.10
) -> Dict[str, float]:
    """Calcule la tarification annuelle d'assurance prospective :
    - Prime pure P_pure = E[L] (espérance des indemnités annuelles)
    - Chargement de sécurité = beta * sigma(L)
    - Chargement de gestion = alpha * P_pure
    - Prime totale P = P_pure + chargements
    TODO: À implémenter par l'étudiant.
    """
    raise NotImplementedError("À compléter par l'étudiant.")
