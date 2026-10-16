"""Render REPORT.md -> docs/Technical_Report.pdf (max 3 pages) and
AI_DISCLOSURE.md -> docs/AI_Disclosure.pdf (1 page). Supports the small Markdown subset used there.
    python docs/build_pdfs.py
"""
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/Harshu3605/quantum-traffic-gridlock-qaoa"

F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("Body", F + "arial.ttf"))
pdfmetrics.registerFont(TTFont("Bold", F + "arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Ital", F + "ariali.ttf"))
pdfmetrics.registerFont(TTFont("BoldItal", F + "arialbi.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "consola.ttf"))
pdfmetrics.registerFont(TTFont("Sym", F + "seguisym.ttf"))
registerFontFamily("Body", normal="Body", bold="Bold", italic="Ital", boldItalic="BoldItal")

INK, MUTED, ACCENT = colors.HexColor("#1f2933"), colors.HexColor("#5b6670"), colors.HexColor("#1d5fa8")
SOFT, LINE = colors.HexColor("#eef3f9"), colors.HexColor("#d5dde6")


def styles(base):
    return {
        "h1": ParagraphStyle("h1", fontName="Bold", fontSize=base + 6.5, leading=base + 9, textColor=INK, spaceAfter=2),
        "meta": ParagraphStyle("meta", fontName="Body", fontSize=base - 1, leading=base + 1.5, textColor=MUTED, spaceAfter=5),
        "h2": ParagraphStyle("h2", fontName="Bold", fontSize=base + 2, leading=base + 4, textColor=ACCENT,
                             spaceBefore=5, spaceAfter=2),
        "p": ParagraphStyle("p", fontName="Body", fontSize=base, leading=base * 1.32, textColor=INK, spaceAfter=3),
        "li": ParagraphStyle("li", fontName="Body", fontSize=base, leading=base * 1.32, textColor=INK,
                             leftIndent=10, bulletIndent=1, spaceAfter=1),
        "cell": ParagraphStyle("cell", fontName="Body", fontSize=base - 0.8, leading=(base - 0.8) * 1.25, textColor=INK),
    }


SYM = set("⊕⟩⌊⌋½₂ĉΠΣλσγβ≤≥≈−→×…∈⊆")


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = t.replace("\\|", "|")
    codes = []  # protect `code` spans from the emphasis/subscript rules

    def keep(m):
        codes.append(m.group(1))
        return f"@@{len(codes) - 1}@@"
    t = re.sub(r"`([^`]+)`", keep, t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", t)
    t = re.sub(r"\^\{([^}]*)\}", r"<super>\1</super>", t)
    t = re.sub(r"\^([A-Za-z0-9])", r"<super>\1</super>", t)
    # glyphs missing from Arial -> Segoe UI Symbol
    t = "".join(f"<font name='Sym'>{c}</font>" if c in "⊕⟩⌊⌋∈⊆₂↔" else c for c in t)
    return re.sub(r"@@(\d+)@@", lambda m: f"<font name='Mono'>{codes[int(m.group(1))]}</font>", t)


def table(lines, st, width):
    rows = [[c.strip() for c in re.split(r"(?<!\\)\|", l.strip())[1:-1]] for l in lines]
    rows = [r for r in rows if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    n = len(rows[0])
    first = 0.2 if rows[0][0] == "Area" else 0.46 if n == 3 else 0.28
    widths = [width * first] + [width * (1 - first) / (n - 1)] * (n - 1)
    data = [[Paragraph(("<b>%s</b>" if i == 0 else "%s") % inline(c), st["cell"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), SOFT), ("LINEBELOW", (0, 0), (-1, 0), 0.7, ACCENT),
                           ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    return t


def md_to_flow(md, st, width, meta):
    flow, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("# "):
            flow.append(Paragraph(inline(l[2:]), st["h1"]))
            flow.append(Paragraph(meta, st["meta"]))
        elif l.startswith("## "):
            flow.append(Paragraph(inline(l[3:]), st["h2"]))
        elif l.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            flow.append(table(block, st, width))
            flow.append(Spacer(1, 3))
            continue
        elif l.startswith("- "):
            flow.append(Paragraph(inline(l[2:]), st["li"], bulletText="•"))
        elif l.strip():
            para = [l]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"(#|\||- )", lines[i + 1]):
                i += 1
                para.append(lines[i])
            flow.append(Paragraph(inline(" ".join(para)), st["p"]))
        i += 1
    return flow


def footer(label):
    def f(c, doc):
        c.saveState()
        c.setFont("Body", 7.5)
        c.setFillColor(MUTED)
        c.drawString(16 * mm, 8 * mm, f"Quantum Traffic Gridlock — {label}  |  IBM Qiskit Fall Fest 2026, QC@IITI  |  {REPO}")
        c.drawRightString(194 * mm, 8 * mm, f"{doc.page}")
        c.restoreState()
    return f


def render(src, out, label, base, max_pages, meta):
    md = open(os.path.join(ROOT, src), encoding="utf-8").read()
    st = styles(base)
    width = A4[0] - 32 * mm
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=13 * mm,
                            bottomMargin=14 * mm, title=md.splitlines()[0].lstrip("# "),
                            author="Quantum Traffic Gridlock team")
    doc.build(md_to_flow(md, st, width, meta), onFirstPage=footer(label), onLaterPages=footer(label))
    import pymupdf
    n = pymupdf.open(out).page_count
    print(f"{out}: {n} page(s) (limit {max_pages})")
    if n > max_pages:
        sys.exit(f"ERROR: {out} exceeds {max_pages} pages")


if __name__ == "__main__":
    team = os.environ.get("TEAM", "Team: Prakhar Keshniya, Harsh Sahu, Pranav Keshniya")
    meta = (f"{team}  ·  " if team else "") + f"Code, outputs and run instructions: {REPO}"
    render("REPORT.md", os.path.join(ROOT, "docs", "Technical_Report.pdf"), "Technical Report", 10, 3, meta)
    render("AI_DISCLOSURE.md", os.path.join(ROOT, "docs", "AI_Disclosure.pdf"), "AI-use Disclosure", 10.5, 1, meta)
