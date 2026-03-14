# Dṛg-gaṇita Pañcāṅga

Hindu lunisolar calendar based on the Swiss Ephemeris.

Forked from https://github.com/webresh/drik-panchanga and modernized.

## Features

- Daily pañcāṅga: tithi, nakṣatra, yoga, karaṇa, vāra, sunrise/sunset, and more
- Śrāddha tithi (based on aparāhṇa kāla)
- CSV export for date ranges with selectable columns
- Monthly PDF calendar generation
- Calendar-grid PDF from CSV (`csv2cal.py`)
- wxPython GUI with prev/next day navigation
- IAST (Unicode) and ITRANS transliteration

## Installation

```
pip install pyswisseph pytz reportlab wxPython
```

Clone the repository and run from the project directory:

```
git clone <repo-url>
cd drikganita
```

## CLI Usage

### Single-day pañcāṅga

```
python3 cli.py <city> DD-MM-YYYY
```

Example:

```
python3 cli.py mumbai 14-03-2026
```

### Date range (CSV output)

Provide two dates to get CSV on stdout:

```
python3 cli.py bangalore 01-03-2026 31-03-2026 > march.csv
```

Select specific columns:

```
python3 cli.py bangalore 01-03-2026 31-03-2026 --columns date,tithi,nakshatra,shraddha_tithi
```

Available columns: `date`, `samvatsara`, `rtu`, `masa`, `paksha`, `tithi`,
`tithi_num`, `tithi_end`, `shraddha_tithi`, `shraddha_tithi_num`, `nakshatra`,
`nakshatra_end`, `yoga`, `yoga_end`, `karana`, `vara`, `sunrise`, `sunset`,
`day_duration`, `kali_day`, `saka_year`, `kali_year`.

### ITRANS output

Add `--itrans` for ASCII-safe transliteration:

```
python3 cli.py helsinki 14-03-2026 --itrans
```

### Monthly PDF

```
python3 cli.py mumbai 03-2026 --pdf
```

Generates `panchanga_Mumbai_03_2026.pdf` in the current directory.

## Generating a PDF Calendar

This is a two-step process: first export a CSV for a date range, then convert
it to a calendar-grid PDF using `csv2cal.py`.

**Step 1** — Generate CSV with the columns needed for the calendar:

```
python3 cli.py --itrans --columns "date,samvatsara,rtu,masa,paksha,tithi_num,shraddha_tithi_num,nakshatra,yoga,karna" mumbai 20-03-2026 17-04-2026 > /tmp/cal.csv
```

**Step 2** — Convert the CSV to a calendar-grid PDF:

```
python3 csv2cal.py /tmp/cal.csv -o /tmp/out.pdf
```

Both steps combined in one command:

```
python3 cli.py --itrans --columns "date,samvatsara,rtu,masa,paksha,tithi_num,shraddha_tithi_num,nakshatra,yoga,karna" mumbai 20-03-2026 17-04-2026 > /tmp/cal.csv && python3 csv2cal.py /tmp/cal.csv -o /tmp/out.pdf
```

Notes:
- The date range typically spans one Hindu lunar month (new moon to new moon).
- `--itrans` uses ASCII-safe transliteration which renders better in PDFs.
- `karna` is an alias for `karana`.
- If `-o` is omitted, the output defaults to `<csv-name>_calendar.pdf`.

## GUI

```
python3 gui.py
```

- Enter a city name and date, then click **Show Pañcāṅga**.
- Use the **◀ Prev Day** / **Next Day ▶** buttons to navigate.
- Latitude, longitude, and timezone are auto-filled from the city database
  but can be edited manually for custom locations.

## License

GNU Affero General Public License v3.0 — see the source files for details.
