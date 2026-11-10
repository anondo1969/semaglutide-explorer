"""Stdlib-only source and Docker contract check; safe before installing packages."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "app/app.py", "app/data_processing.py", "app/charts.py", "app/requirements.txt",
    "app/data/socialstyrelsen_semaglutid_2016_2025.csv",
    "Dockerfile", ".github/workflows/build-image.yml", ".streamlit/config.toml", "README.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on every failed check")
    args = parser.parse_args()
    failures = []
    for relative in sorted(EXPECTED):
        if not (ROOT / relative).is_file():
            failures.append(f"Missing {relative}")

    dockerfile = ROOT / "Dockerfile"
    if dockerfile.is_file():
        content = dockerfile.read_text()
        for essential in ("python:3.12-slim", "-u 1000", "USER appuser", "EXPOSE 8501", "0.0.0.0", "_stcore/health", "app/data/"):
            if essential not in content:
                failures.append(f"Dockerfile missing {essential!r}")

    src = ROOT / "app/data/socialstyrelsen_semaglutid_2016_2025.csv"
    if src.is_file():
        with src.open(encoding="utf-8-sig", newline="") as handle:
            title = handle.readline().strip()
            if title != "Läkemedelsstatistik":
                failures.append(f"Unexpected CSV title: {title!r}")
            reader = csv.DictReader(handle, delimiter=";")
            actual_headers = set(reader.fieldnames or [])
            wanted = {"År", "Läkemedel", "Region", "Kön", "Ålder", "Antal patienter", "Patienter/1000 invånare", "Antal expedieringar", "Expedieringar/1000 invånare", "Befolkning"}
            if wanted - actual_headers:
                failures.append(f"Missing source headers: {sorted(wanted - actual_headers)}")
            years = set()
            national = []
            n = 0
            for row in reader:
                n += 1
                years.add(row["År"])
                if row["År"] == "2025" and row["Region"] == "Riket" and row["Kön"] == "Båda könen" and row["Ålder"].replace("\u00ad", "-") == "0-85+":
                    national.append(row)
            if n == 0 or years != set(map(str, range(2016, 2026))):
                failures.append(f"Unexpected rows/years: count={n}; years={sorted(years)}")
            if len(national) != 1 or national[0]["Antal patienter"] != "260677" or national[0]["Patienter/1000 invånare"] != "24,62":
                failures.append("National 2025 sanity-check row mismatch")
            print(f"Source: {n:,} rows; years {', '.join(sorted(years))}; national 2025 sanity-check {'OK' if not failures else 'needs review'}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1 if args.strict else 0
    print("Preflight passed: files, source sanity check, and Streamlit container profile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
