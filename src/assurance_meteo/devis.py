"""Module d'édition et impression du devis d'assurance.
Conforme à la Section III [Département commercial] du sujet IMAFA 2026-2027.
"""

from typing import Dict
from .model import ProfilClient


def generer_devis(
    client: ProfilClient,
    tarif: Dict[str, float]
) -> str:
    """Génère un devis imprimable avec :
    - Données du client (nom, ville, CA, Cf, pl_bar, pl*, date)
    - Garantie assurée (garantie résultat positif R >= 0 sur 365 jours)
    - Tarif calculé (prime pure, chargements, prime commerciale)
    TODO: Mettre en forme et retourner la chaîne de caractères du devis.
    """
    raise NotImplementedError("À compléter par l'étudiant.")
