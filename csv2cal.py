#!/usr/bin/env python3
"""Convert panchanga CSV to a calendar-style PDF."""

import argparse
import csv
import os
import sys
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
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


def make_cell(row, available_cols, styles, short_naks):
    day = row["_dt"].day
    red = is_highlight(row)
    sfx = "_red" if red else ""

    date_line = f'<b>{day}</b>'
    parts = [Paragraph(date_line, styles["date" + sfx])]

    tnum = row.get("tithi_num", "")
    stnum = row.get("shraddha_tithi_num", "")
    if tnum or stnum:
        line2 = f"<b>{escape(tnum)}</b> / {escape(stnum)}"
        parts.append(Paragraph(line2, styles["row2" + sfx]))

    nak = row.get("nakshatra", "")
    if nak:
        parts.append(Paragraph(escape(shorten_nak(nak, short_naks)), styles["row3" + sfx]))

    yoga = row.get("yoga", "")
    karana_val = row.get("karana", "")
    if yoga or karana_val:
        left = Paragraph(escape(yoga), styles["row3" + sfx]) if yoga else Paragraph("", styles["row3" + sfx])
        right = Paragraph(escape(karana_val), styles["row3r" + sfx]) if karana_val else Paragraph("", styles["row3r" + sfx])
        inner = Table([[left, right]], colWidths=["50%", "50%"])
        inner.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        parts.append(inner)

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
    styles = {
        "date": ParagraphStyle("date", fontName=font_bold, fontSize=14, leading=16),
        "date_red": ParagraphStyle("date_red", fontName=font_bold, fontSize=14, leading=16,
                                   textColor=red),
        "row2": ParagraphStyle("row2", fontName=font, fontSize=7, leading=9,
                               textColor=colors.HexColor("#333333")),
        "row2_red": ParagraphStyle("row2_red", fontName=font, fontSize=7, leading=9,
                                   textColor=red),
        "row3": ParagraphStyle("row3", fontName=font, fontSize=5.5, leading=7,
                               textColor=colors.HexColor("#555555")),
        "row3_red": ParagraphStyle("row3_red", fontName=font, fontSize=5.5, leading=7,
                                   textColor=red),
        "row3r": ParagraphStyle("row3r", fontName=font, fontSize=5.5, leading=7,
                                textColor=colors.HexColor("#555555"), alignment=2),
        "row3r_red": ParagraphStyle("row3r_red", fontName=font, fontSize=5.5, leading=7,
                                    textColor=red, alignment=2),
        "hdr":  ParagraphStyle("hdr", fontName=font_bold, fontSize=7.5, leading=10,
                               alignment=1, textColor=colors.white),
        "day":  ParagraphStyle("day", fontName=font_bold, fontSize=9, leading=11,
                               alignment=1, textColor=colors.white),
        "title": ParagraphStyle("title", fontName=font_bold, fontSize=14,
                                leading=18, alignment=1),
        "sub":  ParagraphStyle("sub", fontName=font, fontSize=9, leading=12,
                               alignment=1, textColor=colors.HexColor("#555555")),
        "legend": ParagraphStyle("legend", fontName=font, fontSize=6.5, leading=9,
                                 textColor=colors.HexColor("#666666"), alignment=1),
    }
    empty = Paragraph("", styles["row3"])

    # Header row: week date ranges
    header = [Paragraph("", styles["hdr"])]
    for week in weeks:
        days = sorted(week.keys())
        d0 = week[days[0]]["_dt"].strftime("%d %b")
        d1 = week[days[-1]]["_dt"].strftime("%d %b")
        header.append(Paragraph(f"{d0} – {d1}", styles["hdr"]))

    krishna_cells = []
    data = [header]
    for wd in range(7):
        row_data = [Paragraph(DAY_NAMES[wd], styles["day"])]
        for wi, week in enumerate(weeks):
            if wd in week:
                row_data.append(make_cell(week[wd], available_cols, styles, short_naks))
                paksha = week[wd].get("paksha", "")
                if paksha in ("KRiShNa", "Kṛṣṇa"):
                    krishna_cells.append((wi + 1, wd + 1))
            else:
                row_data.append(empty)
        data.append(row_data)

    # Layout
    page_w = landscape(A4)[0]
    margin = 12 * mm
    usable = page_w - 2 * margin
    day_col = 24 * mm
    week_col = (usable - day_col) / n_weeks
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

    # Title & subtitle
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

    legend_text = ("Grey cells = Krishna paksha    "
                   "Row 2: Tithi / Shraddha Tithi    "
                   "Row 3: Nakshatra  Yoga  Karana")

    doc = SimpleDocTemplate(output_file, pagesize=landscape(A4),
                            leftMargin=margin, rightMargin=margin,
                            topMargin=8 * mm, bottomMargin=8 * mm)
    elements = [
        Paragraph("Pañcāṅga", styles["title"]),
        Paragraph(sub_text, styles["sub"]),
        Spacer(1, 2 * mm),
        Paragraph(legend_text, styles["legend"]),
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
