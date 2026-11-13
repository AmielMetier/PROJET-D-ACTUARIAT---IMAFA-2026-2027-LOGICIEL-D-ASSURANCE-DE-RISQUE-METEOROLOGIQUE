"""
Formatage des nombres à la française (espace pour les milliers, virgule décimale).
"""

# Espace insécable : évite qu'un montant soit coupé en fin de ligne.
# (L'espace fine U+202F serait plus typographique, mais la police standard des PDF ne la contient pas.)
THIN_NBSP = " "


def fmt_num(value: float, decimals: int = 2) -> str:
    """12478.666 -> '12 478,67'"""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", THIN_NBSP).replace(".", ",")


def fmt_eur(value: float, decimals: int = 2, signed: bool = False) -> str:
    """12478.666 -> '12 478,67 €' ; signed=True ajoute le signe + aux montants positifs."""
    text = fmt_num(value, decimals)
    if signed and value > 0:
        text = "+" + text
    return f"{text} €"


def fmt_pct(value: float, decimals: int = 0) -> str:
    """0.873 -> '87 %'"""
    return f"{fmt_num(value * 100, decimals)} %"
