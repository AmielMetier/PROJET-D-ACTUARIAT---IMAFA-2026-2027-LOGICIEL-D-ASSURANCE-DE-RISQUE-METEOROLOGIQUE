"""Module d'analyse rétrospective et de représentation graphique.
Conforme à la Section IV [Département R&D] du sujet IMAFA 2026-2027.
"""

from typing import Dict, Optional, Tuple
import matplotlib.pyplot as plt
from .model import ProfilClient


def analyser_annee_retrospective(
    client: ProfilClient,
    annee: int,
    prime_a_priori: Optional[float] = None,
    cache_dir: str = "data"
) -> Dict:
    """Analyse a posteriori pour une année passée 'a' saisie :
    - R_{pl_bar, nass, i}^a : résultat annuel non assuré
    - R_{pl_bar, ass, i}^a : résultat annuel assuré garanti
    - P_{pl_bar, i}^a : prime qui aurait été calculée au début de l'année
    - Comparaison et conclusion (s'assurer aurait-il été favorable ?)
    TODO: À implémenter par l'étudiant.
    """
    raise NotImplementedError("À compléter par l'étudiant.")


def tracer_analyse_retrospective(
    bilan: Dict,
    fichier_sauvegarde: Optional[str] = None
) -> Tuple[plt.Figure, Tuple[plt.Axes, plt.Axes]]:
    """Génère la représentation graphique comparative demandée par le sujet :
    1. Évolution chronologique du résultat cumulé (R_nass vs R_ass et net de prime)
    2. Pluviométrie journalière avec niveau pivot pl_bar et seuil de perte pl*
    TODO: Tracer et retourner la figure matplotlib.
    """
    raise NotImplementedError("À compléter par l'étudiant.")
