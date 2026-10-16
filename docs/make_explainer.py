"""Builds docs/Quantum_Traffic_Explainer.pdf — a plain-language (Hinglish) explainer.
Numbers are read from outputs/ so the PDF always matches the latest run.
    python docs/make_explainer.py
"""
import json
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, Polygon
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
                                PageBreak)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "Quantum_Traffic_Explainer.pdf")

pdfmetrics.registerFont(TTFont("Body", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Mono", "C:/Windows/Fonts/consola.ttf"))
pdfmetrics.registerFont(TTFont("Ital", "C:/Windows/Fonts/ariali.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Body", normal="Body", bold="Bold", italic="Ital", boldItalic="Bold")

INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#5b6670")
ACCENT = colors.HexColor("#1d5fa8")
GREEN = colors.HexColor("#2e8b57")
RED = colors.HexColor("#c0392b")
SOFT = colors.HexColor("#eef3f9")
LINE = colors.HexColor("#d5dde6")

H1 = ParagraphStyle("h1", fontName="Bold", fontSize=22, leading=27, textColor=INK, spaceAfter=4)
SUB = ParagraphStyle("sub", fontName="Body", fontSize=10.5, leading=14, textColor=MUTED, spaceAfter=10)
H2 = ParagraphStyle("h2", fontName="Bold", fontSize=14, leading=18, textColor=ACCENT, spaceBefore=12, spaceAfter=5)
P = ParagraphStyle("p", fontName="Body", fontSize=10.5, leading=15, textColor=INK, spaceAfter=5)
LI = ParagraphStyle("li", parent=P, leftIndent=12, bulletIndent=2, spaceAfter=2)
BOX = ParagraphStyle("box", parent=P, fontSize=10.5, leading=15)
CAP = ParagraphStyle("cap", fontName="Body", fontSize=8.5, leading=11, textColor=MUTED, alignment=TA_CENTER)
CELL = ParagraphStyle("cell", fontName="Body", fontSize=9.5, leading=12, textColor=INK)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Bold")


def load():
    seeds = [json.load(open(os.path.join(ROOT, "outputs", "R", f"seed_{s}", "results.json"))) for s in range(5)]
    exp = json.load(open(os.path.join(ROOT, "outputs", "experiments", "experiments.json")))
    return seeds, exp


def bullets(items):
    return [Paragraph(t, LI, bulletText="•") for t in items]


def box(flow, bg=SOFT, border=ACCENT):
    t = Table([[flow]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, border),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def table(rows, widths, bold_rows=()):
    data = [[Paragraph(str(c), CELLB if (r == 0 or r in bold_rows) else CELL) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths])
    st = [("BACKGROUND", (0, 0), (-1, 0), SOFT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
          ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for r in bold_rows:
        st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#e8f4ec")))
    t.setStyle(TableStyle(st))
    return t


def road_diagram():
    d = Drawing(170 * mm, 62 * mm)
    W = 170 * mm
    y = 31 * mm
    # horizontal road
    d.add(Rect(0, y - 6 * mm, W, 12 * mm, fillColor=colors.HexColor("#dfe4ea"), strokeColor=None))
    for cx, name in ((45 * mm, "A"), (125 * mm, "B")):
        d.add(Rect(cx - 6 * mm, 0, 12 * mm, 62 * mm, fillColor=colors.HexColor("#dfe4ea"), strokeColor=None))
        d.add(Circle(cx, y, 9 * mm, fillColor=colors.white, strokeColor=ACCENT, strokeWidth=1.5))
        d.add(String(cx, y - 3.5 * mm, name, fontName="Bold", fontSize=16, fillColor=ACCENT, textAnchor="middle"))
        d.add(String(cx + 8 * mm, 56 * mm, "NS (1)", fontName="Body", fontSize=8, fillColor=MUTED))
    d.add(String(2 * mm, y + 8 * mm, "EW (0)", fontName="Body", fontSize=8, fillColor=MUTED))
    # transfer arrow A -> B
    d.add(Line(57 * mm, y + 13 * mm, 111 * mm, y + 13 * mm, strokeColor=GREEN, strokeWidth=2))
    d.add(Polygon([111 * mm, y + 15.5 * mm, 116 * mm, y + 13 * mm, 111 * mm, y + 10.5 * mm],
                  fillColor=GREEN, strokeColor=GREEN))
    d.add(String(85 * mm, y + 16 * mm, "A se nikli EW gaadiyon ka 60% agle slot mein B pahunchta hai",
                 fontName="Body", fontSize=8, fillColor=GREEN, textAnchor="middle"))
    return d


def cost_chart(vals):
    d = Drawing(170 * mm, 70 * mm)
    left, base, maxw = 62 * mm, 6 * mm, 100 * mm
    vmax = max(v for _, v, _ in vals)
    for i, (lab, v, col) in enumerate(vals):
        yy = base + (len(vals) - 1 - i) * 12 * mm
        d.add(String(left - 3 * mm, yy + 2.5 * mm, lab, fontName="Body", fontSize=9, fillColor=INK, textAnchor="end"))
        w = maxw * v / vmax
        d.add(Rect(left, yy, w, 8 * mm, fillColor=col, strokeColor=None))
        d.add(String(left + w + 2 * mm, yy + 2.5 * mm, f"{v:g}", fontName="Bold", fontSize=9, fillColor=INK))
    return d


def bits_example():
    d = Drawing(170 * mm, 24 * mm)
    bits = "11101010"
    x0 = 25 * mm
    for i, b in enumerate(bits):
        x = x0 + i * 14 * mm + (6 * mm if i >= 4 else 0)
        col = ACCENT if b == "1" else colors.HexColor("#e08a1e")
        d.add(Rect(x, 8 * mm, 12 * mm, 12 * mm, fillColor=col, strokeColor=None, rx=2, ry=2))
        d.add(String(x + 6 * mm, 12 * mm, b, fontName="Bold", fontSize=13, fillColor=colors.white, textAnchor="middle"))
        d.add(String(x + 6 * mm, 3 * mm, f"slot {i % 4 + 1}", fontName="Body", fontSize=7, fillColor=MUTED,
                     textAnchor="middle"))
    d.add(String(x0 + 27 * mm, 21.5 * mm, "Chauraha A", fontName="Bold", fontSize=9, fillColor=INK, textAnchor="middle"))
    d.add(String(x0 + 89 * mm, 21.5 * mm, "Chauraha B", fontName="Bold", fontSize=9, fillColor=INK, textAnchor="middle"))
    return d


def footer(c, doc):
    c.saveState()
    c.setFont("Body", 8)
    c.setFillColor(MUTED)
    c.drawString(20 * mm, 10 * mm, "Quantum Traffic Gridlock — aasaan bhasha mein  |  IBM Qiskit Fall Fest 2026, QC@IITI")
    c.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
    c.restoreState()


def build():
    seeds, exp = load()
    r0 = seeds[0]
    b = r0["baselines"]
    lifts = [s["qaoa_raw"]["lift"] for s in seeds]
    EQ = sum(s["qaoa_raw"]["E_Q"] for s in seeds) / 5
    enr = sum(s["qaoa_raw"]["enrichment"] for s in seeds) / 5
    popt = sum(s["qaoa_raw"]["p_optimal"] for s in seeds) / 5
    gs = exp["generalisation_summary"]
    Cs, Cr = b["exact_enumeration"]["cost"], b["uniform_random_expected"]["cost"]

    s = []
    s.append(Paragraph("Quantum Traffic Gridlock", H1))
    s.append(Paragraph("Quantum computer se traffic signal ka plan kaise banate hain — bilkul shuru se, "
                       "aasaan bhasha mein. Kisi ko bhi samjhane ke liye.", SUB))
    s.append(box(Paragraph(
        f"<b>Ek line mein:</b> Do jude hue traffic signals ka 4 slot ka plan banana tha. Humne traffic ke "
        f"niyamon se quantum computer ke samajhne layak formula (QUBO) banaya, aur quantum algorithm (QAOA) ne "
        f"4096 koshishon mein zyaadatar achhe plan nikaale. Average cost <b>{EQ:.0f}</b> aaya, jabki sabse "
        f"achha <b>{Cs:g}</b> aur bina soche (random) <b>{Cr:g}</b> hai.", BOX)))

    s.append(Paragraph("1. Problem kya hai?", H2))
    s.append(Paragraph("Ek sadak par do chauraahe hain, <b>A</b> aur <b>B</b>. A se nikli kuch gaadiyan aage "
                       "jaakar B par pahunchti hain. Har chauraahe par ek waqt mein sirf ek taraf hara signal "
                       "ho sakta hai:", P))
    s += bullets(["<b>NS</b> (North–South) — upar-neeche wali gaadiyan chalengi",
                  "<b>EW</b> (East–West) — daayein-baayein wali gaadiyan chalengi"])
    s.append(KeepTogether([road_diagram(), Paragraph("Chitra 1: do jude hue chauraahe (Scenario R mein link EW par hai)", CAP)]))
    s.append(Paragraph("Humein <b>4 time slots</b> (har slot 30 second) ka plan banana hai: har slot mein A par "
                       "kaunsa signal hara ho, aur B par kaunsa. <b>Mushkil yeh hai</b> ki A ka faisla B ko "
                       "prabhavit karta hai. A par EW hara kiya to woh gaadiyan agle slot mein B ki line badha "
                       "deti hain. Isliye dono ko alag-alag nahi, saath mein sochna padta hai.", P))

    s.append(Paragraph("2. Plan ko kaise likhte hain? — 8 bits", H2))
    s.append(Paragraph("Har slot ka faisla ek bit hai: <b>1 = NS hara</b>, <b>0 = EW hara</b>. "
                       "4 slot A ke + 4 slot B ke = <b>8 bits</b>.", P))
    s.append(KeepTogether([bits_example(), Paragraph("Chitra 2: plan 1110 | 1010 (neela = NS, narangi = EW). "
                                                     "Yahi Scenario R ka sabse achha plan hai.", CAP)]))
    s.append(Paragraph("8 bits se kul <b>2⁸ = 256</b> alag plan ban sakte hain. Inmein se sabse achha dhoondhna hai.", P))

    s.append(Paragraph("3. “Achha plan” kise kehte hain? — Cost", H2))
    s.append(Paragraph("Organisers ne ek official formula (<font name='Mono'>scorer.py</font>) diya hai. "
                       "<b>Jitni kam cost, utna achha plan.</b> Cost teen cheezon se banti hai:", P))
    s.append(table([["Hissa", "Matlab", "Saza (Scenario R)"],
                    ["Delay", "Har slot ke baad kitni gaadiyan abhi bhi line mein khadi hain", "har gaadi = 1"],
                    ["Overflow", "Line itni lambi ho gayi ki jagah (7 gaadi) se bahar nikal gayi", "har extra gaadi = 4"],
                    ["Switch", "Signal ek slot se agle slot mein badla", "har badlav = 0.5"]], [28, 100, 42]))
    s.append(Spacer(1, 4))
    s.append(Paragraph("Har slot mein hara signal zyada se zyada <b>5 gaadiyan</b> nikaal sakta hai. "
                       "Saari 256 plans valid hain, bas kuch mehenge hain.", P))

    s.append(Paragraph("4. Jab 256 hi plan hain to sab check kyon nahi karte?", H2))
    s.append(Paragraph("Kar sakte hain, aur tulna (comparison) ke liye hum karte bhi hain. Lekin is competition "
                       "ka maqsad yeh seekhna hai ki <b>quantum computer</b> aisi problem kaise solve karta hai. "
                       "Asli shehar mein hazaaron chauraahe hote hain, tab sab plan check karna namumkin hai "
                       "(2<super>1000</super> se bhi zyada plan). Yahaan chhoti problem par tareeka test ho raha hai. "
                       "PDF khud kehta hai: is size par quantum se fayde ki ummeed nahi hai.", P))

    s.append(Paragraph("5. Quantum computer ko problem kaise samjhate hain? — QUBO", H2))
    s.append(Paragraph("Quantum algorithm sirf ek khaas tarah ka formula samajhta hai, jise <b>QUBO</b> kehte hain. "
                       "Usmein sirf <b>akele bits</b> aur <b>do-do bits ke jode</b> ho sakte hain, teen ya zyada "
                       "ek saath nahi. Asli traffic cost isse zyada tedhi hai: line kabhi negative nahi hoti, aur "
                       "5 se zyada gaadiyan ek slot mein nahi nikal sakti.", P))
    s.append(Paragraph("Humne kya kiya:", P))
    s += bullets(["<b>Tod diya:</b> kul cost = har line (A-NS, A-EW, B-NS, B-EW) ki cost + signal badalne ki cost. "
                  "Yeh todna bilkul exact hai, official scorer se 256 × 40 plans par check kiya.",
                  "<b>Signal badalna</b> pehle se jode wala formula hai, use exactly rakha.",
                  "<b>Har line ki cost</b> ke liye sabse karib wala “jode-wala” formula banaya, jaise kisi tedhi "
                  "line ko sabse achhi seedhi line se approximate karna (maths mein: order-2 Walsh projection).",
                  "Yeh niyam har scenario par same chalta hai. Humne jawab pehle se dhoondhkar formula mein chhupaya "
                  "<b>nahi</b> hai (yeh competition mein mana hai)."])
    s.append(box(Paragraph(
        f"<b>Kitna sahi hai?</b> Scenario R par is formula ka sabse achha plan bilkul asli best plan hi nikla "
        f"(cost {b['qubo_exact_minimizer']['cost']:g}, galti 0%). 30 random scenarios mein average galti "
        f"{gs['qubo_regret_mean_pct']:.1f}%, aur sabse kharab case mein {gs['qubo_regret_max_pct']:.1f}%.", BOX)))

    s.append(Paragraph("6. QAOA kya karta hai? — Quantum hissa", H2))
    s.append(Paragraph("Socho 8 sikke hain, har sikka ek bit hai.", P))
    s += bullets(["<b>Shuru mein</b> saare sikke hawa mein ghoom rahe hain. Saare 256 plan ek saath, barabar chance "
                  "(quantum superposition).",
                  "<b>Fir do kaam baar-baar (4 baar, depth p = 4):</b> (a) <i>Cost step:</i> achhe plans ko thoda "
                  "dhakka do; (b) <i>Mix step:</i> plans ko aapas mein milao taaki naye achhe plan bhi mil sakein.",
                  "Kitna dhakka dena hai (angles), yeh ek normal computer <b>300 koshishon</b> ke andar seekhta hai. "
                  "Pehle 1 layer seekhte hain, fir usi se 2, 3, 4 layers banate hain (INTERP tareeka).",
                  "<b>Ant mein</b> circuit ko <b>4096 baar</b> chalakar dekhte hain ki kaunsa plan kitni baar aaya."])
    s.append(Paragraph("<b>Kaamyabi kab maane?</b> Jab achhe plans zyada baar niklein aur bure kam. Sirf ek baar best "
                       "plan mil jaana kaafi nahi hai, poore 4096 nateejon ka average achha hona chahiye.", P))

    vals = [("Random plan (average)", Cr, colors.HexColor("#b8c2cc")),
            ("Alternating (1010…)", b["best_alternating"]["cost"], colors.HexColor("#b8c2cc")),
            ("Greedy (lambi line ko hara)", b["greedy"]["cost"], colors.HexColor("#b8c2cc")),
            ("QAOA (4096 ka average)", round(EQ, 1), ACCENT),
            ("Sabse achha possible", Cs, GREEN)]
    s.append(KeepTogether([Paragraph("7. Nateeja — Scenario R", H2), cost_chart(vals), Paragraph("Chitra 3: cost (kam = behtar). QAOA ka average greedy se "
                                                       "behtar hai, lekin best tak nahi pahuncha.", CAP)]))
    s.append(Spacer(1, 4))
    s.append(table([["Metric", "Value", "Matlab"],
                    ["Lift", f"{min(lifts):.2f} – {max(lifts):.2f}",
                     "Random se best tak ka kitna faasla tay kiya (0 = random jaisa, 1 = perfect)"],
                    ["Elite enrichment", f"{enr:.1f}×", "Top 13 plans random ke mukable itne guna zyada baar aaye"],
                    ["Best plan kitni baar", f"{100 * popt:.1f}%", "4096 mein se itne % baar sabse achha plan (72) aaya"],
                    ["5 seeds par", "lagbhag same", "Nateeja stable hai, kismat se nahi aaya"]], [38, 30, 102]))

    s.append(Paragraph("8. Saath mein kya jaancha (baselines)", H2))
    s.append(table([["Tareeka", "Kya karta hai", "Cost (R)"],
                    ["Alternating", "Har slot signal badlo (4 tarah ke)", f"{b['best_alternating']['cost']:g}"],
                    ["Greedy", "Har slot mein jo line lambi, use hara karo", f"{b['greedy']['cost']:g}"],
                    ["Sab 256 check karo", "Asli sabse achha jawab (sirf tulna ke liye)", f"{Cs:g}"],
                    ["Random", "Bina soche plan ka average", f"{Cr:g}"],
                    ["QUBO ka best", "Humare formula ka sabse achha plan", f"{b['qubo_exact_minimizer']['cost']:g}"],
                    ["QAOA (raw)", "Quantum ke 4096 nateejon ka average", f"{EQ:.1f}"],
                    ["Hybrid", "QAOA + normal computer se chhota sudhaar (alag likha hai)",
                     f"{r0['hybrid_qaoa_plus_local_search']['cost']:g}"]], [38, 100, 32]))

    s.append(Paragraph("9. Imaandar baatein (limitations)", H2))
    s += bullets(["Is chhoti problem par normal computer turant jawab de deta hai. Quantum se fayda dikhana maqsad nahi tha.",
                  f"Jode-wala formula hamesha perfect nahi hota. Ek random scenario mein yeh {gs['qubo_regret_max_pct']:.1f}% "
                  "peeche raha.",
                  "Sab kuch quantum <b>simulator</b> par chala hai, asli quantum hardware par nahi. Hardware ka noise nahi jaancha.",
                  "Official scenario H ka nateeja abhi baaki hai. Code bina badle uspar chalega."])

    s.append(KeepTogether([Paragraph("10. Shabdkosh (mushkil shabd)", H2), table([["Shabd", "Aasaan matlab"],
                    ["Bit", "0 ya 1 — yahaan: EW ya NS hara"],
                    ["Qubit", "Quantum bit — ek saath 0 aur 1 dono ho sakta hai, jab tak dekho nahi"],
                    ["QUBO", "Aisa cost formula jismein sirf akele bits aur do-do bits ke jode hon"],
                    ["QAOA", "Quantum algorithm jo achhe jawabon ke chance badhata hai"],
                    ["Shot", "Circuit ko ek baar chalakar ek jawab dekhna (humne 4096 shots liye)"],
                    ["Seed", "Random numbers ka fixed number, taaki nateeja dobara same aaye"],
                    ["Baseline", "Tulna ke liye simple tareeke (greedy, random, aadi)"],
                    ["Lift / Enrichment", "QAOA random se kitna behtar hai, iske maap"]], [38, 132])]))
    s.append(Spacer(1, 8))
    s.append(Paragraph("Code chalane ke liye: <font name='Mono'>python run.py --scenario official/scenario_R.json "
                       "--seed 0 --out outputs/R/seed_0</font>. Poori technical jaankari REPORT.md mein hai.", SUB))

    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title="Quantum Traffic Gridlock — Aasaan Explainer",
                            author="Quantum Traffic Gridlock team")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
