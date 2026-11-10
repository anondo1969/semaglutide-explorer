# Skeptical research review and corrective changes

Review performed: 2026-11-06. This review uses the uploaded DDLS 2026 workshop
materials and original project source, not external or inferred patient data.
The original workshop CSV has been retained unchanged (SHA-256 below).

## Review questions and findings

| Finding | Consequence | Correction | Test evidence |
| --- | --- | --- | --- |
| Published `0.00` per-1,000 rates may conceal positive counts. The CSV contains 12 such patient-rate rows and 3 dispensing-rate rows. | A plotted zero can be mistaken for no reported dispensing. | Show a contextual rounding note, show companion count and published rate together, and export rates with two decimal places. | `test_published_zero_rates_can_mean_positive_counts`, `test_rounded_zero_explained_and_count_visible` |
| Only the total age category was removed from age plots; new or overlapping age groups were previously accepted uncritically. | Future exports with e.g. a `5-19` category could make an invalid supposedly disjoint age chart. | Verify age interval boundaries before a demographic comparison; report overlaps/ambiguous labels without stopping unrelated panels. | `test_overlapping_age_group_is_reported_and_not_plotted`, `test_unknown_overlap_disables_only_demographic_view`, `test_invalid_age_interval_is_not_misrepresented` |
| An unexpected sex category could have appeared beside known mutually exclusive categories with no semantic review. | An added aggregate or ambiguous category could compromise comparisons. | Verify the known sex-specific categories; otherwise disable only the sex breakdown. | `test_unknown_sex_breakdown_is_blocked` |
| Raw count comparisons were not conspicuously qualified. | Population-size differences can mislead regional, demographic and temporal comparisons. | Show a warning whenever a count measure is selected; recommend the corresponding original per-1,000 rate. | `test_measure_changed_updates_ui_exports_and_charts` |
| Eighteen age groups were shown as vertically oriented bars with a crowded category axis. | Age labels may be unreadable at typical screen widths. | Use horizontal bars with youngest groups first, keeping all source values and categories unchanged. | `test_age_chart_is_horizontal_and_national_is_not_a_region_bar` |
| The view exports omitted unselected source measurements, and missing bars could occupy blank positions in rankings. | Rounding and missingness were difficult to audit independently. | Include all ten original source columns, plus selected measure/unit; omit missing values from bar rankings but retain those rows in exports. | `test_default_app_views_and_export`, `test_figures_change_with_measure_and_preserve_source_values` |
| The source's count/population relationship was not checked as a separate consistency check. | Altered rate values might go unnoticed even when plotting source values faithfully. | Warn if published rates disagree with corresponding count/population beyond two-decimal rounding; never replace source measurements with calculated values. | `test_rate_consistency_audit_preserves_published_numbers` |

None of these changes alters the defined scientific method. The application
still only filters and displays the supplied aggregate observations. No
forecasting, causal analysis, diagnosis, patient identification, category
summing, or derived outcome measure has been added.

## Independent comparisons with the original CSV

All reference values below were read from the source CSV as separate rows for
the reported year, region, both sexes and all ages; they were not created by
summing region or age records.

| Year | Region | Patients | Patients / 1,000 | Dispensings | Dispensings / 1,000 |
| --- | --- | ---: | ---: | ---: | ---: |
| 2025 | Riket | 260,677 | 24.62 | 1,306,902 | 123.44 |
| 2024 | Riket | 176,059 | 16.69 | 831,379 | 78.79 |
| 2025 | Jamtlands lan (label contains Swedish accents in CSV) | 4,496 | 33.85 | 21,206 | 159.64 |
| 2023 | Stockholms lan (label contains Swedish accents in CSV) | 31,235 | 12.80 | 134,485 | 55.12 |

The source includes 12,540 records from 2016-2025 inclusive; 22 geography
categories including `Riket`, three sex categories, and 19 age categories
including the all-ages record. No blank or duplicate key records were found.
The source rate columns agree with count / population * 1,000 within 0.00501,
consistent with two-decimal rounding. This arithmetic is a quality check only,
not a replacement for the published rates.

In 2016 and 2017, the provided national aggregate rows report zero patients
and dispensings; these zeros are source observations, not missing values. The
app does not infer the reason for this pattern.

**Scope caution:** the provided drug category is `A10BJ06 Semaglutid`.
It is not evidence for all semaglutide use, diagnoses, treatment outcomes,
indications, or hospital-administered supply. The source README explains the
limitations of the pharmaceutical register, missing personal identifiers,
and the special interpretation of dose dispensing.

## Verification actually performed

- Full data audit against the original CSV: record count, years, regions, sexes,
  age groups, drug category, duplicate key checks, numeric fields and rates.
- Byte-preservation check: original bundled CSV SHA-256
  `5596aabb1716a5a269f30465bf843ba397d758250243adc53457b4b13902bae6`.
- `python -m pytest -q`: **36 tests passed** using Python 3.13,
  pandas 2.2.3, Plotly 6.5.2 and pytest 9.0.2. The tests include real
  Plotly construction/serialization and simulated control interactions.
- `python scripts/preflight.py --strict`: passed.
- Source values, plotting inputs and exports were independently compared for
  multiple regions/years and each of the four measurements.

## What remains unverified

- An actual Streamlit server/browser session and responsive rendering on
  typical desktops/mobile devices. The Streamlit package was unavailable in
  this environment and package-index access did not offer it.
- A standalone Plotly preview could be generated, but browser navigation for
  local files and loopback HTTP was blocked by the runtime's administrator.
  The chart structure was tested programmatically, not visually signed off.
- A Docker image build, health check and SciLifeLab Serve deployment.
  Docker was not installed here. GitHub Actions has not been run.
- Behaviour under a future data extract with changed official source
  definitions; unknown/overlapping groups now trigger warnings, and the
  underlying source README must be rechecked by the researcher.
- Independent legal review of license and provenance before public deployment.

**Practical sign-off:** run the commands in the project README under Python
3.12, verify the three views in a real browser, download each panel's CSV,
then build/run Docker and review any warnings before publicly sharing.
