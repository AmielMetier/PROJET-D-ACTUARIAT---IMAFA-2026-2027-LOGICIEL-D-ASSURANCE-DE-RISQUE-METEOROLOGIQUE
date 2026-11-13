"""
Module de génération de Devis Commercial (PDF).
Permet d'imprimer un devis officiel conforme aux exigences du sujet.
"""

import hashlib
from typing import Dict, Any, Optional
from io import BytesIO
from datetime import datetime, date
from xml.sax.saxutils import escape
from .simulation import ClientProfile
from .pricing import coverage_end


def make_quote_ref(profile: ClientProfile, issued: Optional[date] = None) -> str:
    """
    Référence unique et reproductible du devis : date d'émission + empreinte des données client.
    Ex. DEV-20261113-3F9A2C
    """
    issued = issued or date.today()
    key = f"{profile.city}|{profile.ca_max}|{profile.cf}|{profile.pl_pivot}|{profile.subscription_date}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:6].upper()
    return f"DEV-{issued:%Y%m%d}-{digest}"


def generate_devis_pdf(
    profile: ClientProfile,
    pricing_res: Dict[str, Any],
    quote_ref: Optional[str] = None,
    station_label: Optional[str] = None,
    history_label: Optional[str] = None,
) -> bytes:
    """
    Génère un devis d'assurance météorologique au format PDF.

    :param station_label: point de mesure météo retenu (nom officiel de la localité)
    :param history_label: période d'historique utilisée pour tarifer (ex. "2010 à 2025, 15 années")
    """
    quote_ref = quote_ref or make_quote_ref(profile)
    sub = date.fromisoformat(profile.subscription_date)
    end = coverage_end(sub)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        elements = []
        styles = getSampleStyleSheet()

        # Styles personnalisés
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=20
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=10,
            spaceAfter=10
        )

        elements.append(Paragraph("DEVIS D'ASSURANCE RISQUE MÉTÉOROLOGIQUE", title_style))
        elements.append(Paragraph(f"Référence du devis : <b>{quote_ref}</b> | Émis le {datetime.now().strftime('%d/%m/%Y')}", subtitle_style))
        elements.append(Spacer(1, 10))

        # Tableau des informations client
        elements.append(Paragraph("1. Informations du Souscripteur", section_style))
        client_data = [
            ["Ville d'activité :", profile.city, "Date de prise d'effet :", f"{sub:%d/%m/%Y}"],
            ["Chiffre d'Affaires Max Journalier (CA) :", f"{profile.ca_max:,.2f} €", "Coûts Fixes Journaliers (Cf) :", f"{profile.cf:,.2f} €"],
            ["Seuil Pluviométrique Pivot (pl_bar) :", f"{profile.pl_pivot:.1f} mm", "Fin de couverture :", f"{end:%d/%m/%Y} (365 jours)"],
        ]
        t_client = Table(client_data, colWidths=[150, 110, 150, 100])
        t_client.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(t_client)
        elements.append(Spacer(1, 15))

        # Tableau des garanties
        elements.append(Paragraph("2. Description des Garanties", section_style))
        seuil_perte = profile.pl_pivot * (1 - profile.cf / profile.ca_max)
        garanties_text = (
            f"L'assurance garantit au souscripteur un <b>résultat d'exploitation journalier supérieur ou égal à 0 €</b> "
            f"tout au long des 365 jours de la période de couverture.<br/>"
            f"Dès que la pluviométrie journalière dépasse le seuil critique de <b>{seuil_perte:.2f} mm</b>, "
            f"l'indemnité compense l'intégralité du déficit d'exploitation journalier (perte maximale couverte : {profile.cf:,.2f} €/jour)."
        )
        elements.append(Paragraph(garanties_text, styles["Normal"]))
        if station_label or history_label:
            base_text = "Tarif établi à partir des précipitations journalières réelles (source : Open-Meteo)"
            if station_label:
                base_text += f" mesurées à <b>{escape(station_label)}</b>"
            if history_label:
                base_text += f", sur les périodes de couverture équivalentes du {escape(history_label)}"
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(base_text + ".", styles["Normal"]))
        elements.append(Spacer(1, 15))

        # Tableau de tarification
        elements.append(Paragraph("3. Proposition Tarifaire", section_style))
        prem_data = [
            ["Composante", "Montant"],
            ["Prime Pure Technique (E[Indemnités])", f"{pricing_res['pure_premium']:,.2f} €"],
            ["Chargement de Sécurité Actuariel", f"{pricing_res['safety_loading']:,.2f} €"],
            ["Frais de Gestion & Marge Commerciale", f"{pricing_res['expense_loading']:,.2f} €"],
            ["Prime Commerciale Annuelle (hors taxes)", f"{pricing_res['commercial_premium']:,.2f} €"],
        ]
        t_prem = Table(prem_data, colWidths=[300, 210])
        t_prem.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
        ]))
        elements.append(t_prem)
        elements.append(Spacer(1, 25))

        # Mention de souscription
        elements.append(Paragraph(
            "Prime payable en une fois à la date de prise d'effet. Montant hors taxe sur les conventions d'assurance. "
            "Devis valable 30 jours à compter de sa date d'émission. Bon pour accord :",
            styles["Italic"]
        ))
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    except ImportError:
        # Fallback textuel simple si reportlab n'est pas encore installé
        simple_text = f"""DEVIS ASSURANCE METEOROLOGIQUE - {quote_ref}
Ville : {profile.city}
Couverture : du {sub:%d/%m/%Y} au {end:%d/%m/%Y}
CA max: {profile.ca_max} EUR, Coûts fixes: {profile.cf} EUR, Pivot pluie: {profile.pl_pivot} mm
Prime Pure: {pricing_res['pure_premium']:.2f} EUR
Prime Commerciale Annuelle (hors taxes): {pricing_res['commercial_premium']:.2f} EUR
"""
        return simple_text.encode("utf-8")
