"""Vector figures for the technical report (reportlab drawings; numbers read from outputs/)."""
import json
import os

from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle, PolyLine
from reportlab.lib import colors
from reportlab.lib.units import mm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK, MUTED, ACCENT = colors.HexColor("#1f2933"), colors.HexColor("#5b6670"), colors.HexColor("#1d5fa8")
GREEN, GREY, ORANGE = colors.HexColor("#2e8b57"), colors.HexColor("#b8c2cc"), colors.HexColor("#d9822b")
SOFT, LINE = colors.HexColor("#eef3f9"), colors.HexColor("#d5dde6")


def _txt(d, x, y, s, size=7.5, font="Body", col=INK, anchor="middle"):
    d.add(String(x, y, s, fontName=font, fontSize=size, fillColor=col, textAnchor=anchor))


def _arrow(d, x1, y, x2, col=MUTED):
    d.add(Line(x1, y, x2 - 2 * mm, y, strokeColor=col, strokeWidth=1.2))
    d.add(Polygon([x2 - 2.2 * mm, y + 1.3 * mm, x2, y, x2 - 2.2 * mm, y - 1.3 * mm], fillColor=col, strokeColor=col))


def pipeline(width):
    """Fig. 1: network (left) + pipeline steps (right)."""
    H = 30 * mm
    d = Drawing(width, H)
    # mini network
    road = colors.HexColor("#dfe4ea")
    d.add(Rect(0, 11 * mm, 46 * mm, 7 * mm, fillColor=road, strokeColor=None))
    for cx, n in ((11 * mm, "A"), (35 * mm, "B")):
        d.add(Rect(cx - 3.5 * mm, 2 * mm, 7 * mm, 25 * mm, fillColor=road, strokeColor=None))
        d.add(Circle(cx, 14.5 * mm, 5 * mm, fillColor=colors.white, strokeColor=ACCENT, strokeWidth=1.2))
        _txt(d, cx, 12.3 * mm, n, 10, "Bold", ACCENT)
    d.add(Line(17 * mm, 22.5 * mm, 27 * mm, 22.5 * mm, strokeColor=GREEN, strokeWidth=1.3))
    d.add(Polygon([27 * mm, 23.8 * mm, 29.5 * mm, 22.5 * mm, 27 * mm, 21.2 * mm], fillColor=GREEN, strokeColor=GREEN))
    _txt(d, 23 * mm, 24.6 * mm, "transfer", 6.5, col=GREEN)
    _txt(d, 23 * mm, 0, "8 bits: A1-A4 | B1-B4", 6.5, col=MUTED)
    # steps
    steps = [("Scenario", "JSON input"), ("QUBO", "8 qubits"),
             ("QAOA train", "p=4, 300 evals"), ("Sample", "4,096 shots"),
             ("Score", "official scorer")]
    x0, bw, gap = 52 * mm, (width - 52 * mm - 4 * 5 * mm) / 5, 5 * mm
    for i, (a, b) in enumerate(steps):
        x = x0 + i * (bw + gap)
        d.add(Rect(x, 8 * mm, bw, 14 * mm, rx=2, ry=2, fillColor=SOFT, strokeColor=ACCENT, strokeWidth=0.8))
        _txt(d, x + bw / 2, 16.5 * mm, a, 7.5, "Bold")
        _txt(d, x + bw / 2, 11.5 * mm, b, 6.3, col=MUTED)
        if i < 4:
            _arrow(d, x + bw + 0.5 * mm, 15 * mm, x + bw + gap - 0.5 * mm)
    _txt(d, x0 + (width - x0) / 2, 1.5 * mm, "Fig. 1  Two linked intersections (left) and the pipeline run by run.py (right).",
         7, col=MUTED)
    return d


def _load_costs(sc):
    rs = [json.load(open(os.path.join(ROOT, "outputs", sc, f"seed_{k}", "results.json"))) for k in range(5)]
    b = rs[0]["baselines"]
    eq = sum(r["qaoa_raw"]["E_Q"] for r in rs) / 5
    return [("Random avg", b["uniform_random_expected"]["cost"], GREY),
            ("Alternating", b["best_alternating"]["cost"], GREY),
            ("Greedy", b["greedy"]["cost"], GREY),
            ("QAOA avg (E_Q)", eq, ACCENT),
            ("Optimum C*", b["exact_enumeration"]["cost"], GREEN)]


def costs(width):
    """Fig. 2: cost comparison bars for R and H (shared axis per panel)."""
    H = 36 * mm
    d = Drawing(width, H)
    pw = (width - 6 * mm) / 2
    for p, sc in enumerate(("R", "H")):
        vals = _load_costs(sc)
        ox = p * (pw + 6 * mm)
        lab_w = 24 * mm
        vmax = max(v for _, v, _ in vals)
        _txt(d, ox, H - 3.5 * mm, f"Scenario {sc}", 8.5, "Bold", anchor="start")
        for i, (lab, v, col) in enumerate(vals):
            y = H - 10 * mm - i * 5 * mm
            _txt(d, ox + lab_w - 1.5 * mm, y + 0.9 * mm, lab, 7, anchor="end")
            w = (pw - lab_w - 12 * mm) * v / vmax
            d.add(Rect(ox + lab_w, y, w, 3.6 * mm, fillColor=col, strokeColor=None))
            _txt(d, ox + lab_w + w + 1.2 * mm, y + 0.9 * mm, (f"{v:.2f}".rstrip("0").rstrip(".") if lab != "QAOA avg (E_Q)" else f"{v:.1f}"), 7, "Bold",
                 anchor="start")
    _txt(d, width / 2, 0.5 * mm, "Fig. 2  Official cost of each method (lower is better). Blue = mean of 4,096 raw QAOA "
         "samples, averaged over 5 seeds.", 7, col=MUTED)
    return d


def depth(width):
    """Fig. 3: worst-seed lift vs depth p for three initialisations, R and H."""
    exp = json.load(open(os.path.join(ROOT, "outputs", "experiments", "experiments.json")))
    H = 40 * mm
    d = Drawing(width, H)
    styles = {"interp": (ACCENT, "INTERP warm start (used)"), "ramp": (ORANGE, "linear ramp only"),
              "random": (GREY, "random start")}
    pw = (width - 50 * mm) / 2
    for p, sc in enumerate(("R", "H")):
        ox, oy, ph = 8 * mm + p * (pw + 8 * mm), 8 * mm, H - 15 * mm
        d.add(Rect(ox, oy, pw, ph, fillColor=None, strokeColor=LINE, strokeWidth=0.6))
        for v in (0, 0.5, 1.0):
            y = oy + ph * v
            d.add(Line(ox, y, ox + pw, y, strokeColor=LINE, strokeWidth=0.4))
            _txt(d, ox - 1.2 * mm, y - 1 * mm, f"{v:g}", 6.5, col=MUTED, anchor="end")
        for k in range(1, 5):
            _txt(d, ox + pw * (k - 0.5) / 4, oy - 4 * mm, f"p={k}", 6.5, col=MUTED)
        _txt(d, ox + pw / 2, oy + ph + 2 * mm, f"Scenario {sc}: worst-seed lift", 7.5, "Bold")
        for init, (col, _) in styles.items():
            pts = []
            for k in range(1, 5):
                r = next(a for a in exp["ablations"] if a["scenario"] == sc and a["p"] == k and a["init"] == init
                         and a["lam_o"] == 1.0)
                pts += [ox + pw * (k - 0.5) / 4, oy + ph * max(0.0, min(1.0, r["lift_min"]))]
            d.add(PolyLine(pts, strokeColor=col, strokeWidth=1.6 if init == "interp" else 1.1))
            for j in range(0, len(pts), 2):
                d.add(Circle(pts[j], pts[j + 1], 0.9 * mm, fillColor=col, strokeColor=None))
    lx = width - 40 * mm
    for i, (init, (col, lab)) in enumerate(styles.items()):
        y = H - 14 * mm - i * 5.5 * mm
        d.add(Line(lx, y + 1 * mm, lx + 5 * mm, y + 1 * mm, strokeColor=col, strokeWidth=1.6))
        _txt(d, lx + 6.5 * mm, y, lab, 6.8, anchor="start")
    _txt(d, width / 2, 0, "Fig. 3  Ablation over depth and initialisation (5 seeds, 300-evaluation budget). "
         "Only INTERP keeps improving as p grows.", 7, col=MUTED)
    return d


FIGS = {"pipeline": pipeline, "costs": costs, "depth": depth}
