"""Render the 2-page monthly letter as a branded PDF (reportlab).

Consumes the grounded `facts` + a `narrative` dict (prose written by the LLM or a
deterministic fallback) + chart PNG paths. The header/footer band carries the XP
house-style; everything is parameterized per advisor/client for scale.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageTemplate, Paragraph, Spacer, Table,
    TableStyle, KeepTogether,
)

from . import brand as B
from . import config

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
HEADER_H = 26 * mm
FOOTER_H = 16 * mm

_y = colors.HexColor(B.XP_YELLOW)
_blk = colors.HexColor(B.XP_BLACK)
_gray = colors.HexColor(B.XP_GRAY)
_graylt = colors.HexColor(B.XP_GRAY_LT)
_pos = colors.HexColor(B.POSITIVE)
_neg = colors.HexColor(B.NEGATIVE)


# --------------------------------------------------------------------------- fmt
def brl(v: float) -> str:
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float, signed: bool = True) -> str:
    return (f"{v:+.2f}%" if signed else f"{v:.2f}%").replace(".", ",")


# ------------------------------------------------------------------------ styles
def _styles() -> dict:
    base = dict(fontName="Helvetica", textColor=_blk, leading=13)
    return {
        "body": ParagraphStyle("body", **base, fontSize=9.5, alignment=TA_JUSTIFY,
                               spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5,
                             textColor=_blk, spaceBefore=8, spaceAfter=4, leading=14),
        "kpi_val": ParagraphStyle("kpi_val", fontName="Helvetica-Bold", fontSize=15,
                                  textColor=_blk, leading=17),
        "kpi_lbl": ParagraphStyle("kpi_lbl", fontName="Helvetica", fontSize=7.5,
                                  textColor=_gray, leading=9),
        "rec_h": ParagraphStyle("rec_h", fontName="Helvetica-Bold", fontSize=9,
                                textColor=_blk, leading=11),
        "rec_b": ParagraphStyle("rec_b", fontName="Helvetica", fontSize=8.3,
                                textColor=_graphite(), leading=10, alignment=TA_JUSTIFY),
        "sign": ParagraphStyle("sign", fontName="Helvetica-Bold", fontSize=9.5,
                               textColor=_blk, leading=12),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.2,
                                textColor=_gray, leading=8.6, alignment=TA_JUSTIFY),
        "tbl": ParagraphStyle("tbl", fontName="Helvetica", fontSize=8.2, textColor=_blk,
                              leading=10),
    }


def _graphite():
    return colors.HexColor(B.XP_GRAPHITE)


# ------------------------------------------------------------- header / footer
def _header_footer(canvas, doc):
    facts = doc._facts
    canvas.saveState()
    # top black band
    canvas.setFillColor(_blk)
    canvas.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)
    # XP logo (official asset provided by the user, else a generated fallback mark)
    logo = doc._logo_path
    if logo and logo.exists():
        lh = 16 * mm
        lw = lh * doc._logo_ratio
        canvas.drawImage(str(logo), MARGIN, PAGE_H - HEADER_H + (HEADER_H - lh) / 2,
                         width=lw, height=lh, mask="auto", preserveAspectRatio=True)
    # title (right-aligned)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - HEADER_H + 13 * mm,
                           "Relatório Mensal de Investimentos")
    canvas.setFillColor(_y)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - HEADER_H + 8 * mm,
                           f"Referência: {facts['meta']['reference_month_label']}  ·  "
                           f"Perfil {facts['client']['risk_profile']}")
    # footer
    canvas.setFillColor(_graylt)
    canvas.rect(0, 0, PAGE_W, FOOTER_H, fill=1, stroke=0)
    canvas.setFillColor(_gray)
    canvas.setFont("Helvetica", 6.6)
    disclaimer = facts["disclaimer"]
    # word-wrap to the left column (leave room for the advisor block on the right)
    # and render up to two lines, never cutting a word mid-way.
    from reportlab.pdfbase.pdfmetrics import stringWidth
    avail = PAGE_W - 2 * MARGIN - 62 * mm
    lines, cur = [], ""
    for word in disclaimer.split():
        trial = f"{cur} {word}".strip()
        if stringWidth(trial, "Helvetica", 6.6) <= avail:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    for i, line in enumerate(lines[:2]):
        canvas.drawString(MARGIN, FOOTER_H - (6 + 3 * i) * mm, line)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(_blk)
    canvas.drawRightString(PAGE_W - MARGIN, FOOTER_H - 6 * mm,
                           f"{facts['advisor']['name']} · {facts['advisor']['title']} {facts['advisor']['code']}")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_gray)
    canvas.drawRightString(PAGE_W - MARGIN, FOOTER_H - 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


# -------------------------------------------------------------- content pieces
def _kpi_card(label, value, color=None, S=None):
    val = Paragraph(f'<font color="{(color or B.XP_BLACK)}">{value}</font>', S["kpi_val"])
    lbl = Paragraph(label, S["kpi_lbl"])
    t = Table([[val], [lbl]], colWidths=[(PAGE_W - 2 * MARGIN - 12) / 3])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, _graylt),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, _y),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (0, 0), 6),
        ("BOTTOMPADDING", (0, 1), (0, 1), 6),
    ]))
    return t


def _kpi_row(facts, S):
    p = facts["performance"]
    acc = facts["accumulated"]
    cards = [
        _kpi_card("Patrimônio total", brl(facts["totals"]["patrimony_brl"]), B.XP_BLACK, S),
        _kpi_card(f"Retorno em {facts['meta']['reference_month_label']} (estimativa)",
                  pct(p["total_return_pct"]), B.POSITIVE if p["total_return_pct"] >= 0 else B.NEGATIVE, S),
        _kpi_card("Retorno acumulado (desde os aportes)", pct(acc["return_pct"]),
                  B.POSITIVE if acc["return_pct"] >= 0 else B.NEGATIVE, S),
    ]
    row = Table([cards], colWidths=[(PAGE_W - 2 * MARGIN) / 3] * 3)
    row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                             ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return row


def _img_h(path, height_mm):
    """Image flowable at a fixed height, width from the file's true aspect ratio."""
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        ratio = im.size[0] / im.size[1]
    return Image(path, width=height_mm * mm * ratio, height=height_mm * mm)


def _two_charts(chart_paths, S):
    h = 52
    donut = _img_h(chart_paths["allocation"], h)
    bench = _img_h(chart_paths["benchmark"], h)
    avail = PAGE_W - 2 * MARGIN
    t = Table([[donut, bench]], colWidths=[avail * 0.42, avail * 0.58])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ALIGN", (0, 0), (0, 0), "CENTER"),
                           ("ALIGN", (1, 0), (1, 0), "CENTER"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def _accumulated_chart(chart_paths, S):
    img = _img_h(chart_paths["accumulated"], 40)
    t = Table([[img]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _rebalance_table(facts, S):
    head = ["Classe", "Atual", "Alvo", "Δ (p.p.)"]
    rows = [head]
    for r in facts["rebalance"]:
        rows.append([r["asset_class"], f'{r["current_pct"]:.1f}%'.replace(".", ","),
                     f'{r["target_pct"]:.0f}%',
                     f'{r["delta_pct"]:+.1f}'.replace(".", ",")])
    t = Table(rows, colWidths=[40 * mm, 20 * mm, 20 * mm, 22 * mm])
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _blk),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.4, _graylt),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i, r in enumerate(facts["rebalance"], start=1):
        c = _pos if r["delta_pct"] <= 0 else _neg
        style.append(("TEXTCOLOR", (3, i), (3, i), c))
    t.setStyle(TableStyle(style))
    return t


def _recommendations(facts, S, top=4):
    flow = []
    badge = {"INVESTIR": _pos, "DESINVESTIR": _neg, "REBALANCEAR": _graphite(),
             "REVISAR": _gray, "MANTER": _blk}
    for r in facts["recommendations"][:top]:
        amt = f' · ~{brl(r["amount_brl"])}' if r.get("amount_brl") else ""
        head = Paragraph(f'{r["headline"]}{amt}', S["rec_h"])
        body = Paragraph(r["rationale"], S["rec_b"])
        cell = Table([[head], [body]], colWidths=[PAGE_W - 2 * MARGIN - 10])
        cell.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (0, 0), 4), ("BOTTOMPADDING", (0, 1), (0, 1), 5),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, badge.get(r["action"], _blk)),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FCFCFC")),
        ]))
        flow.append(KeepTogether([cell, Spacer(1, 4)]))
    return flow


# ----------------------------------------------------------------------- build
def render_letter(facts: dict, narrative: dict, chart_paths: dict,
                  out_path: Path) -> Path:
    S = _styles()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=HEADER_H + 6 * mm, bottomMargin=FOOTER_H + 4 * mm,
        title=f"Relatório Mensal de {facts['client']['full_name']}",
        author=facts["advisor"]["name"],
    )
    doc._facts = facts
    # XP logo: use assets/xp_logo.png (official asset if present, else generate one)
    logo_path = config.INPUT_DIR / "XP_Investimentos_logo.png"   # asset provided by user
    if not logo_path.exists():
        logo_path = config.ASSETS_DIR / "xp_logo.png"
        if not logo_path.exists():
            from . import make_logo
            make_logo.generate(logo_path)
    doc._logo_path = logo_path
    try:
        from PIL import Image
        with Image.open(logo_path) as _im:
            doc._logo_ratio = _im.size[0] / _im.size[1]
    except Exception:
        doc._logo_ratio = 1.0
    frame = Frame(MARGIN, FOOTER_H + 4 * mm, PAGE_W - 2 * MARGIN,
                  PAGE_H - HEADER_H - FOOTER_H - 10 * mm, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame],
                                       onPage=_header_footer)])

    story = []
    dateline = ParagraphStyle("dateline", fontName="Helvetica", fontSize=9,
                              textColor=_gray, alignment=TA_RIGHT, spaceAfter=8)
    story.append(Paragraph(facts["meta"]["issue_dateline_pt"], dateline))
    story.append(Paragraph(
        f'{facts["client"]["salutation"]} {facts["client"]["first_name"]},', S["h2"]))
    story.append(Paragraph(narrative["greeting"], S["body"]))
    story.append(_kpi_row(facts, S))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Desempenho da carteira", S["h2"]))
    story.append(_two_charts(chart_paths, S))
    story.append(Spacer(1, 4))
    story.append(Paragraph(narrative["performance"], S["body"]))
    story.append(Paragraph(f'<i>{facts["period_disclaimer"]}</i>', S["small"]))

    story.append(Paragraph("Cenário macroeconômico", S["h2"]))
    story.append(Paragraph(narrative["macro"], S["body"]))

    story.append(Paragraph("Recomendações", S["h2"]))
    story.append(Paragraph(narrative["recommendations"], S["body"]))
    story.append(Spacer(1, 2))
    story.extend(_recommendations(facts, S))
    story.append(Spacer(1, 4))
    story.append(_rebalance_table(facts, S))

    story.append(Spacer(1, 8))
    story.append(Paragraph(narrative["closing"], S["body"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Atenciosamente,", S["body"]))
    story.append(Paragraph(facts["advisor"]["name"], S["sign"]))
    story.append(Paragraph(f'{facts["advisor"]["title"]} de Investimentos · Código {facts["advisor"]["code"]}',
                           S["kpi_lbl"]))

    doc.build(story)
    return out_path


if __name__ == "__main__":
    from .facts import build_facts
    from .charts import build_all
    from .narrate import build_narrative
    f = build_facts()
    charts = build_all(f)
    nar = build_narrative(f)
    out = render_letter(f, nar, charts,
                        config.OUTPUT_DIR / "albert_da_silva_relatorio_abr25.pdf")
    print("PDF:", out)
