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

    def __post_init__(self):
        if self.ca_max <= self.couts_fixes:
            raise ValueError("Le chiffre d'affaires maximum CA doit être strictement supérieur aux coûts fixes Cf.")
        if self.pluie_pivot <= 0:
            raise ValueError("Le niveau de pluie pivot doit être strictement positif.")
        if self.couts_fixes < 0:
            raise ValueError("Les coûts fixes ne peuvent pas être négatifs.")

    @property
    def seuil_perte(self) -> float:
        """Seuil pluviométrique (en mm) à partir duquel le résultat journalier devient négatif.
        pl* = pl_bar * (1 - Cf / CA)
        """
        return self.pluie_pivot * (1.0 - self.couts_fixes / self.ca_max)

    def facteur_ca(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Calcule le facteur multiplicatif du CA f_t^{pl} en fonction de la pluviométrie pl_t."""
        pl_arr = np.asarray(pl, dtype=float)
        # f = (pl_bar - pl) / pl_bar pour 0 < pl < pl_bar, 0 si pl >= pl_bar, 1 si pl <= 0
        f = np.where(
            pl_arr >= self.pluie_pivot,
            0.0,
            np.where(
                pl_arr <= 0.0,
                1.0,
                (self.pluie_pivot - pl_arr) / self.pluie_pivot
            )
        )
        return float(f) if np.isscalar(pl) else f

    def chiffre_affaires_journalier(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Chiffre d'affaires à la date t (CA_t^{pl}).
        - CA si pl_t = 0
        - f_t^{pl} * CA si 0 < pl_t < pl_bar
        - 0 si pl_t >= pl_bar
        """
        f = self.facteur_ca(pl)
        ca = f * self.ca_max
        return float(ca) if np.isscalar(pl) else ca

    def resultat_journalier(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Résultat journalier à la date t non assuré (R_t^{pl} = CA_t^{pl} - Cf)."""
        ca = self.chiffre_affaires_journalier(pl)
        res = ca - self.couts_fixes
        return float(res) if np.isscalar(pl) else res

    def indemnite_journaliere(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Indemnité versée par l'assurance pour garantir un résultat positif ou nul (R >= 0).
        I_t = max(0, -R_t^{pl})
        """
        res = self.resultat_journalier(pl)
        indemnite = np.maximum(0.0, -np.asarray(res, dtype=float))
        return float(indemnite) if np.isscalar(pl) else indemnite

    def resultat_assure_journalier(self, pl: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Résultat garanti avec assurance (avant déduction de la prime annuelle) :
        R_ass,t = max(0, R_t^{pl}) >= 0
        """
        res = self.resultat_journalier(pl)
        res_ass = np.maximum(0.0, np.asarray(res, dtype=float))
        return float(res_ass) if np.isscalar(pl) else res_ass


def simulation_activite_journaliere(client: ProfilClient, series_pluie: pd.Series) -> pd.DataFrame:
    """Calcule l'ensemble des grandeurs journalières pour une série temporelle de pluie."""
    df = pd.DataFrame(index=series_pluie.index)
    df["pluie_mm"] = series_pluie.values
    df["facteur_ca"] = client.facteur_ca(df["pluie_mm"].values)
    df["ca_journalier"] = client.chiffre_affaires_journalier(df["pluie_mm"].values)
    df["resultat_non_assure"] = client.resultat_journalier(df["pluie_mm"].values)
    df["indemnite_assurance"] = client.indemnite_journaliere(df["pluie_mm"].values)
    df["resultat_assure_brut"] = client.resultat_assure_journalier(df["pluie_mm"].values)
    df["jour_a_perte"] = df["resultat_non_assure"] < 0
    return df
