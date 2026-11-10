# Maintainer notes for coding assistants

This project implements the supplied DDLS 2026 semaglutide brief. The user-supplied `docs/SOURCE_README.md` and bundled original CSV, then the current SciLifeLab Serve Streamlit template, take precedence over assumptions.

- Preserve the original Swedish source labels and source definitions. Normalization is for display only.
- Never sum patient counts across years, drugs, overlapping sex/age groups or national+regional rows. Never compute national rates by averaging regional rates.
- Keep all science and data-selection logic in `app/data_processing.py`, plotting in `app/charts.py`, and controls in `app/app.py`.
- Add tests before adding derived measures; they require a documented formula and researcher validation.
- Report missing data, malformed source rows and duplicate source keys explicitly; do not silently delete/correct source rows.
- The app is descriptive, does not infer an indication/diagnosis, and cannot be used for treatment advice.
- For Docker changes, follow [SciLifeLab Serve's Streamlit profile](https://github.com/ScilifelabDataCentre/serve-app-template/blob/main/profiles/streamlit/Dockerfile): port 8501, 0.0.0.0 bind, UID 1000, amd64 build, health check, no telemetry.
- Do not add credentials, private data, user databases or telemetry. Do not publish or deploy without user instruction.
