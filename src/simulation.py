"""
Module de calculs et de modélisation journalière des flux financiers du commerçant.
Implémente fidèlement les formules du sujet de projet.
"""

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np
import pandas as pd


@dataclass
class ClientProfile:
    """Informations de souscription du commerçant."""
    ca_max: float        # Chiffre d'affaires journalier maximum (CA)
    cf: float            # Coûts fixes journaliers (Cf), avec CA > Cf
    pl_pivot: float      # Niveau de pluie journalier pivot en mm (pl_bar)
    city: str            # Ville de localisation
    subscription_date: str # Date de souscription (YYYY-MM-DD)

    def __post_init__(self):
        if self.ca_max <= self.cf:
            raise ValueError("Le chiffre d'affaires maximal CA doit être strictement supérieur aux coûts fixes Cf.")
        if self.pl_pivot <= 0:
            raise ValueError("Le niveau pivot de pluie pl_bar doit être strictement positif.")


def compute_daily_impact(pl_t: float, profile: ClientProfile) -> Dict[str, float]:
    """
    Calcule pour une journée donnée avec pluviométrie pl_t:
    - f_pl: facteur multiplicatif du CA
    - ca_pl: chiffre d'affaires du jour
    - r_pl: résultat du jour sans assurance
    - indemnity: indemnité versée par l'assurance pour garantir un résultat >= 0
    - r_assure_brut: résultat garanti brut (>= 0)
    """
    pl_bar = profile.pl_pivot
    ca = profile.ca_max
    cf = profile.cf

    if pl_t >= pl_bar:
        f_pl = 0.0
        ca_pl = 0.0
        r_pl = -cf
    elif pl_t > 0:
        f_pl = (pl_bar - pl_t) / pl_bar
        ca_pl = f_pl * ca
        r_pl = ca_pl - cf
    else:  # pl_t == 0
        f_pl = 1.0
        ca_pl = ca
        r_pl = ca - cf

    # Indemnité garantissant un résultat >= 0:
    indemnity = max(0.0, -r_pl)
    r_assure_brut = max(0.0, r_pl)  # équivaut à r_pl + indemnity

    return {
        "pl_t": pl_t,
        "f_pl": f_pl,
        "ca_pl": ca_pl,
        "r_nass": r_pl,
        "indemnity": indemnity,
        "r_ass_brut": r_assure_brut,
    }


def simulate_year(precipitation_series: pd.Series, profile: ClientProfile) -> pd.DataFrame:
    """
    Simule une année complète (ou période) à partir d'une série de pluviométries journalières.
    """
    records = [compute_daily_impact(float(p), profile) for p in precipitation_series]
    df = pd.DataFrame(records)
    if hasattr(precipitation_series, "index"):
        df.index = precipitation_series.index
    return df
