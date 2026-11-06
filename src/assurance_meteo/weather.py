"""Module de récupération des données météorologiques historiques et temps réel.
Conforme aux exigences 'Real time' et climatologie (Infoclimat, NOAA / NCEI, Open-Meteo).
"""

from typing import Dict, Tuple
import pandas as pd


def obtenir_coordonnees_ville(ville: str) -> Tuple[float, float]:
    """Retourne la latitude et la longitude d'une ville.
    TODO: Implémenter la résolution de la localisation (API de géocodage ou dictionnaire local).
    """
    raise NotImplementedError("À compléter par l'étudiant.")


def recuperer_pluviometrie_annuelle(
    ville: str,
    annee: int,
    cache_dir: str = "data"
) -> pd.Series:
    """Récupère la série temporelle journalière des précipitations (en mm) pour une année 'a'.
    TODO:
    - Vérifier si un cache CSV existe dans cache_dir.
    - Sinon, interroger l'API météorologique (ex: Open-Meteo, Infoclimat).
    - Retourner une pd.Series avec les dates en index et les mm de pluie en valeurs.
    """
    raise NotImplementedError("À compléter par l'étudiant.")


def recuperer_historique_pluviometrie(
    ville: str,
    annee_debut: int,
    annee_fin: int,
    cache_dir: str = "data"
) -> Dict[int, pd.Series]:
    """Récupère l'historique annuel de pluviométrie sur une plage d'années [annee_debut, annee_fin].
    TODO: Boucler sur les années et collecter les séries annuelles.
    """
    raise NotImplementedError("À compléter par l'étudiant.")


def recuperer_donnees_temps_reel(ville: str) -> pd.DataFrame:
    """Récupère les données/prévisions météo en temps réel juste avant les calculs.
    TODO: Requêter l'API météo en direct pour la ville sélectionnée.
    """
    raise NotImplementedError("À compléter par l'étudiant.")
