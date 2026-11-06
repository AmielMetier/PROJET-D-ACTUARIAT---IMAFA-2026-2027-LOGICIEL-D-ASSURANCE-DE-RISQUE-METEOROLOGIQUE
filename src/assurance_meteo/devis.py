"""Module d'édition et impression du devis d'assurance.
Conforme à la Section III [Département commercial] du sujet IMAFA 2026-2027.
"""

from datetime import datetime
from typing import Dict
from .model import ProfilClient


def generer_devis(
    client: ProfilClient,
    tarif: Dict[str, float],
    reference_devis: str = "DEV-2026-METEO-001"
) -> str:
    """Génère un devis commercial formel et imprimable pour le client."""
    date_jour = datetime.now().strftime("%d/%m/%Y")
    
    devis_texte = f"""
================================================================================
                    DEVIS D'ASSURANCE PARAMÉTRIQUE MÉTÉOROLOGIQUE
                         IMAFA ASSURANCES — PROJET ACTUARIAT
================================================================================
Référence devis       : {reference_devis}
Date d'émission       : {date_jour}
Date d'effet garantie : {client.date_souscription} (Durée : 365 jours)

1. INFORMATIONS DU SOUSCRIPTEUR
--------------------------------------------------------------------------------
Nom / Raison sociale         : {client.nom}
Ville d'exploitation         : {client.ville.capitalize()}
Chiffre d'affaires max (CA)  : {client.ca_max:,.2f} € / jour
Coûts fixes journaliers (Cf) : {client.couts_fixes:,.2f} € / jour
Pluie journalière pivot (pl̄) : {client.pluie_pivot:.1f} mm / jour
Seuil de déclenchement (pl*) : {client.seuil_perte:.2f} mm / jour
   -> Au-delà de {client.seuil_perte:.2f} mm de pluie, le résultat journalier devient négatif.

2. NATURE ET ÉTENDUE DE LA GARANTIE
--------------------------------------------------------------------------------
Objet de la couverture :
   L'assureur garantit au souscripteur un résultat d'exploitation journalier
   positif ou nul (R_t >= 0) sur l'ensemble des 365 jours de la période de couverture.
   
Indemnisation journalière :
   I_t = max(0, -R_t^{{pl}}) = max(0, Cf - f_t^{{pl}} * CA)
   Chaque journée déficitaire provoquée par un aléa pluviométrique (pl_t > pl*)
   donne lieu au versement d'une indemnité compensant intégralement la perte du jour.

3. DÉCOMPOSITION DU TARIF ANNUEL (DÉPARTEMENT TARIFICATION)
--------------------------------------------------------------------------------
Nombre d'années historiques analysées  : {tarif.get('nb_annees_observees', '-')} ans
Jours d'intempéries indemnisés (moy.)  : {tarif.get('nb_jours_sinistre_moyen', '-')} jours / an

Prime pure (E[Pertes annuelles])       : {tarif.get('prime_pure', 0.0):>10,.2f} €
Chargement de sécurité (écart-type)    : {tarif.get('chargement_securite', 0.0):>10,.2f} €
Frais de gestion et d'acquisition      : {tarif.get('chargement_frais', 0.0):>10,.2f} €
--------------------------------------------------------------------------------
TOTAL PRIME ANNUELLE TTC               : {tarif.get('prime_totale', 0.0):>10,.2f} €
================================================================================
Validité de l'offre : 30 jours à compter de la date d'émission.
Signature du client précédée de la mention 'Bon pour accord' :
"""
    return devis_texte.strip()
