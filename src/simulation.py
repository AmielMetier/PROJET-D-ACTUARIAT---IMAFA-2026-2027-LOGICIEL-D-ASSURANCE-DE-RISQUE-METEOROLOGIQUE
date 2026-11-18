"""
Module de calculs et de modélisation journalière des flux financiers du commerçant.
Implémente fidèlement les formules du sujet de projet.
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import pandas as pd

# Noms des jours de la semaine, dans l'ordre de pandas (lundi = 0)
WEEKDAYS_FR = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")


@dataclass
class ClientProfile:
    """Informations de souscription du commerçant."""
    ca_max: float        # Chiffre d'affaires journalier maximum (CA)
    cf: float            # Coûts fixes journaliers (Cf), avec CA > Cf
    pl_pivot: float      # Niveau de pluie journalier pivot en mm (pl_bar)
    city: str            # Ville de localisation
    subscription_date: str # Date de souscription (YYYY-MM-DD)
    # Jours de fermeture hebdomadaire (0 = lundi ... 6 = dimanche). Un jour fermé ne fait ni chiffre
    # d'affaires ni coûts fixes et n'est pas couvert : Cf s'entend alors par jour d'ouverture.
    closed_weekdays: Tuple[int, ...] = ()

    def __post_init__(self):
        self.closed_weekdays = tuple(sorted(set(int(d) for d in self.closed_weekdays)))
        if any(d < 0 or d > 6 for d in self.closed_weekdays):
            raise ValueError("Les jours de fermeture sont numérotés de 0 (lundi) à 6 (dimanche).")
        if len(self.closed_weekdays) == 7:
            raise ValueError("Le commerce doit être ouvert au moins un jour par semaine.")
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


CLOSED_DAY = {"f_pl": 0.0, "ca_pl": 0.0, "r_nass": 0.0, "indemnity": 0.0, "r_ass_brut": 0.0}


def open_days_count(start, days: int, profile: ClientProfile) -> int:
    """Nombre de jours d'ouverture parmi les `days` jours qui commencent le `start`."""
    dates = pd.date_range(pd.Timestamp(start), periods=days, freq="D")
    return int((~dates.dayofweek.isin(profile.closed_weekdays)).sum())


def simulate_year(precipitation_series: pd.Series, profile: ClientProfile) -> pd.DataFrame:
    """
    Simule une année complète (ou période) à partir d'une série de pluviométries journalières.
    Si le commerce a des jours de fermeture, la série doit être indexée par date : un jour fermé
    ne produit ni chiffre d'affaires, ni coûts fixes, ni indemnité.
    """
    closed = None
    if profile.closed_weekdays:
        if not isinstance(precipitation_series.index, pd.DatetimeIndex):
            raise ValueError("Des jours de fermeture sont définis : la série de pluie doit être indexée par date.")
        closed = precipitation_series.index.dayofweek.isin(profile.closed_weekdays)

    records = []
    for i, p in enumerate(precipitation_series):
        if closed is not None and closed[i]:
            records.append({"pl_t": float(p), **CLOSED_DAY})
        else:
            records.append(compute_daily_impact(float(p), profile))
    df = pd.DataFrame(records)
    df["open"] = True if closed is None else ~closed
    df.index = precipitation_series.index
    return df
