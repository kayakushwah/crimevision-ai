"""Epic 6 - court-style forensic PDF via ReportLab."""
import io
import datetime as dt
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

SS = getSampleStyleSheet()
H = ParagraphStyle("h", parent=SS["Heading2"], textColor=colors.HexColor("#8d0801"))
SM = ParagraphStyle("sm", parent=SS["BodyText"], fontSize=7.5, leading=9)


def _tbl(rows, widths, head=True):
    data = [[Paragraph(escape(str(c)), SM) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), .4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e5e5")))
    t.setStyle(TableStyle(st))
    return t


def _footer(c, d):
    c.setFont("Helvetica", 7)
    c.drawString(2 * cm, 1.2 * cm, "CrimeVision AI - AI-assisted analysis; requires human investigator verification.")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, "Page %d" % d.page)


def build_pdf(case_id, investigator, signed, image, aud, vid, ledger, chat):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm, title="Forensic Report " + case_id)
    W = A4[0] - 4 * cm
    s = [Paragraph("FORENSIC EVIDENCE SUMMARY REPORT", SS["Title"]),
         _tbl([["Case ID", case_id], ["Generated (UTC)", dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")],
               ["Investigator", investigator or "Unassigned"],
               ["Sign-off", "SIGNED" if signed else "PENDING - not yet signed off"]], [4 * cm, W - 4 * cm], head=False),
         Paragraph("1. Chain of Custody", H)]
    recs = [x["rec"] for x in (image, aud, vid) if x]
    if recs:
        s.append(_tbl([["Evidence ID", "File", "SHA-256", "Logged (UTC)", "KB"]] +
                      [[r["evidence_id"], r["file"], r["sha256"], r["logged_utc"], r["size_kb"]] for r in recs],
                      [2.6 * cm, 3 * cm, 7 * cm, 3 * cm, 1.4 * cm]))
    else:
        s.append(Paragraph("No evidence registered.", SS["BodyText"]))
    if image:
        r = image["res"]
        s += [Paragraph("2. Visual Evidence Analysis", H),
              Paragraph("Scene: <b>%s</b> | Threat level: <b>%s</b> | Model: %s" % (r["scene"], r["threat"], r["model"]),
                        SS["BodyText"])]
        b = io.BytesIO()
        r["annotated"].save(b, "PNG")
        b.seek(0)
        iw, ih = r["annotated"].size
        s += [RLImage(b, width=12 * cm, height=12 * cm * ih / iw), Spacer(1, 6),
              _tbl([["Item", "Confidence", "BBox (x,y,w,h)"]] +
                   [[d["label"], d["conf"], str(d["bbox"])] for d in r["detections"]], [6 * cm, 3 * cm, 8 * cm]),
              Spacer(1, 6)] + [Paragraph("- " + escape(l), SM) for l in r["leads"]]
    if ledger:
        s += [Paragraph("3. Master Event Ledger", H),
              _tbl([["Time", "Source", "Entry ID", "Event", "Category"]] +
                   [[e["clock"], e["source"], e["entry_id"], e["event"], e["category"]] for e in ledger],
                   [2.2 * cm, 1.5 * cm, 3.3 * cm, 6 * cm, 4 * cm])]
    if chat:
        s.append(Paragraph("4. Investigator Q&amp;A Log (grounded)", H))
        for q, a in chat:
            s += [Paragraph("<b>Q:</b> " + escape(q), SM),
                  Paragraph("<b>A:</b> " + escape(a).replace("\n", "<br/>"), SM), Spacer(1, 4)]
    s += [Spacer(1, 30), Paragraph("Investigator signature: ______________________   Date: ____________", SS["BodyText"])]
    doc.build(s, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
