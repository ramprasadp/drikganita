#!/usr/bin/env python3

import argparse
import csv
import json
import sys
import difflib
from datetime import datetime, timedelta
from pytz import timezone

from panchanga import *

FORMAT_TIME = lambda t: "%02d:%02d:%02d" % (t[0], t[1], t[2])

IAST_TO_ITRANS = [
    ("ā", "aa"), ("ī", "ii"), ("ū", "uu"),
    ("ṝ", "RRI"), ("ṛ", "Ri"),
    ("ai", "ai"), ("au", "au"),
    ("ṃ", "M"), ("ḥ", "H"),
    ("ṅ", "~N"), ("ñ", "~n"),
    ("ṭh", "Th"), ("ṭ", "T"),
    ("ḍh", "Dh"), ("ḍ", "D"),
    ("ṇ", "N"),
    ("ś", "sh"), ("ṣ", "Sh"),
    ("Ā", "Aa"), ("Ī", "Ii"), ("Ū", "Uu"),
    ("Ṝ", "RRI"), ("Ṛ", "Ri"),
    ("Ṃ", "M"), ("Ḥ", "H"),
    ("Ṅ", "~N"), ("Ñ", "~n"),
    ("Ṭh", "Th"), ("Ṭ", "T"),
    ("Ḍh", "Dh"), ("Ḍ", "D"),
    ("Ṇ", "N"),
    ("Ś", "Sh"), ("Ṣ", "Sh"),
]


def to_itrans(text):
    import unicodedata
    text = unicodedata.normalize('NFC', text)
    for iast, itrans in IAST_TO_ITRANS:
        text = text.replace(iast, itrans)
    return text


def load_data():
    with open("sanskrit_names.json") as f:
        names = json.load(f)
    with open("cities.json") as f:
        cities = json.load(f)
    return names, cities


def resolve_city(city_name, cities):
    key = city_name.title()
    if key in cities:
        return key, cities[key]

    for k in cities:
        if k.lower() == city_name.lower():
            return k, cities[k]

    matches = difflib.get_close_matches(key, cities.keys(), n=5, cutoff=0.6)
    if matches:
        print(f"City '{city_name}' not found. Did you mean:", file=sys.stderr)
        for m in matches:
            print(f"  - {m}", file=sys.stderr)
    else:
        print(f"City '{city_name}' not found in database.", file=sys.stderr)
    sys.exit(1)


def parse_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%d-%m-%Y")
        return Date(dt.year, dt.month, dt.day)
    except ValueError:
        print(f"Invalid date format: '{date_str}'. Use DD-MM-YYYY.", file=sys.stderr)
        sys.exit(1)


def compute_tz_offset(city_info, date):
    tz = timezone(city_info['timezone'])
    dt = datetime(date.year, date.month, date.day)
    return tz.utcoffset(dt, is_dst=True).total_seconds() / 3600.0


def format_name_hms(nhms, lookup):
    name = lookup[str(nhms[0])]
    time = FORMAT_TIME(nhms[1])
    if len(nhms) == 4:
        name += ", " + lookup[str(nhms[2])]
        time += ", " + FORMAT_TIME(nhms[3])
    return name, time


def compute_panchanga(date, place, names, use_itrans=False):
    jd = gregorian_to_jd(date)
    ti = tithi(jd, place)
    nak = nakshatra(jd, place)
    yog = yoga(jd, place)
    kar = karana(jd, place)
    mas = masa(jd, place)
    rtu_val = ritu(mas[0])
    vara = vaara(jd)
    srise = sunrise(jd, place)[1]
    sset = sunset(jd, place)[1]
    kday = ahargana(jd)
    kyear, sakayr = elapsed_year(jd, mas[0])
    samvat = samvatsara(jd, mas[0])
    day_dur = day_duration(jd, place)[1]

    tithi_name, tithi_end = format_name_hms(ti, names["tithis"])
    nak_name, nak_end = format_name_hms(nak, names["nakshatras"])
    yoga_name, yoga_end = format_name_hms(yog, names["yogas"])
    karana_name = names["karanas"][str(kar[0])]
    vara_name = names["varas"][str(vara)]
    masa_name = names["masas"][str(mas[0])]
    if mas[1]:
        masa_name = "Adhika " + masa_name
    rtu_name = names["ritus"][str(rtu_val)]
    samvat_name = names["samvats"][str(samvat)]

    paksha_name = "Kṛṣṇa" if ti[0] > 15 else "Śukla"
    st = shraddha_tithi(jd, place)
    shraddha_tithi_name = names["tithis"][str(st)]

    def strip_paksha(name):
        parts = [p.strip() for p in name.split(",")]
        stripped = [p.split("pakṣa ", 1)[1] if "pakṣa " in p else p for p in parts]
        return ", ".join(stripped)

    def tithi_num(t):
        return t if t <= 15 else t - 15

    tithi_name = strip_paksha(tithi_name)
    shraddha_tithi_name = strip_paksha(shraddha_tithi_name)

    tithi_nums = [tithi_num(ti[0])]
    if len(ti) == 4:
        tithi_nums.append(tithi_num(ti[2]))
    tithi_num_str = ", ".join(str(n) for n in tithi_nums)
    shraddha_tithi_num_str = str(tithi_num(st))

    xlat = to_itrans if use_itrans else lambda x: x

    return {
        "samvatsara": xlat(samvat_name),
        "masa": xlat(masa_name),
        "rtu": xlat(rtu_name),
        "paksha": xlat(paksha_name),
        "tithi": xlat(tithi_name),
        "tithi_num": tithi_num_str,
        "tithi_end": tithi_end,
        "shraddha_tithi": xlat(shraddha_tithi_name),
        "shraddha_tithi_num": shraddha_tithi_num_str,
        "nakshatra": xlat(nak_name),
        "nakshatra_end": nak_end,
        "yoga": xlat(yoga_name),
        "yoga_end": yoga_end,
        "karana": xlat(karana_name),
        "vara": xlat(vara_name),
        "sunrise": FORMAT_TIME(srise),
        "sunset": FORMAT_TIME(sset),
        "day_duration": FORMAT_TIME(day_dur),
        "kali_day": int(kday),
        "saka_year": sakayr,
        "kali_year": kyear,
    }


def print_single(date_str, city_name, city_info, tz_offset, pdata, use_itrans=False):
    xlat = to_itrans if use_itrans else lambda x: x
    w = 22
    print()
    print(f"  {xlat('Pañcāṅga for'):>{w}}  {date_str}  —  {city_name}")
    print(f"  {'Coordinates':>{w}}  {city_info['latitude']:.4f}°N, {city_info['longitude']:.4f}°E  (UTC{tz_offset:+.1f})")
    print(f"  {'─' * (w + 40)}")
    print(f"  {'Samvatsara':>{w}}  {pdata['samvatsara']}")
    print(f"  {xlat('Māsa'):>{w}}  {pdata['masa']}")
    print(f"  {xlat('Ṛtu'):>{w}}  {pdata['rtu']}")
    print(f"  {'─' * (w + 40)}")
    print(f"  {'Tithi':>{w}}  {pdata['tithi']:<30}  ends {pdata['tithi_end']}")
    print(f"  {xlat('Śrāddha Tithi'):>{w}}  {pdata['shraddha_tithi']}")
    print(f"  {xlat('Nakṣatra'):>{w}}  {pdata['nakshatra']:<30}  ends {pdata['nakshatra_end']}")
    print(f"  {'Yoga':>{w}}  {pdata['yoga']:<30}  ends {pdata['yoga_end']}")
    print(f"  {xlat('Karaṇa'):>{w}}  {pdata['karana']}")
    print(f"  {xlat('Vāra'):>{w}}  {pdata['vara']}")
    print(f"  {'─' * (w + 40)}")
    print(f"  {'Sunrise':>{w}}  {pdata['sunrise']}")
    print(f"  {'Sunset':>{w}}  {pdata['sunset']}")
    print(f"  {'Day duration':>{w}}  {pdata['day_duration']}")
    print(f"  {'─' * (w + 40)}")
    print(f"  {'Kali day':>{w}}  {pdata['kali_day']}")
    print(f"  {xlat('Śālivāhana śaka'):>{w}}  {pdata['saka_year']}")
    print(f"  {'Gata Kali':>{w}}  {pdata['kali_year']}")
    print()


def date_range(from_date, to_date):
    d = datetime(from_date.year, from_date.month, from_date.day)
    end = datetime(to_date.year, to_date.month, to_date.day)
    while d <= end:
        yield Date(d.year, d.month, d.day)
        d += timedelta(days=1)


def parse_month(month_str):
    try:
        dt = datetime.strptime(month_str, "%m-%Y")
        return dt.month, dt.year
    except ValueError:
        print(f"Invalid month format: '{month_str}'. Use MM-YYYY.", file=sys.stderr)
        sys.exit(1)


def register_pdf_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    candidates = [
        '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont('UnicodeFont', path))
            pdfmetrics.registerFont(TTFont('UnicodeFont-Bold', path))
            return 'UnicodeFont', 'UnicodeFont-Bold'
    return 'Helvetica', 'Helvetica-Bold'


def generate_pdf(city_name, city_info, month, year, names, use_itrans):
    import calendar as cal
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from xml.sax.saxutils import escape

    xlat = to_itrans if use_itrans else lambda x: x
    font, font_bold = register_pdf_font()

    cell_style = ParagraphStyle('cell', fontName=font, fontSize=7, leading=9)
    cell_end_style = ParagraphStyle('cell_end', fontName=font, fontSize=6,
                                    leading=8, textColor=colors.HexColor('#666666'))
    hdr_style = ParagraphStyle('hdr', fontName=font_bold, fontSize=8,
                               leading=10, textColor=colors.white)
    title_style = ParagraphStyle('title', fontName=font_bold, fontSize=14,
                                 leading=18, alignment=1)
    sub_style = ParagraphStyle('sub', fontName=font, fontSize=9,
                               leading=12, alignment=1,
                               textColor=colors.HexColor('#555555'))

    num_days = cal.monthrange(year, month)[1]
    weekday_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    headers = [
        Paragraph("Day", hdr_style),
        Paragraph("#", hdr_style),
        Paragraph("Tithi", hdr_style),
        Paragraph(escape(xlat("Nakṣatra")), hdr_style),
        Paragraph("Yoga", hdr_style),
        Paragraph(escape(xlat("Karaṇa")), hdr_style),
        Paragraph(escape(xlat("Māsa")), hdr_style),
        Paragraph("Sunrise", hdr_style),
        Paragraph("Sunset", hdr_style),
    ]
    data = [headers]

    day_weekdays = []
    for day in range(1, num_days + 1):
        date = Date(year, month, day)
        tz_offset = compute_tz_offset(city_info, date)
        place = Place(city_info['latitude'], city_info['longitude'], tz_offset)
        pdata = compute_panchanga(date, place, names, use_itrans)

        dt = datetime(year, month, day)
        wday = dt.weekday()
        day_weekdays.append(wday)

        def cell_with_end(name_key, end_key):
            n = escape(pdata[name_key])
            e = escape(pdata[end_key])
            return [Paragraph(n, cell_style), Paragraph(e, cell_end_style)]

        row = [
            Paragraph(weekday_short[wday], cell_style),
            Paragraph(str(day), cell_style),
            cell_with_end("tithi", "tithi_end"),
            cell_with_end("nakshatra", "nakshatra_end"),
            cell_with_end("yoga", "yoga_end"),
            Paragraph(escape(pdata['karana']), cell_style),
            Paragraph(escape(pdata['masa']), cell_style),
            Paragraph(pdata['sunrise'], cell_style),
            Paragraph(pdata['sunset'], cell_style),
        ]
        data.append(row)
        print(f"  {day:02d}-{month:02d}-{year} done", file=sys.stderr)

    col_widths = [16*mm, 10*mm, 58*mm, 48*mm, 42*mm, 26*mm, 28*mm, 20*mm, 20*mm]

    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#bdc3c7')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1a252f')),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]

    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(
                ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f5f6fa')))

    for i, wday in enumerate(day_weekdays, start=1):
        if wday == 6:  # Sunday
            style_cmds.append(
                ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fadbd8')))

    table.setStyle(TableStyle(style_cmds))

    filename = f"panchanga_{city_name}_{month:02d}_{year}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4),
                            leftMargin=8*mm, rightMargin=8*mm,
                            topMargin=10*mm, bottomMargin=10*mm)

    month_name = cal.month_name[month]
    title_text = escape(f"{xlat('Pañcāṅga')} — {month_name} {year}")
    coord_text = (f"{city_name}  |  "
                  f"{city_info['latitude']:.4f}°N, {city_info['longitude']:.4f}°E  |  "
                  f"{city_info['timezone']}")

    elements = [
        Paragraph(title_text, title_style),
        Paragraph(escape(coord_text), sub_style),
        Spacer(1, 4*mm),
        table,
    ]
    doc.build(elements)
    return filename


def main():
    parser = argparse.ArgumentParser(
        description="Dṛg-gaṇita Pañcāṅga — Hindu lunisolar calendar"
    )
    parser.add_argument("city", help="City name (e.g. Bangalore, Helsinki)")
    parser.add_argument("dates", nargs="+", metavar="date",
                        help="DD-MM-YYYY (single), DD-MM-YYYY DD-MM-YYYY (CSV range), "
                             "or MM-YYYY with --pdf")
    parser.add_argument("--itrans", action="store_true",
                        help="Use ITRANS transliteration instead of IAST Unicode")
    parser.add_argument("--pdf", action="store_true",
                        help="Generate monthly PDF calendar (date format: MM-YYYY)")
    parser.add_argument("--columns",
                        help="Comma-separated list of columns for CSV output")
    args = parser.parse_args()

    names, cities = load_data()
    city_name, city_info = resolve_city(args.city, cities)

    if args.pdf:
        if len(args.dates) != 1:
            print("--pdf requires exactly one month argument (MM-YYYY).", file=sys.stderr)
            sys.exit(1)
        month, year = parse_month(args.dates[0])
        filename = generate_pdf(city_name, city_info, month, year,
                                names, args.itrans)
        print(f"  Saved: {filename}", file=sys.stderr)

    elif len(args.dates) == 1:
        date = parse_date(args.dates[0])
        tz_offset = compute_tz_offset(city_info, date)
        place = Place(city_info['latitude'], city_info['longitude'], tz_offset)
        pdata = compute_panchanga(date, place, names, args.itrans)
        print_single(args.dates[0], city_name, city_info, tz_offset, pdata, args.itrans)

    elif len(args.dates) == 2:
        from_date = parse_date(args.dates[0])
        to_date = parse_date(args.dates[1])

        ALL_CSV_FIELDS = [
            "date", "samvatsara", "rtu", "masa", "paksha",
            "tithi", "tithi_num", "tithi_end",
            "shraddha_tithi", "shraddha_tithi_num",
            "nakshatra", "nakshatra_end",
            "yoga", "yoga_end", "karana", "vara",
            "sunrise", "sunset", "day_duration",
            "kali_day", "saka_year", "kali_year",
        ]
        COLUMN_ALIASES = {"karna": "karana"}

        if args.columns:
            requested = [c.strip() for c in args.columns.split(",")]
            fields = [COLUMN_ALIASES.get(c, c) for c in requested]
            unknown = [c for c in fields if c not in ALL_CSV_FIELDS]
            if unknown:
                print(f"Unknown columns: {', '.join(unknown)}", file=sys.stderr)
                print(f"Available: {', '.join(ALL_CSV_FIELDS)}", file=sys.stderr)
                sys.exit(1)
        else:
            fields = ALL_CSV_FIELDS

        writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()

        for date in date_range(from_date, to_date):
            tz_offset = compute_tz_offset(city_info, date)
            place = Place(city_info['latitude'], city_info['longitude'], tz_offset)
            pdata = compute_panchanga(date, place, names, args.itrans)
            pdata["date"] = f"{date.day:02d}-{date.month:02d}-{date.year:04d}"
            writer.writerow(pdata)
            print(f"  {pdata['date']} done", file=sys.stderr)

    else:
        print("Provide 1 date, 2 dates (range), or MM-YYYY with --pdf.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
