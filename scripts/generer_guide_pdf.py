"""
Génère docs/USER_GUIDE.pdf à partir de docs/USER_GUIDE.md (captures et formules comprises).

Usage, depuis la racine du projet :
    pip install -r requirements-dev.txt
    python scripts/generer_guide_pdf.py

Le PDF est imprimé par Microsoft Edge (installé d'office sous Windows) ou, à défaut, par le
Chromium de Playwright (`python -m playwright install chromium`). Les formules sont rendues
par KaTeX, chargé depuis un CDN : une connexion Internet est nécessaire.
"""

import re
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "USER_GUIDE.md"
TARGET = ROOT / "docs" / "USER_GUIDE.pdf"
TMP_HTML = ROOT / "docs" / "_user_guide_impression.html"

KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1f2933; }
h1 { font-size: 22pt; color: #1A365D; margin: 0 0 4pt; }
h2 { font-size: 14pt; color: #2B6CB0; margin: 0 0 10pt; }
h3 { font-size: 14pt; color: #1A365D; border-bottom: 1.5px solid #2B6CB0; padding-bottom: 3pt; margin-top: 18pt; }
h4 { font-size: 11.5pt; color: #2B6CB0; margin: 14pt 0 4pt; }
h5 { font-size: 10.5pt; margin: 10pt 0 2pt; }
h3, h4, h5 { break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: #2B6CB0; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: #f1f5f9; padding: 0 3px; border-radius: 3px; }
pre { background: #f1f5f9; padding: 8px 10px; border-radius: 4px; break-inside: avoid; }
pre code { padding: 0; background: none; }
blockquote { margin: 8pt 0; padding: 4pt 10pt; border-left: 3px solid #2B6CB0; background: #f5f8fc; color: #334155; }
table { border-collapse: collapse; margin: 8pt 0; break-inside: avoid; }
th, td { border: 1px solid #cbd5e1; padding: 3pt 7pt; text-align: left; }
th { background: #EDF2F7; }
img { max-width: 100%; border: 1px solid #e2e8f0; }
img[align="right"] { float: right; margin: 0 0 10pt 14pt; }
blockquote { overflow: hidden; }
p[align="center"] { text-align: center; margin: 4pt 0; break-inside: avoid; }
p[align="center"] em { font-size: 9pt; color: #52606d; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 14pt 0; }
.katex-display { margin: 6pt 0; }
"""


def protect_math(text):
    """Met les formules de côté pour que Markdown ne touche pas aux _ et * qu'elles contiennent."""
    formulas = []

    def keep(match):
        formulas.append(match.group(0))
        return f"@@MATH{len(formulas) - 1}@@"

    text = re.sub(r"\$\$.+?\$\$", keep, text, flags=re.S)
    text = re.sub(r"(?<![\\$])\$(?!\s)[^$\n]+?(?<!\s)\$", keep, text)
    return text, formulas


LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s")


def normalize_lists(text):
    """
    Adapte la syntaxe GitHub à Python-Markdown, plus strict :
    - une liste doit être précédée d'une ligne vide ;
    - les sous-listes et suites d'items sont indentées de 4 espaces (et non 2 ou 3).
    """
    out, in_code = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_code = not in_code
        if not in_code:
            match = re.match(r"^ {1,3}(\S.*)$", line)
            if match:
                line = "    " + match.group(1)
            prev = out[-1] if out else ""
            if (LIST_ITEM.match(line) and not line.startswith("    ")
                    and prev.strip() and not LIST_ITEM.match(prev) and not prev.startswith("    ")):
                out.append("")
        out.append(line)
    return "\n".join(out)


def build_html():
    text, formulas = protect_math(normalize_lists(SOURCE.read_text(encoding="utf-8")))
    body = markdown.markdown(text, extensions=["extra", "sane_lists"])
    for i, formula in enumerate(formulas):
        body = body.replace(f"@@MATH{i}@@", formula.replace("&", "&amp;").replace("<", "&lt;"))
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Manuel d'utilisation — Logiciel d'assurance de risque météorologique</title>
<link rel="stylesheet" href="{KATEX}/katex.min.css">
<script src="{KATEX}/katex.min.js"></script>
<script src="{KATEX}/contrib/auto-render.min.js"></script>
<style>{CSS}</style></head><body>{body}
<script>
renderMathInElement(document.body, {{
  delimiters: [{{left: "$$", right: "$$", display: true}}, {{left: "$", right: "$", display: false}}],
  throwOnError: false
}});
Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => {{ i.onload = i.onerror = r; }})))
  .then(() => document.fonts.ready).then(() => document.body.dataset.ready = "1");
</script></body></html>"""


def main():
    TMP_HTML.write_text(build_html(), encoding="utf-8")
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="msedge")
            except Exception:
                browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(TMP_HTML.as_uri())
            page.wait_for_selector("body[data-ready='1']", timeout=60_000)
            page.pdf(
                path=str(TARGET),
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=(
                    "<div style='font-size:8px;color:#888;width:100%;text-align:center;'>"
                    "Logiciel d'assurance de risque météorologique — Manuel d'utilisation — "
                    "page <span class='pageNumber'></span> / <span class='totalPages'></span></div>"
                ),
                margin={"top": "18mm", "bottom": "20mm", "left": "16mm", "right": "16mm"},
            )
            browser.close()
    finally:
        TMP_HTML.unlink(missing_ok=True)
    print(f"PDF généré : {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
