# Audit of the supplied semaglutide CSV

**Input:** `ddls-2026-workshop-materials/semaglutid/socialstyrelsen_semaglutid_2016_2025.csv`, extracted byte-for-byte from the user's uploaded workshop ZIP; processing takes place in a separate app project directory. The associated scientific context is preserved in `SOURCE_README.md`.

## Structural checks

- CSV title line: `Läkemedelsstatistik` before the actual header.
- Encoding: UTF-8; separator: `;`; decimals: comma (example `24,62`).
- Records: **12,540**, all with 10 source columns.
- Coverage: 10 years, **2016–2025** inclusive (1,254 records per year).
- Drug: one category, **`A10BJ06 Semaglutid`**.
- Geography: **21 named Swedish regions** plus the pre-existing `Riket` national category.
- Sex: `Män`, `Kvinnor`, `Båda könen` (the latter is an aggregate).
- Age: **18 disjoint constituent age groups** (`0­4` through `85+`) plus **`0­85+`** (all ages); the separator in the source labels is a Unicode soft hyphen, displayed in the app as an en dash.
- Missing or empty source fields: **0**; duplicate `(År, Läkemedel, Region, Kön, Ålder)` keys: **0**.
- Numeric values: published per-1,000 rates successfully parsed as decimals, and count/population fields as whole numbers.

## Direct national row, 2025

For `År=2025`, `Region=Riket`, `Kön=Båda könen`, and age `0­85+`, the source row reports:

| Source column | Reported value |
|---|---:|
| `Antal patienter` | 260677 |
| `Patienter/1000 invånare` | 24,62 |
| `Antal expedieringar` | 1306902 |
| `Expedieringar/1000 invånare` | 123,44 |
| `Befolkning` | 10587710 |

All values in the app are read from the CSV; none are hard-coded into charts or metric cards. Tests also independently compare the actual source rows for the 2024 national rate, 2025 Jämtlands rate and 2023 Stockholm rate with prepared chart data.

## Integrity rules implemented

1. Source column names are unchanged; added `Ålder (visning)`, `Värde`, `Mått`, and `Enhet` fields are documented.
2. One category combination maps to **one** source observation; duplicate key levels block unsafe charts, and validation never deletes duplicate records silently.
3. National rates come from `Riket`, **not** from an average across region rates.
4. The regional ranking excludes `Riket` as a bar; only its distinct published value is a reference line.
5. Age and sex detail panels exclude the respective total group when constituent groups are shown.
6. No patient count is added across years, drugs or overlapping groups; each row is a reported count for that exact category.
7. Missing numeric fields remain `NA` and are reported, not changed to zero; unknown numeric tokens cause explicit errors.
8. When an input selection has no observations, the UI displays a useful empty state.
9. Exported CSV rows reproduce their panel's source observations, with the currently selected metric and unit.

## Scope and limitations

This is a descriptive explorer, not causal research or a clinical application. Socialstyrelsen states that patient counts represent those who collected a medication at least once in a period, not continuous usage. The register cannot establish why medicines were prescribed. Dose-dispensing arrangements can influence dispensing counts; the register does not cover all medication provision and some personal identifiers can be missing. Compare differing population sizes with source per-1,000 values and do not combine overlapped aggregates. See `SOURCE_README.md` for the complete original Swedish caveats.
