# Coding-agent prompt 1: Semaglutide Data Explorer (Streamlit)

> Copy this entire prompt into your coding assistant. It is self-contained, and can also replace the `DESCRIBE YOUR IDEA` part of the SciLifeLab Serve app template README prompt. You must give the agent access to the workshop materials repository or its `semaglutid/` folder.

## Role and task

Act as a careful research software engineer. Build a **small, elegant, scientifically faithful Streamlit dashboard** named **Semaglutide Use in Sweden: Interactive Explorer**. The purpose is to help researchers and other interested users explore **reported aggregate semaglutide dispensing statistics**, not to perform clinical prediction or give medical advice.

Use these sources as authoritative project inputs:

- Workshop materials: https://github.com/ScilifelabDataCentre/ddls-2026-workshop-materials
- Data directory: `semaglutid/`
- Scientific context: `semaglutid/README.md`
- Data file: `semaglutid/socialstyrelsen_semaglutid_2016_2025.csv`
- Web app template: https://github.com/ScilifelabDataCentre/serve-app-template

Read the relevant README files and the template's current instructions before starting. **If the repositories or CSV are not available to your environment, tell me exactly which files you need and how I should provide them. Do not invent data or pretend you accessed files.** If you have filesystem/network access, clone or inspect the repositories yourself. Create the finished application in a separate project directory; do not modify the original workshop materials.

The Serve template is useful for good application engineering even if the app is never deployed on SciLifeLab Serve. Use its simplicity, maintainability, containerization, and security guidance. **Hosting on Serve is optional**; a correct locally running app comes first.

## 1. Scientific specification: already decided

**Research question:** How have reported semaglutide dispensing statistics changed from 2016 through 2025 in Sweden, and how do they vary by geography, sex, and age group?

**Input:** The existing Socialstyrelsen aggregate CSV provided by the workshop. It is not individual patient data.

**Output:** Filtered published observations; descriptive trend and comparison plots; clearly labeled values and a download of the filtered data.

**Method:** Read, subset, display, and compare the supplied observations. No forecasting, no causal analysis, no clinical classification, and no invented methodology. When a new derived metric is requested, explain and validate its formula before implementing it.

**Accountability:** Preserve the published definitions and their caveats. The researcher remains responsible for whether the analysis and conclusions are appropriate. Ask for clarification before making an important scientific assumption.

## 2. Inspect and validate the CSV BEFORE implementing the web interface

Read `semaglutid/README.md` and inspect the actual CSV, not just its first few rows. The source file has a title line before the header, is semicolon-separated, uses decimal commas, and includes Swedish text/age labels. Handle its encoding, delimiters, numeric types, and possible nonstandard hyphens correctly.

The expected source columns include:

- `År` (year)
- `Läkemedel` (drug)
- `Region`
- `Kön` (sex)
- `Ålder` (age group)
- `Antal patienter` (number of patients)
- `Patienter/1000 invånare` (patients per 1,000 inhabitants)
- `Antal expedieringar` (number of dispensings)
- `Expedieringar/1000 invånare` (dispensings per 1,000 inhabitants)
- `Befolkning` (population)

Do not silently rename variables without keeping a documented mapping. Detect the actual levels present in the file instead of assuming a particular ordering or exact spelling of an all-ages category. Make the application resilient to extra rows, different Unicode hyphen characters, and missing measurements.

**Critical aggregation rules:**

1. `Riket` is an existing national summary category; do not reconstruct it by averaging region rates.
2. `Båda könen` and the all-ages group are existing aggregate records; do not mix them with sex-specific or age-specific rows when calculating totals or plotting rankings.
3. A patient count refers to a person who dispensed the medicine at least once during the reporting year, not necessarily continuous treatment.
4. Do not sum patients across years, overlapping age groups, overlapping drug groups, or other non-independent categories.
5. When comparing populations of different sizes, use the source's per-1,000 measures unless another justified comparison is specified.
6. A dispensing is not the same thing as a unique patient. The register does not say why the medication was prescribed.
7. Do not infer diagnoses, indications, treatment outcomes, or causes of trends.

Write small, testable, framework-independent functions for loading, validating, filtering, selecting one measurement, and preparing data for each plot. **Implement and test these core functions first, then build the interface.**

## 3. Data checks to implement

- Verify that the source contains the expected year coverage and inspect the region, sex, age, and medication categories actually present.
- Confirm the 2025 row for `Riket`, `Båda könen`, and the all-ages category includes **260677 patients** and **24.62 patients per 1,000 inhabitants**, using parsed data rather than hard-coded display values.
- Check that rate columns are parsed as decimal numbers, not text (for example, `24,62` -> `24.62`).
- Check for duplicate records at the relevant key level, missing fields, and unexpected categories; report findings rather than quietly deleting rows.
- Check that filtering for a single region/year/sex/age produces the correct source observation.
- Check that changing the selected measurement updates values, units, plots, and downloadable rows consistently.
- If a filter selection has no data, show a helpful message instead of a broken chart.

## 4. Build the Streamlit interface AFTER core validation

**App title:** Semaglutide Use in Sweden: Interactive Explorer

Aim for one readable page with a short introduction, controls in a sidebar or compact filter area, plots, a data table, and a source/limitations section.

### Controls

- Year range; default to the full available period (2016-2025 if the file confirms it).
- Region selector, initially `Riket`. Allow multiple regions for clearly labeled comparisons.
- Sex selector, initially `Båda könen`.
- Age group selector, initially the all-ages category found in the file.
- Measurement selector: patients per 1,000 (default); number of patients; dispensings per 1,000; or number of dispensings.

### Outputs

1. **Trend plot:** Interactive line plot across years. The legend identifies each region, and the y-axis always includes the chosen measure and unit.
2. **Regional comparison:** For one selected year, sex, age group, and measure, show a bar chart for the individual regions. Exclude `Riket` from the set of regions being ranked; if shown, show it as a separate, clearly identified reference.
3. **Age/sex exploration:** One compact view for comparing age groups or sexes at a selected year and region. Never include aggregate groups in the same set as their constituent groups without explicit labeling.
4. **Summary values:** A few context-sensitive cards derived from exactly the current selection, not from arbitrary summed records.
5. **Data table and download:** A table of the observations behind the current view and a CSV download of those rows. Keep provenance and original measurement definitions available.
6. **Interpretation panel:** Plain-language data definitions, caution about interpretation, and direct links to the source/README.

Choose simple Streamlit components, pandas, and one lightweight plotting library. Make the interface visually polished without complex CSS, databases, authentication, unnecessary pages, or features unrelated to the research question.

## 5. Independent interface verification

After the app works, behave like a skeptical researcher:

- Compare at least three plotted/table values with the original CSV, including the 2025 national all-ages/both-sexes patient rate of 24.62.
- Ensure filters actually affect every relevant plot and the download in the intended way.
- Verify that national values are never computed by unweighted averaging of regions.
- Verify that no count is inflated through summing overlapping categories.
- Inspect labels, units, empty states, odd age group labels, and unexpected input.
- Add automated tests for the core parsing/filtering functions; do not depend on Streamlit UI tests for scientific validation.

## 6. Packaging and reproducibility

Follow the **current** SciLifeLab Serve app template README and its Streamlit profile, rather than inventing a custom deployment architecture. Keep core data logic outside the UI code. Produce a reproducible application with a minimal dependency list, bundled public aggregate dataset, a Dockerfile, and clear local/Docker instructions. If the template specifies a GitHub Actions build workflow and Serve instructions, include them in a straightforward form; **do not deploy or publish automatically**.

Do not commit secrets or add patient-level or sensitive data. If you cannot test Docker here, say so explicitly and supply commands for me to verify on my machine.

## 7. Execution order and expected response

Work in this order and report progress after each meaningful milestone:

1. Read the workshop README, CSV and relevant template guidance. List available files and any missing prerequisites.
2. Inspect the data and summarize fields, levels, units, coverage, and caveats.
3. Implement and test the framework-independent processing functions.
4. Create the Streamlit UI that consumes those functions.
5. Run it locally, exercise representative selections, fix errors, and verify outputs against the CSV.
6. Prepare the Docker setup, tests, and concise README. Test Docker if available.
7. Summarize what was actually tested, what remains unverified, and exactly how I can run it.

Deliver a **working first version**, not an elaborate prototype. Make only justified decisions. If the scientific specification conflicts with the source README, explain the conflict and ask before changing the intended method.
