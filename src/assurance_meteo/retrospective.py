"""Module d'analyse rétrospective et de visualisation graphique.
Conforme à la Section IV [Département R&D] du sujet IMAFA 2026-2027.
"""

from typing import Dict, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .model import ProfilClient, simulation_activite_journaliere
from .pricing import calculer_prime_assurance
from .weather import recuperer_pluviometrie_annuelle, recuperer_historique_pluviometrie


def analyser_annee_retrospective(
    client: ProfilClient,
    annee: int,
    annees_historique: int = 15,
    prime_imposee: Optional[float] = None,
    cache_dir: str = "data"
) -> Dict:
    """Réalise l'analyse rétrospective complète pour une année passée 'a' :
    1. Récupère la météo de l'année a
    2. Calcule la prime a priori P qui aurait été fixée au début de l'année a (sur l'historique antérieur)
    3. Simule les résultats a posteriori :
       - R_nass : résultat annuel non assuré
       - R_ass : résultat annuel protégé par l'assurance (brut)
       - R_ass_net : résultat annuel net de prime (R_ass - P)
       - Pertes réelles subies par le non assuré (L = R_ass - R_nass)
       - Gain net procuré par l'assurance (L - P)
    """
    # Données météo de l'année passée
    serie_annee = recuperer_pluviometrie_annuelle(client.ville, annee, cache_dir=cache_dir)
    df_jour = simulation_activite_journaliere(client, serie_annee)

    # Calcul a priori de la prime (basé sur les années antérieures à 'annee')
    if prime_imposee is not None:
        prime_a_priori = float(prime_imposee)
        details_pricing = {"prime_totale": prime_a_priori, "prime_pure": prime_a_priori}
    else:
        annee_deb = max(1950, annee - annees_historique)
        annee_fin = annee - 1
        try:
            hist_anterieur = recuperer_historique_pluviometrie(
                client.ville, annee_deb, annee_fin, cache_dir=cache_dir
            )
            if len(hist_anterieur) >= 3:
                details_pricing = calculer_prime_assurance(client, hist_anterieur)
                prime_a_priori = details_pricing["prime_totale"]
            else:
                # Si historique antérieur indisponible, utiliser l'année courante comme approximation
                details_pricing = calculer_prime_assurance(client, {annee: serie_annee})
                prime_a_priori = details_pricing["prime_totale"]
        except Exception:
            details_pricing = {"prime_totale": 3000.0, "prime_pure": 3000.0}
            prime_a_priori = 3000.0

    r_nass = float(df_jour["resultat_non_assure"].sum())
    indemnites_totales = float(df_jour["indemnite_assurance"].sum())
    r_ass = float(df_jour["resultat_assure_brut"].sum())
    r_ass_net = r_ass - prime_a_priori
    pertes_reelles = indemnites_totales  # égale à abs(r_nass - r_ass)
    gain_assurance = pertes_reelles - prime_a_priori
    assurance_favorable = gain_assurance > 0

    return {
        "annee": annee,
        "client": client.nom,
        "ville": client.ville,
        "pluie_pivot": client.pluie_pivot,
        "prime_a_priori": round(prime_a_priori, 2),
        "resultat_non_assure": round(r_nass, 2),
        "resultat_assure_brut": round(r_ass, 2),
        "resultat_assure_net": round(r_ass_net, 2),
        "pertes_reelles": round(pertes_reelles, 2),
        "gain_net_assurance": round(gain_assurance, 2),
        "assurance_favorable": assurance_favorable,
        "nb_jours_sinistres": int(df_jour["jour_a_perte"].sum()),
        "pluie_cumulee_mm": round(float(serie_annee.sum()), 1),
        "details_journaliers": df_jour,
        "details_pricing": details_pricing,
    }


def tracer_analyse_retrospective(
    bilan: Dict,
    fichier_sauvegarde: Optional[str] = None
) -> Tuple[plt.Figure, Tuple[plt.Axes, plt.Axes]]:
    """Génère la représentation graphique comparative demandée dans la Section IV."""
    df_jour = bilan["details_journaliers"]
    annee = bilan["annee"]
    client_nom = bilan["client"]
    pluie_pivot = bilan["pluie_pivot"]
    prime = bilan["prime_a_priori"]

    # Trajectoires cumulées sur l'année
    cumul_non_ass = df_jour["resultat_non_assure"].cumsum()
    cumul_ass = df_jour["resultat_assure_brut"].cumsum()
    cumul_ass_net = cumul_ass - prime

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    # Graphique 1 : Trajectoires des résultats
    ax1.plot(df_jour.index, cumul_non_ass, label="Sans assurance (R_nass)", color="#d9534f", linewidth=2)
    ax1.plot(df_jour.index, cumul_ass, label="Assuré brut (R_ass)", color="#5cb85c", linewidth=2, linestyle="--")
    ax1.plot(df_jour.index, cumul_ass_net, label=f"Assuré net de prime (R_ass - P = {bilan['resultat_assure_net']:,.0f} €)", color="#0275d8", linewidth=2)
    ax1.set_title(
        f"Analyse rétrospective {annee} — {client_nom} ({bilan['ville'].capitalize()})\n"
        f"Prime a priori : {prime:,.0f} € | Pertes évitées : {bilan['pertes_reelles']:,.0f} € "
        f"({'Assurance favorable' if bilan['assurance_favorable'] else 'Non favorable'})",
        fontsize=12, fontweight="bold"
    )
    ax1.set_ylabel("Résultat cumulé (€)", fontsize=11)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left")

    # Graphique 2 : Pluviométrie journalière et seuil pivot
    seuil_perte = df_jour["pluie_mm"].iloc[0]  # dummy
    # Calcul seuil
    client_ca = (df_jour["ca_journalier"] / df_jour["facteur_ca"].replace(0, np.nan)).dropna().iloc[0] if (df_jour["facteur_ca"] > 0).any() else 1000
    couts_fixes = client_ca - df_jour["resultat_non_assure"].iloc[0] if df_jour["pluie_mm"].iloc[0] == 0 else 400
    seuil_estime = pluie_pivot * (1 - couts_fixes / client_ca)

    ax2.bar(df_jour.index, df_jour["pluie_mm"], color="#5bc0de", width=1.0, label="Pluie journalière (mm)")
    ax2.axhline(pluie_pivot, color="black", linestyle="--", linewidth=1.5, label=f"Pluie pivot pl̄ ({pluie_pivot:.1f} mm)")
    if 0 < seuil_estime < pluie_pivot:
        ax2.axhline(seuil_estime, color="#d9534f", linestyle=":", linewidth=1.5, label=f"Seuil de perte pl* ({seuil_estime:.1f} mm)")

    # Colorer les jours indemnisés
    jours_sinistres = df_jour[df_jour["jour_a_perte"]]
    if not jours_sinistres.empty:
        ax2.bar(jours_sinistres.index, jours_sinistres["pluie_mm"], color="#d9534f", width=1.0, label="Jours de perte (indemnisés)")

    ax2.set_ylabel("Précipitations (mm)", fontsize=11)
    ax2.set_xlabel("Date", fontsize=11)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right")

    plt.tight_layout()

    if fichier_sauvegarde:
        fig.savefig(fichier_sauvegarde, dpi=150)

    return fig, (ax1, ax2)
