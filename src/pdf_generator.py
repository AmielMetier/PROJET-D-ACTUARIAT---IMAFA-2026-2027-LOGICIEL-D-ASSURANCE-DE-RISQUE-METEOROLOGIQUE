"""
Module de génération de Devis Commercial (PDF).
Permet d'imprimer un devis officiel conforme aux exigences du sujet.
"""

import hashlib
from typing import Dict, Any, Optional
from io import BytesIO
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .simulation import ClientProfile
from .pricing import coverage_end
from .formatting import fmt_eur, fmt_num, fmt_pct

# Coordonnées de l'assureur imprimées sur le devis.
# Société fictive créée pour le projet : à adapter si le groupe choisit un autre nom.
INSURER = {
    "name": "Météo Assur",
    "description": "Assureur fictif — Projet d'actuariat IMAFA 2026-2027",
    "product": "Contrat « Résultat Garanti Pluie » — assurance paramétrique annuelle",
}

PRIMARY = colors.HexColor("#2B6CB0")
DARK = colors.HexColor("#1A365D")
GREY = colors.HexColor("#4A5568")


def make_quote_ref(profile: ClientProfile, issued: Optional[date] = None) -> str:
    """
    Référence unique et reproductible du devis : date d'émission + empreinte des données client.
    Ex. DEV-20261113-3F9A2C
    """
    issued = issued or date.today()
    key = f"{profile.city}|{profile.ca_max}|{profile.cf}|{profile.pl_pivot}|{profile.subscription_date}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:6].upper()
    return f"DEV-{issued:%Y%m%d}-{digest}"


_CELL_STYLE = ParagraphStyle("Cell", fontName="Helvetica", fontSize=9, leading=11)


def _boxed_table(data, col_widths, header=False):
    # Les cellules de texte deviennent des paragraphes : un texte long (raison sociale, libellé)
    # passe à la ligne au lieu de déborder sur la case voisine.
    first_body_row = 1 if header else 0
    data = [
        [Paragraph(escape(c), _CELL_STYLE) if (i >= first_body_row and isinstance(c, str)) else c for c in row]
        for i, row in enumerate(data)
    ]
    table = Table(data, colWidths=col_widths)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    else:
        style.append(("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke))
    table.setStyle(TableStyle(style))
    return table


def generate_devis_pdf(
    profile: ClientProfile,
    pricing_res: Dict[str, Any],
    quote_ref: Optional[str] = None,
    station_label: Optional[str] = None,
    history_label: Optional[str] = None,
    client_name: str = "",
    company_name: str = "",
    issued: Optional[date] = None,
    correction_label: str = "",
) -> bytes:
    """
    Génère un devis d'assurance météorologique au format PDF.

    :param station_label: localité dont le point de grille météo a servi au tarif
    :param history_label: période d'historique utilisée pour tarifer (ex. "13/11/2010 au 12/11/2025 (15 années)")
    :param client_name: nom et prénom du souscripteur
    :param company_name: raison sociale du commerce
    """
    issued = issued or date.today()
    quote_ref = quote_ref or make_quote_ref(profile, issued)
    sub = date.fromisoformat(profile.subscription_date)
    end = coverage_end(sub)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=36,
                            title=f"Devis {quote_ref}", author=INSURER["name"])
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, textColor=GREY, leading=10)
    title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, textColor=DARK, spaceAfter=4)
    section_style = ParagraphStyle("SectionTitle", parent=styles["Heading2"], fontSize=13, textColor=PRIMARY,
                                   spaceBefore=10, spaceAfter=8)
    insurer_style = ParagraphStyle("Insurer", parent=normal, fontSize=9, leading=12)

    elements = []

    # En-tête : assureur à gauche, références du devis à droite
    header = Table([[
        Paragraph(
            f"<font size=14 color='#1A365D'><b>{escape(INSURER['name'])}</b></font><br/>"
            f"{escape(INSURER['description'])}<br/>{escape(INSURER['product'])}",
            insurer_style,
        ),
        Paragraph(
            f"<b>Devis n° {quote_ref}</b><br/>Émis le {issued:%d/%m/%Y}<br/>"
            f"Valable jusqu'au {date.fromordinal(issued.toordinal() + 30):%d/%m/%Y}",
            ParagraphStyle("Ref", parent=insurer_style, alignment=2),
        ),
    ]], colWidths=[330, 185])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, PRIMARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("DEVIS D'ASSURANCE RISQUE MÉTÉOROLOGIQUE", title_style))
    elements.append(Spacer(1, 6))

    # 1. Souscripteur
    elements.append(Paragraph("1. Souscripteur", section_style))
    client_data = [
        ["Nom du client :", client_name or "—", "Raison sociale :", company_name or "—"],
        ["Ville d'activité :", profile.city, "Date de prise d'effet :", f"{sub:%d/%m/%Y}"],
        ["CA max. journalier (CA) :", fmt_eur(profile.ca_max), "Coûts fixes journaliers (Cf) :", fmt_eur(profile.cf)],
        ["Pluie pivot journalière :", f"{fmt_num(profile.pl_pivot, 1)} mm", "Fin de couverture :", f"{end:%d/%m/%Y} (365 jours)"],
    ]
    elements.append(_boxed_table(client_data, [130, 125, 140, 120]))

    # 2. Garantie
    elements.append(Paragraph("2. Garantie", section_style))
    seuil_perte = profile.pl_pivot * (1 - profile.cf / profile.ca_max)
    elements.append(Paragraph(
        f"L'assurance garantit au souscripteur un <b>résultat d'exploitation journalier supérieur ou égal à 0 €</b> "
        f"chaque jour de la période de couverture. Dès que la pluie journalière dépasse <b>{fmt_num(seuil_perte)} mm</b>, "
        f"l'indemnité compense intégralement le déficit du jour (au plus {fmt_eur(profile.cf)} par jour, soit les coûts fixes). "
        f"Le déclenchement est paramétrique : il dépend uniquement de la pluie mesurée, sans expertise du sinistre.",
        normal,
    ))
    if station_label or history_label:
        base_text = "Tarif établi à partir des précipitations journalières de réanalyse (source : Open-Meteo / ERA5)"
        if station_label:
            base_text += f" au point de grille le plus proche de <b>{escape(station_label)}</b>"
        if history_label:
            base_text += f", sur les périodes de couverture équivalentes du {escape(history_label)}"
        elements.append(Spacer(1, 5))
        if correction_label:
            base_text += ". " + escape(correction_label.rstrip("."))
        elements.append(Paragraph(base_text + ".", normal))

    # 3. Tarif
    elements.append(Paragraph("3. Proposition tarifaire", section_style))
    beta = pricing_res.get("safety_beta")
    safety_label = "Chargement de sécurité"
    if beta is not None:
        safety_label += f" ({fmt_num(beta)} × écart-type des indemnités)"
    amount = ParagraphStyle("Amount", parent=_CELL_STYLE, alignment=2)
    bold = ParagraphStyle("Bold", parent=_CELL_STYLE, fontName="Helvetica-Bold")
    bold_amount = ParagraphStyle("BoldAmount", parent=bold, alignment=2)
    prem_data = [
        ["Composante", "Montant"],
        ["Prime pure technique (espérance des indemnités annuelles)",
         Paragraph(fmt_eur(pricing_res['pure_premium']), amount)],
        [safety_label, Paragraph(fmt_eur(pricing_res['safety_loading']), amount)],
        [f"Frais de gestion et marge ({fmt_pct(pricing_res['expense_rate'])} de la prime commerciale)",
         Paragraph(fmt_eur(pricing_res['expense_loading']), amount)],
        [Paragraph("Prime commerciale annuelle (hors taxes)", bold),
         Paragraph(fmt_eur(pricing_res['commercial_premium']), bold_amount)],
    ]
    t_prem = _boxed_table(prem_data, [370, 145], header=True)
    t_prem.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
    ]))
    elements.append(t_prem)
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Prime payable en une fois à la date de prise d'effet. Montant hors taxe sur les conventions d'assurance. "
        "Devis valable 30 jours à compter de sa date d'émission.",
        small,
    ))

    # 4. Signatures
    elements.append(Paragraph("4. Acceptation", section_style))
    sign_style = ParagraphStyle("Sign", parent=normal, fontSize=9, leading=13)
    signatures = Table([
        [Paragraph("<b>Pour l'assureur</b>", sign_style),
         Paragraph("<b>Le souscripteur</b><br/>(signature précédée de la mention « Bon pour accord »)", sign_style)],
        [Paragraph(f"{escape(INSURER['name'])}<br/>Nom du signataire :<br/><br/>Date :<br/><br/>Signature :", sign_style),
         Paragraph(f"{escape(client_name) or 'Nom :'}<br/>{escape(company_name)}<br/><br/>Date :<br/><br/>Signature :", sign_style)],
    ], colWidths=[257, 258], rowHeights=[None, 120])
    signatures.setStyle(TableStyle([
        ("BOX", (0, 0), (0, -1), 0.8, GREY),
        ("BOX", (1, 0), (1, -1), 0.8, GREY),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(signatures)

    doc.build(elements)
    return buffer.getvalue()
