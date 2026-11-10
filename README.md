# Semaglutide Use in Sweden: Interactive Explorer

A small, reproducible **Streamlit dashboard for descriptive exploration of published aggregate semaglutide dispensing statistics** from Sweden's National Board of Health and Welfare (Socialstyrelsen). The app reads the real workshop CSV supplied in `app/data/`, without fetching external data or generating any estimates.

This dashboard is **not** designed for clinical prediction, medical advice, causal inference, or identifying prescribing indications.

## What you can explore

- **Time trends (2016–2025):** multiple separately drawn regions, including the original `Riket` national record.
- **Regional comparison:** each of 21 individual regions for a chosen year/sex/age group, with `Riket` shown *only* as an independently published dashed reference line.
- **Age/sex comparison:** verified non-overlapping age categories (not the all-ages total) or known sex-specific categories (not the both-sexes total) at a chosen year and region. Unexpected or overlapping categories disable only the unsafe breakdown.
- **Four measurements:** reported patients per 1,000 inhabitants; number of patients; dispensings per 1,000; number of dispensings.
- **Data and downloads:** exact observations backing each panel, with all ten original Swedish source columns, the selected measurement/units, and both the published count and rate for rounding checks; no summing or averaging.

The sidebar controls the trend view's year range, region(s), sex, age and measurement. The *comparison year* is shared by the regional and demographic views. The regional chart **intentionally displays all individual regions**, regardless of trend region selection; the demographic view has its own single-region selector. Each panel has its **own matching CSV download**. Data downloads use semicolons, decimal commas, and UTF-8 BOM for compatibility with Swedish spreadsheet software.

**Interpretation safeguards:** source per-1,000 rates are rounded to two decimals, so `0.00` need not imply zero patients/dispensings; the UI flags such records. Comparisons using raw counts are explicitly marked as population-size dependent. The supplied extract is only the source category `A10BJ06 Semaglutid`, not a census of all semaglutide administration or prescribing indications.

## Run locally

Requires **Python 3.12**. From this project directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate     # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python scripts/preflight.py --strict
python -m pytest -q
streamlit run app/app.py --server.port=8501 --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

Open <http://localhost:8501>. Stop with `Ctrl+C`. To install runtime dependencies only, use `pip install -r app/requirements.txt`. The project uses pandas, Plotly and Streamlit; all runtime dependencies are pinned in `app/requirements.txt`.

### Checks to perform in the browser

1. Default: `Riket` / `Båda könen` / all ages / patients per 1,000 / 2025 should show **24.62**, and the original national patient count should be **260677** when switching to *Number of patients*.
2. Switch to *Number of dispensings*: the 2025 national value is **1306902**; the line, axis, data table, and downloaded `Värde` should all change.
3. Add two regions for the trend; ensure separate lines appear, without their patient counts being combined. Compare a plotted point with the source CSV.
4. Check that the 2025 regional chart has 21 region bars, and only a dashed `Riket` reference (not a 22nd bar).
5. Switch age/sex comparison modes; there should be 18 constituent age groups or two sex-specific rows, never the overlapping total.
6. Deselect all regions: the trend should show a helpful no-data message, not an exception.
7. Select the 2024 all-sexes national age group `5-9` (displayed with a dash) and *Patients per 1,000*: the source rate is `0.00` but the original patient count is `2`; a rounding note should be shown, and the CSV should preserve `0,00`.
8. Select *Number of patients*: confirm the warning about differing population sizes. Download each panel's CSV and verify it contains the ten original fields, plus displayed age and selected measure/unit.

The automated tests check these behaviors by exercising the processing/Plotly code and app selection logic with a simulated Streamlit interface. A **real browser check** still requires installing and running Streamlit.

## Run with Docker

Adapted from the [current SciLifeLab Serve Streamlit Docker profile](https://github.com/ScilifelabDataCentre/serve-app-template/blob/main/profiles/streamlit/Dockerfile). It uses a Python 3.12 slim image, non-root UID 1000, a health check at `/_stcore/health`, and Streamlit bound to `0.0.0.0:8501` with telemetry disabled.

```bash
docker build --platform linux/amd64 -t semaglutide-explorer:0.1.0 .
docker run --rm -p 8501:8501 semaglutide-explorer:0.1.0
```

Open <http://localhost:8501>. Stop with `Ctrl+C`. An equivalent smoke check is `curl -fsS http://localhost:8501/_stcore/health` after the server starts.

## Optionally publish through GitHub and SciLifeLab Serve

**No deployment, publication or remote push is performed by this project.** To publish later:

1. Review the scientific limitations, data reuse conditions, source license, and all local tests. Create a **public** GitHub repository for this app, then push the project to its `main` branch (do not push secrets). The included `.github/workflows/build-image.yml` tests the project and builds a `linux/amd64` image in GitHub Container Registry (GHCR), using a unique timestamp/SHA/run tag rather than a mutable `latest` tag.
2. In the repository's GitHub Actions output, find the published image name (`ghcr.io/OWNER/REPO:UNIQUE-TAG`). Set the GHCR package visibility to **Public** so the hosting platform can fetch it.
3. On [SciLifeLab Serve](https://serve.scilifelab.se/), choose your project, create an application, provide that **exact public image tag**, set application port **8501**, and enter the public GitHub repository as the source-code URL. Start with a review-only visibility option as appropriate and verify the deployed interface. Use a **new** image tag for every subsequent deployment.

Consult the current [Serve app template](https://github.com/ScilifelabDataCentre/serve-app-template) and [Serve hosting documentation](https://serve.scilifelab.se/docs/application-hosting/streamlit/) before deployment because platform requirements may change.

## Data and scientific interpretation

- **Primary public source:** [Socialstyrelsen medication-statistics portal](https://sdb.socialstyrelsen.se/if_lak/val.aspx).
- **Exact workshop dataset and README:** [SciLifeLab DDLS 2026 workshop materials](https://github.com/ScilifelabDataCentre/ddls-2026-workshop-materials/tree/main/semaglutid). The original source README is included in `docs/SOURCE_README.md`; workshop-wide notes in `docs/WORKSHOP_README.md`.
- **Bundled source CSV:** `app/data/socialstyrelsen_semaglutid_2016_2025.csv` (12,540 records). SHA-256: `5596aabb1716a5a269f30465bf843ba397d758250243adc53457b4b13902bae6`.
- **Details of the validation:** `docs/DATA_AUDIT.md`.
- **Independent scientific/implementation review and fixes:** `docs/RESEARCH_REVIEW.md`.

The source has a title line before the column header, is semicolon-delimited, and uses decimal commas and Unicode soft hyphens in age categories. The loader preserves all original Swedish names and keys, adds only the documented `Ålder (visning)` label and the selected `Värde`/`Mått`/`Enhet`, and leaves missing measurements as missing values. No unknown category is silently aggregated or discarded. A source consistency warning can be raised if count/population and the published rate disagree by more than two-decimal rounding. **Published rates are always used for plotting, not recomputed from counts.**

| Swedish CSV variable | Meaning in the app |
|---|---|
| `År` | Reporting year |
| `Läkemedel` | Drug category (this CSV contains `A10BJ06 Semaglutid`) |
| `Region` | Geography (`Riket` is the source national summary) |
| `Kön` | Sex (`Båda könen` is a source aggregate) |
| `Ålder` | Age group (all ages: `0­85+`, with a soft hyphen in the source) |
| `Antal patienter` | Unique people dispensing at least once during the year, not continuous treatment |
| `Patienter/1000 invånare` | Published patient count per 1,000 inhabitants |
| `Antal expedieringar` | Number of dispensing events, **not** unique patients |
| `Expedieringar/1000 invånare` | Published dispensing events per 1,000 inhabitants |
| `Befolkning` | Population denominator field as provided by Socialstyrelsen |

**Limitations from the source README:** the drug register does not identify the reason for prescribing. Over-the-counter medications, certain healthcare-administered medicines and records with missing identifiers can affect interpretation. Dispensing event counts depend on prescription and dose-dispensing arrangements. Use per-1,000 source values for population comparisons. Neither patient counts nor aggregated data categories should be summed across years, drugs, or overlapping groups. Even high values for specific small age groups may be affected by how population and age are defined. The data alone cannot establish diagnoses, outcomes or causes of trends.

## Project layout

```text
app/
  app.py                        # Streamlit UI only
  charts.py                     # Standalone Plotly chart functions
  data_processing.py            # Loading, validation, filtering, safe chart data
  data/socialstyrelsen_semaglutid_2016_2025.csv
  requirements.txt
docs/SOURCE_README.md              # Unmodified source scientific context
docs/WORKSHOP_README.md            # Workshop instructions
docs/DATA_AUDIT.md
docs/RESEARCH_REVIEW.md           # Skeptical scientific review, fixes and verification limits
tests/test_data_processing.py     # Scientific integrity tests
tests/test_charts_and_ui.py       # Plotly + simulated Streamlit interaction tests
scripts/preflight.py              # Stdlib-only data/container audit
.streamlit/config.toml             # Lightweight Streamlit color/theme settings
Dockerfile                        # Based on Serve's Streamlit profile
.github/workflows/build-image.yml # Optional GHCR build, no manual publish here
requirements-dev.txt
```

## Testing status after scientific review (2026-11-06)

The CSV was read from the supplied ZIP and independently validated against the original, including the published 2025 national row and three other regional/year values. **36 automated tests passed** with Python 3.13, pandas 2.2.3, Plotly 6.5.2, and pytest 9.0.2. The source preflight also passed. The runtime target is Python 3.12, so it must also be tested there. Streamlit could not be installed here because it was unavailable through the configured package index; Docker was not installed and browser navigation was blocked. **Actual Streamlit server startup, visual browser QA, Docker build, GitHub Actions, and Serve deployment remain unverified.** See `docs/RESEARCH_REVIEW.md` for evidence and limitations.

## Software license and data attribution

See `LICENSE` for the MIT software license accompanying the SciLifeLab workshop materials. **This does not by itself determine the independent reuse/license conditions of Socialstyrelsen's underlying statistics.** Review the source portal's terms and confirm appropriate data licensing/attribution before republishing the dataset or deploying publicly. Credit the Socialstyrelsen public statistics and the SciLifeLab DDLS 2026 workshop materials when using this app.
