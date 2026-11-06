"""Modélisation de l'activité économique du commerçant et du risque pluviométrique.
Conforme aux spécifications du sujet IMAFA 2026-2027 (Section I & II).
"""

from dataclasses import dataclass
from typing import Union
import numpy as np
import pandas as pd


@dataclass
class ProfilClient:
    """Représente le profil d'un commerçant assuré."""
    nom: str
    ville: str
    date_souscription: str
    ca_max: float        # Chiffre d'affaires journalier maximum (CA)
    couts_fixes: float   # Coûts fixes journaliers (Cf)
    pluie_pivot: float   # Niveau de pluie journalier pivot en mm (pl_bar)

    @property
    def seuil_perte(self) -> float:
        """Seuil pluviométrique pl* (en mm) à partir duquel le résultat journalier devient négatif.
        TODO: Calculer pl* = pl_bar * (1 - Cf / CA)
        """
        raise NotImplementedError("À compléter par l'étudiant.")

    def facteur_ca(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Calcule le facteur multiplicatif f_t^{pl} du CA en cas de pluie pl_t.
        TODO:
        - 1 si pl <= 0
        - (pl_bar - pl) / pl_bar si 0 < pl < pl_bar
        - 0 si pl >= pl_bar
        """
        raise NotImplementedError("À compléter par l'étudiant.")

    def chiffre_affaires_journalier(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Calcule le chiffre d'affaires CA_t^{pl} à la date t.
        TODO: f_t^{pl} * CA
        """
        raise NotImplementedError("À compléter par l'étudiant.")

    def resultat_journalier(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Calcule le résultat journalier non assuré R_t^{pl} = CA_t^{pl} - Cf.
        TODO: CA_t^{pl} - Cf
        """
        raise NotImplementedError("À compléter par l'étudiant.")

    def indemnite_journaliere(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Indemnité versée par l'assurance pour garantir R >= 0.
        TODO: I_t = max(0, -R_t^{pl})
        """
        raise NotImplementedError("À compléter par l'étudiant.")

    def resultat_assure_journalier(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Résultat garanti avec assurance (avant prime) : R_ass = max(0, R_t^{pl}).
        TODO: max(0, R_t^{pl})
        """
        raise NotImplementedError("À compléter par l'étudiant.")


def simulation_activite_journaliere(client: ProfilClient, series_pluie: pd.Series) -> pd.DataFrame:
    """Calcule l'ensemble des grandeurs journalières pour une série de pluie donnée.
    TODO: Renvoyer un DataFrame contenant :
    - 'pluie_mm'
    - 'facteur_ca'
    - 'ca_journalier'
    - 'resultat_non_assure'
    - 'indemnite_assurance'
    - 'resultat_assure_brut'
    - 'jour_a_perte'
    """
    raise NotImplementedError("À compléter par l'étudiant.")
