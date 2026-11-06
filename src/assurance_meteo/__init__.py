"""Package d'assurance et tarification de risque météorologique.
Projet d'Actuariat IMAFA 2026-2027 - Polytech Nice Sophia.
"""

from .model import ProfilClient, simulation_activite_journaliere
from .pricing import calculer_prime_assurance
from .weather import recuperer_pluviometrie_annuelle, recuperer_historique_pluviometrie
from .devis import generer_devis
from .retrospective import analyser_annee_retrospective

__all__ = [
    "ProfilClient",
    "simulation_activite_journaliere",
    "calculer_prime_assurance",
    "recuperer_pluviometrie_annuelle",
    "recuperer_historique_pluviometrie",
    "generer_devis",
    "analyser_annee_retrospective",
]
