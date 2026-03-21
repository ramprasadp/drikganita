#!/usr/bin/env python3
"""
From a start date, walk forward day by day until the saṃvatsara index changes.
Emit one CSV row per civil day where tithi at sunrise is Śukla Prathamā (tithi 1).
The second column is the civil date immediately before the next row’s date (empty on
the last row).

Default location is Mumbai; pass --city to use another entry from cities.json.
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta

from panchanga import Date, gregorian_to_jd, Place, tithi, masa, samvatsara

from cli import load_data, resolve_city, compute_tz_offset, parse_date


def fmt_date(d):
    return f"{d.day:02d}-{d.month:02d}-{d.year:04d}"


def date_add_one(d):
    dt = datetime(d.year, d.month, d.day) + timedelta(days=1)
    return Date(dt.year, dt.month, dt.day)


def date_sub_one(d):
    dt = datetime(d.year, d.month, d.day) - timedelta(days=1)
    return Date(dt.year, dt.month, dt.day)


def main():
    parser = argparse.ArgumentParser(
        description="CSV of Śukla Prathamā dates from START until saṃvatsara changes "
        "(date; day before next row’s date)."
    )
    parser.add_argument(
        "start_date",
        help="Start date DD-MM-YYYY; scan forward until the saṃvatsara index "
        "differs from this day’s value.",
    )
    parser.add_argument(
        "--city",
        default="Mumbai",
        help="City from cities.json (default: Mumbai).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write CSV to this file instead of stdout.",
    )
    args = parser.parse_args()

    _, cities = load_data()
    _, city_info = resolve_city(args.city, cities)
    start = parse_date(args.start_date)
    tz_offset = compute_tz_offset(city_info, start)
    place = Place(city_info["latitude"], city_info["longitude"], tz_offset)

    start_sv = None
    prathamas = []

    d = start
    max_days = 450
    for _ in range(max_days):
        jd = gregorian_to_jd(d)
        mas = masa(jd, place)
        sv = samvatsara(jd, mas[0])
        if start_sv is None:
            start_sv = sv
        elif sv != start_sv:
            break

        ti = tithi(jd, place)[0]
        if ti == 1:
            prathamas.append(d)

        d = date_add_one(d)
    else:
        print(
            f"Stopped after {max_days} days without saṃvatsara change; "
            "extend max_days if needed.",
            file=sys.stderr,
        )

    fields = ["date", "day_before_next"]
    out = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    try:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        n = len(prathamas)
        for i, day in enumerate(prathamas):
            if i + 1 < n:
                before_next = fmt_date(date_sub_one(prathamas[i + 1]))
            else:
                before_next = ""
            writer.writerow({"date": fmt_date(day), "day_before_next": before_next})
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
