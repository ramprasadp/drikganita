#!/usr/bin/env python3
"""Convert panchanga CSV to a calendar-style PDF."""

import argparse
import csv
import os
import sys
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]



def register_font():
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("CalFont", path))
            pdfmetrics.registerFont(TTFont("CalFontB", path))
            return "CalFont", "CalFontB"
    return "Helvetica", "Helvetica-Bold"


def load_short_nakshatras(path="shortnakshatra.txt"):
    mapping = {}
    if not os.path.exists(path):
        return mapping
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            full, short = line.split(",", 1)
            mapping[full.strip().lower()] = short.strip()
    return mapping


def read_csv(filename):
    with open(filename) as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            row["_dt"] = datetime.strptime(row["date"], "%d-%m-%Y")
            row["_wd"] = (row["_dt"].weekday() + 1) % 7  # Sun=0, Mon=1, ..., Sat=6
            rows.append(row)
    return rows


def build_weeks(rows):
    weeks, cur = [], {}
    for row in rows:
        wd = row["_wd"]
        if wd == 0 and cur:  # new Sunday = new week
            weeks.append(cur)
            cur = {}
        cur[wd] = row
    if cur:
        weeks.append(cur)
    return weeks


def shorten_nak(name, short_naks):
    return short_naks.get(name.lower(), name)


def is_highlight(row):
    tnum = row.get("tithi_num", "")
    stnum = row.get("shraddha_tithi_num", "")
    paksha = row.get("paksha", "")
    is_krishna = paksha in ("KRiShNa", "Kṛṣṇa")
    if "11" in tnum.split(", "):
        return True
    if is_krishna and stnum == "15":
        return True
    return False


def make_cell(row, available_cols, styles, short_naks, inner_cell_w):
    """inner_cell_w: usable width inside the cell (points) for nested tables."""
    day = row["_dt"].day
    red = is_highlight(row)
    sfx = "_red" if red else ""

    date_para = Paragraph(f"<b>{day}</b>", styles["date" + sfx])

    tnum = row.get("tithi_num", "")
    stnum = row.get("shraddha_tithi_num", "")
    tithi_lines = []
    if tnum:
        tithi_lines.append(Paragraph(f"<b>{escape(tnum)}</b>", styles["tithi_stack" + sfx]))
    if stnum:
        tithi_lines.append(Paragraph(escape(stnum), styles["tithi_stack" + sfx]))

    if tithi_lines:
        tithi_col_w = max(inner_cell_w * 0.52, 1)
        tithi_stack = Table([[ln] for ln in tithi_lines], colWidths=[tithi_col_w])
        tithi_stack.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        top_w = max(inner_cell_w * 0.48, 1)
        top_row = Table([[date_para, tithi_stack]], colWidths=[top_w, tithi_col_w])
        top_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        parts = [top_row]
    else:
        parts = [date_para]

    nak = row.get("nakshatra", "")
    if nak:
        parts.append(
            Paragraph(escape(shorten_nak(nak, short_naks)), styles["nak_mid" + sfx]))

    yoga = row.get("yoga", "")
    karana_val = row.get("karana", "")
    if yoga or karana_val:
        half = max(inner_cell_w * 0.5, 1)
        left = (
            Paragraph(escape(yoga), styles["row3" + sfx])
            if yoga
            else Paragraph("", styles["row3" + sfx])
        )
        right = (
            Paragraph(escape(karana_val), styles["row3_kar" + sfx])
            if karana_val
            else Paragraph("", styles["row3_kar" + sfx])
        )
        yk = Table([[left, right]], colWidths=[half, half])
        yk.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        parts.append(yk)

    return parts


def unique_ordered(rows, key):
    seen, result = set(), []
    for r in rows:
        v = r.get(key, "")
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def generate_pdf(csv_file, output_file):
    font, font_bold = register_font()
    short_naks = load_short_nakshatras()
    rows = read_csv(csv_file)
    weeks = build_weeks(rows)
    available_cols = set(rows[0].keys())
    n_weeks = len(weeks)

    red = colors.HexColor("#cc0000")
    grey = colors.HexColor("#555555")
    styles = {
        "date": ParagraphStyle("date", fontName=font_bold, fontSize=18, leading=20,
                               alignment=0),
        "date_red": ParagraphStyle("date_red", fontName=font_bold, fontSize=18, leading=20,
                                   textColor=red, alignment=0),
        "tithi_stack": ParagraphStyle(
            "tithi_stack", fontName=font, fontSize=9, leading=11,
            textColor=colors.HexColor("#333333"), alignment=2),
        "tithi_stack_red": ParagraphStyle(
            "tithi_stack_red", fontName=font, fontSize=9, leading=11,
            textColor=red, alignment=2),
        "nak_mid": ParagraphStyle("nak_mid", fontName=font, fontSize=6, leading=7.5,
                                  textColor=grey, alignment=1),
        "nak_mid_red": ParagraphStyle("nak_mid_red", fontName=font, fontSize=6, leading=7.5,
                                      textColor=red, alignment=1),
        "row3": ParagraphStyle("row3", fontName=font, fontSize=6, leading=7.5,
                               textColor=grey, alignment=0),
        "row3_red": ParagraphStyle("row3_red", fontName=font, fontSize=6, leading=7.5,
                                   textColor=red, alignment=0),
        "row3_kar": ParagraphStyle("row3_kar", fontName=font, fontSize=6, leading=7.5,
                                   textColor=grey, alignment=2),
        "row3_kar_red": ParagraphStyle("row3_kar_red", fontName=font, fontSize=6, leading=7.5,
                                       textColor=red, alignment=2),
        "hdr":  ParagraphStyle("hdr", fontName=font_bold, fontSize=7.5, leading=10,
                               alignment=1, textColor=colors.white),
        "day":  ParagraphStyle("day", fontName=font_bold, fontSize=9, leading=11,
                               alignment=1, textColor=colors.white),
        "sub":  ParagraphStyle("sub", fontName=font, fontSize=9, leading=12,
                               alignment=1, textColor=colors.HexColor("#555555")),
    }
    empty = Paragraph("", styles["row3"])

    # Header row: week date ranges
    header = [Paragraph("", styles["hdr"])]
    for week in weeks:
        days = sorted(week.keys())
        d0 = week[days[0]]["_dt"].strftime("%d %b")
        d1 = week[days[-1]]["_dt"].strftime("%d %b")
        header.append(Paragraph(f"{d0} – {d1}", styles["hdr"]))

    # Layout: portrait A4 — inner width for cell content (after table cell padding)
    page_w = A4[0]
    margin = 12 * mm
    usable = page_w - 2 * margin
    day_col = 24 * mm
    week_col = (usable - day_col) / n_weeks
    inner_cell_w = week_col - 7  # ~4pt left + ~3pt right padding

    krishna_cells = []
    data = [header]
    for wd in range(7):
        row_data = [Paragraph(DAY_NAMES[wd], styles["day"])]
        for wi, week in enumerate(weeks):
            if wd in week:
                row_data.append(
                    make_cell(week[wd], available_cols, styles, short_naks, inner_cell_w))
                paksha = week[wd].get("paksha", "")
                if paksha in ("KRiShNa", "Kṛṣṇa"):
                    krishna_cells.append((wi + 1, wd + 1))
            else:
                row_data.append(empty)
        data.append(row_data)

    col_widths = [day_col] + [week_col] * n_weeks

    table = Table(data, colWidths=col_widths, repeatRows=1)

    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#34495e")),
        ("TEXTCOLOR",  (0, 1), (0, -1), colors.white),
        ("ALIGN",      (0, 1), (0, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#bdc3c7")),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (1, 1), (-1, -1), 4),
        ("RIGHTPADDING",  (1, 1), (-1, -1), 3),
        ("VALIGN", (0, 1), (0, -1), "MIDDLE"),
    ]

    for col, row in krishna_cells:
        cmds.append(("BACKGROUND", (col, row), (col, row),
                     colors.HexColor("#e8e8e8")))

    table.setStyle(TableStyle(cmds))

    # Subtitle (samvatsara, rtu, masa, date range)
    first, last = rows[0], rows[-1]
    date_range = (f"{first['_dt'].strftime('%d %b %Y')}"
                  f" – {last['_dt'].strftime('%d %b %Y')}")
    masas = unique_ordered(rows, "masa")
    parts = []
    if "samvatsara" in available_cols:
        parts.append(first["samvatsara"])
    if "rtu" in available_cols:
        parts.extend(unique_ordered(rows, "rtu"))
    if masas:
        parts.append(", ".join(masas))
    parts.append(date_range)
    sub_text = escape("  |  ".join(parts))

    doc = SimpleDocTemplate(output_file, pagesize=A4,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=8 * mm, bottomMargin=8 * mm)
    elements = [
        Paragraph(sub_text, styles["sub"]),
        Spacer(1, 2 * mm),
        table,
    ]
    doc.build(elements)
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Convert panchanga CSV to a calendar-grid PDF")
    parser.add_argument("csv_file", help="Input CSV file from cli.py")
    parser.add_argument("-o", "--output",
                        help="Output PDF filename (default: <csv>_calendar.pdf)")
    args = parser.parse_args()

    output = args.output or args.csv_file.rsplit(".", 1)[0] + "_calendar.pdf"
    result = generate_pdf(args.csv_file, output)
    print(f"Saved: {result}")


if __name__ == "__main__":
    main()
