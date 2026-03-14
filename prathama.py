#!/usr/bin/env python3
"""Print CSV of all Śukla pakṣa prathamā dates in a given range."""

import argparse
import csv
import json
import sys
import difflib
import unicodedata
from datetime import datetime, timedelta
from pytz import timezone

from panchanga import *

FORMAT_TIME = lambda t: "%02d:%02d:%02d" % (t[0], t[1], t[2])
SHUKLA_PRATHAMA = 1

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


def main():
    parser = argparse.ArgumentParser(
        description="List all Śukla pakṣa prathamā dates in a range (CSV)")
    parser.add_argument("city", help="City name (e.g. Bangalore, Mumbai)")
    parser.add_argument("from_date", help="Start date (DD-MM-YYYY)")
    parser.add_argument("to_date", help="End date (DD-MM-YYYY)")
    parser.add_argument("--itrans", action="store_true",
                        help="Use ITRANS transliteration instead of IAST Unicode")
    args = parser.parse_args()

    xlat = to_itrans if args.itrans else lambda x: x

    names, cities = load_data()
    city_name, city_info = resolve_city(args.city, cities)
    from_date = parse_date(args.from_date)
    to_date = parse_date(args.to_date)

    fields = ["date", "samvatsara", "masa", "rtu",
              "tithi", "nakshatra", "yoga", "karana"]
    writer = csv.DictWriter(sys.stdout, fieldnames=fields)
    writer.writeheader()

    d = datetime(from_date.year, from_date.month, from_date.day)
    end = datetime(to_date.year, to_date.month, to_date.day)

    while d <= end:
        date = Date(d.year, d.month, d.day)
        tz_offset = compute_tz_offset(city_info, date)
        place = Place(city_info['latitude'], city_info['longitude'], tz_offset)
        jd = gregorian_to_jd(date)
        ti = tithi(jd, place)

        is_match = (ti[0] == SHUKLA_PRATHAMA or
                    (len(ti) == 4 and ti[2] == SHUKLA_PRATHAMA))

        if is_match:
            mas = masa(jd, place)
            nak = nakshatra(jd, place)
            yog = yoga(jd, place)
            kar = karana(jd, place)

            masa_name = names["masas"][str(mas[0])]
            if mas[1]:
                masa_name = "Adhika " + masa_name
            rtu_name = names["ritus"][str(ritu(mas[0]))]
            samvat_name = names["samvats"][str(samvatsara(jd, mas[0]))]

            date_str = f"{d.day:02d}-{d.month:02d}-{d.year:04d}"
            writer.writerow({
                "date": date_str,
                "samvatsara": xlat(samvat_name),
                "masa": xlat(masa_name),
                "rtu": xlat(rtu_name),
                "tithi": xlat(names["tithis"][str(SHUKLA_PRATHAMA)]),
                "nakshatra": xlat(names["nakshatras"][str(nak[0])]),
                "yoga": xlat(names["yogas"][str(yog[0])]),
                "karana": xlat(names["karanas"][str(kar[0])]),
            })
            print(f"  {date_str}  {xlat(masa_name)}", file=sys.stderr)

        d += timedelta(days=1)


if __name__ == "__main__":
    main()
