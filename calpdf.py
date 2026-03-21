#!/usr/bin/env python3
"""
Read a CSV of date ranges (Fromdate, toDate), generate a pañcāṅga CSV per range
via cli.py, render each with csv2cal.py, and merge into one PDF.

  python3 calpdf.py ranges.csv combined.pdf

Requires: pypdf (pip install pypdf)
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path

# Suppress csv2cal "Saved: ..." on stdout when driving programmatically.
_SUBPROCESS_QUIET = {"stdout": subprocess.DEVNULL}

CLI_COLUMNS = (
    "date,samvatsara,rtu,masa,paksha,tithi_num,shraddha_tithi_num,"
    "nakshatra,yoga,karna"
)


def _norm_key(k):
    return (k or "").strip().lower().replace(" ", "_")


def _parse_ranges(path):
    """Yield (from_str, to_str) in DD-MM-YYYY from CSV with header Fromdate, toDate."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Empty CSV or missing header.", file=sys.stderr)
            sys.exit(1)
        keymap = {_norm_key(h): h for h in reader.fieldnames}
        from_key = keymap.get("fromdate") or keymap.get("from_date")
        to_key = keymap.get("todate") or keymap.get("to_date")
        if not from_key or not to_key:
            print(
                "CSV must have columns Fromdate and toDate (or from_date / to_date).",
                file=sys.stderr,
            )
            sys.exit(1)
        for row in reader:
            a = (row.get(from_key) or "").strip()
            b = (row.get(to_key) or "").strip()
            if not a or not b:
                continue
            yield a, b


def _merge_pdfs(parts, dest):
    try:
        from pypdf import PdfWriter
    except ImportError:
        print("Install pypdf:  pip install pypdf", file=sys.stderr)
        sys.exit(1)
    writer = PdfWriter()
    for p in parts:
        writer.append(str(p))
    with open(dest, "wb") as outf:
        writer.write(outf)


def main():
    parser = argparse.ArgumentParser(
        description="Build one merged calendar PDF from a CSV of Fromdate/toDate ranges."
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        help="CSV with columns Fromdate, toDate (DD-MM-YYYY each).",
    )
    parser.add_argument(
        "output_pdf",
        type=Path,
        help="Path for the merged PDF.",
    )
    args = parser.parse_args()

    if not args.input_csv.is_file():
        print(f"Not found: {args.input_csv}", file=sys.stderr)
        sys.exit(1)

    root = Path(__file__).resolve().parent
    cli_py = root / "cli.py"
    csv2cal_py = root / "csv2cal.py"
    for p in (cli_py, csv2cal_py):
        if not p.is_file():
            print(f"Missing script: {p}", file=sys.stderr)
            sys.exit(1)

    tmp_csv = Path("/tmp/temp.csv")
    page_pdfs = []

    try:
        for i, (from_date, to_date) in enumerate(_parse_ranges(args.input_csv)):
            cmd_cli = [
                sys.executable,
                str(cli_py),
                "--itrans",
                "--columns",
                CLI_COLUMNS,
                "mumbai",
                from_date,
                to_date,
            ]
            with open(tmp_csv, "w", encoding="utf-8") as out:
                r = subprocess.run(
                    cmd_cli,
                    cwd=str(root),
                    stdout=out,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            if r.returncode != 0:
                print(r.stderr, file=sys.stderr)
                sys.exit(r.returncode)

            out_pdf = Path(f"/tmp/out{i}.pdf")
            r2 = subprocess.run(
                [
                    sys.executable,
                    str(csv2cal_py),
                    str(tmp_csv),
                    "-o",
                    str(out_pdf),
                ],
                cwd=str(root),
                stderr=subprocess.PIPE,
                text=True,
                **_SUBPROCESS_QUIET,
            )
            if r2.returncode != 0:
                print(r2.stderr, file=sys.stderr)
                sys.exit(r2.returncode)
            page_pdfs.append(out_pdf)
            print(f"  Page {i + 1}: {from_date} … {to_date} -> {out_pdf.name}", file=sys.stderr)

        if not page_pdfs:
            print("No data rows in CSV.", file=sys.stderr)
            sys.exit(1)

        args.output_pdf.parent.mkdir(parents=True, exist_ok=True)
        _merge_pdfs(page_pdfs, args.output_pdf)
        print(f"Saved: {args.output_pdf.resolve()}", file=sys.stderr)
    finally:
        if tmp_csv.exists():
            try:
                tmp_csv.unlink()
            except OSError:
                pass
        for p in page_pdfs:
            try:
                p.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
