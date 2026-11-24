"""Builds a printable PDF of a health report with ReportLab."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .advice import EMERGENCY

LEVEL_COLOR = {"Low": colors.HexColor("#17855C"), "Moderate": colors.HexColor("#9A6A00"), "High": colors.HexColor("#CC3B2E")}
INK, MUTED = colors.HexColor("#11212D"), colors.HexColor("#5B6B75")


def build_pdf(rep):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title="Health report " + rep["report_id"])
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=20, textColor=INK, alignment=0, spaceAfter=2)
    H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, textColor=INK, spaceBefore=12, spaceAfter=4)
    B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13, textColor=INK)
    S = ParagraphStyle("s", parent=B, fontSize=8.5, textColor=MUTED)
    p = rep["patient"]
    el = [Paragraph("Smart Health Monitor - Health report", H1),
          Paragraph(f"Report {rep['report_id']} &nbsp;|&nbsp; {rep['created']}", S), Spacer(1, 6)]
    info = [["Patient", p.get("name") or "Guest", "Preferred city", p.get("city") or "Not given"]]
    t = Table(info, colWidths=[24 * mm, 56 * mm, 30 * mm, 56 * mm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (0, 0), MUTED),
                           ("TEXTCOLOR", (2, 0), (2, 0), MUTED), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#D5DDDA"))]))
    el += [t, Paragraph("Summary", H2), Paragraph(rep["overall"]["headline"], B), Paragraph(rep["overall"]["detail"], B), Paragraph("Model scores are screening outputs, not validated clinical probabilities or diagnoses. Safety flags are assessed separately.", S)]

    rows = [["Screening", "Risk", "Probability", "Model (ROC-AUC)"]]
    for r in rep["results"]:
        rows.append([r["title"], r["risk_level"], f"{r['percent']:g}% (model score)", f"{r['model']['name']} ({r['model']['roc_auc']:.2f})"])
    t = Table(rows, colWidths=[55 * mm, 28 * mm, 30 * mm, 57 * mm], repeatRows=1)
    st = [("FONTSIZE", (0, 0), (-1, -1), 9), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6ECEA")),
          ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DDDA")), ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    for i, r in enumerate(rep["results"], 1):
        st.append(("TEXTCOLOR", (1, i), (1, i), LEVEL_COLOR[r["risk_level"]]))
        st.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
    t.setStyle(TableStyle(st))
    el += [Paragraph("Results", H2), t]

    for r in rep["results"]:
        el.append(Paragraph(f"{r['title']} - {r['risk_level']} risk ({r['percent']:g}%)", H2))
        if r.get("factors_up"):
            el.append(Paragraph("<b>Main factors raising the risk:</b> " + "; ".join(f"{f['label']} ({f['value']})" for f in r["factors_up"]), B))
        for f in r.get("flags", []):
            el.append(Paragraph("&bull; " + f["text"], B))
        el.append(Spacer(1, 3))
        for a in r["advice"]:
            el.append(Paragraph("- " + a, B))

    el.append(Paragraph("Recommended doctors", H2))
    for g in rep["doctor_groups"]:
        el.append(Paragraph(f"<b>{g['specialty']}</b> - {g['urgency']}", B))
        rows = [["Doctor", "Hospital, city", "Experience", "Fee", "Match"]]
        for d in g["doctors"]:
            rows.append([d["name"], f"{d['hospital']}, {d['city']}", f"{d['experience_years']} yrs", f"Rs. {d['consultation_fee_inr']}", f"{d['match_percent']}%"])
        t = Table(rows, colWidths=[38 * mm, 66 * mm, 22 * mm, 22 * mm, 22 * mm], repeatRows=1)
        t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6ECEA")),
                               ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DDDA"))]))
        el += [t, Spacer(1, 6)]

    el += [Paragraph("Important", H2), Paragraph(EMERGENCY, B), Paragraph("Independent safety alerts may recommend more urgent assessment than the model risk category. The model score does not override symptoms or concerning measurements.", B),
           Paragraph("This report is a screening aid produced by machine-learning models trained on public datasets. "
                     "It is not a diagnosis. The doctor directory is sample data for demonstration. Always consult a "
                     "qualified doctor before making medical decisions.", S)]
    doc.build(el)
    return buf.getvalue()
