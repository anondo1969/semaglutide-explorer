"""Semaglutide Use in Sweden: Interactive Explorer (aggregate data only)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from charts import make_demographic_chart, make_regional_chart, make_trend_chart
from data_processing import (
    DATA_FILE, MEASURES, DataValidationError, detect_all_ages,
    detect_both_sexes, exported_csv, filter_observations, formatted_value,
    load_source, normalize_age_label, ordered_ages, paired_measure_columns,
    prepare_demographics, prepare_regional, prepare_trend,
    rounded_zero_rate_rows, validate_source,
)

st.set_page_config(
    page_title="Semaglutide Use in Sweden | Interactive Explorer",
    page_icon="💊", layout="wide", initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def get_data():
    frame = load_source(DATA_FILE)
    report = validate_source(frame)
    return frame, report


def data_section(rows: pd.DataFrame, measure_key: str, file_stem: str, *, expanded: bool = False):
    """Show exactly the source observations used by this view, with a matching export."""
    count_column, rate_column = paired_measure_columns(measure_key)
    with st.expander(f"Source observations & download ({len(rows):,} rows)", expanded=expanded):
        show_cols = [
            "År", "Region", "Kön", "Ålder (visning)", "Läkemedel",
            count_column, rate_column, "Befolkning",
        ]
        visible = rows[[c for c in show_cols if c in rows.columns]].copy()
        visible = visible.rename(columns={"Ålder (visning)": "Age group (display)"})
        st.dataframe(visible, hide_index=True, use_container_width=True)
        st.caption(
            "The download contains all ten original Swedish CSV columns plus the readable age label, "
            "the selected measurement ('Värde') and unit ('Enhet'). "
            "The count and published rate are both displayed above so rounding can be checked. "
            "Rows are never summed or averaged."
        )
        st.download_button(
            "Download these observations (.csv)", data=exported_csv(rows, measure_key),
            file_name=f"semaglutide_{file_stem}_{measure_key}.csv",
            mime="text/csv", key=f"download_{file_stem}",
        )


def measurement_notes(rows: pd.DataFrame, measure_key: str) -> None:
    """Clarify rounded zeroes and unavailable values without changing source data."""
    missing = int(rows["Värde"].isna().sum())
    if missing:
        st.caption(
            f"Not reported: {missing} source observations have no value for this measure. "
            "They remain in the table/download but do not appear as plotted values."
        )
    n_rounded = rounded_zero_rate_rows(rows, measure_key)
    if n_rounded:
        st.caption(
            f"Rounding: {n_rounded} observations show 0.00 per 1,000 despite a positive "
            "reported count. A plotted zero rate need not mean zero patients or dispensings; "
            "see both published fields in the table."
        )


try:
    frame, report = get_data()
except (FileNotFoundError, UnicodeError, ValueError) as error:
    st.error(f"Could not load the supplied data: {error}")
    st.stop()

if report.errors:
    st.error("Data integrity checks found errors. The plots have been disabled to prevent misleading comparisons.")
    for issue in report.errors:
        st.error(issue)
    st.stop()

all_ages = detect_all_ages(report.ages)
both_sexes = detect_both_sexes(report.sexes)
year_min, year_max = min(report.years), max(report.years)

st.title("Semaglutide Use in Sweden: Interactive Explorer")
st.markdown(
    "Explore **published aggregate pharmacy-dispensing statistics** from Sweden's "
    "National Board of Health and Welfare (Socialstyrelsen). "
    "Select years, geographic areas, sex, age group and measurement to inspect observed values. "
    "**Descriptive only — not clinical advice or a causal analysis.**"
)
st.caption(
    f"Source: Socialstyrelsen • {year_min}–{year_max} • {report.observations:,} published observations "
    f"• {len(report.regions) - int('Riket' in report.regions)} regions + national summary"
)

with st.sidebar:
    st.header("Explore the data")
    if len(report.years) > 1:
        year_range = st.select_slider("Year range", options=list(report.years), value=(year_min, year_max))
    else:
        year_range = (year_min, year_min)
        st.caption(f"Year: {year_min}")
    regions = st.multiselect(
        "Regions for trend", options=list(report.regions),
        default=["Riket"] if "Riket" in report.regions else [report.regions[0]],
        help="Riket is the published national aggregate, not the average of the regions.",
    )
    sex = st.selectbox("Sex for trend and regional comparison", options=list(report.sexes),
                       index=list(report.sexes).index(both_sexes))
    ages = ordered_ages(report.ages)
    age = st.selectbox(
        "Age group for trend and regional comparison", options=ages,
        index=ages.index(all_ages), format_func=normalize_age_label,
    )
    measure_key = st.selectbox("Measurement", options=list(MEASURES),
                               format_func=lambda key: MEASURES[key].label)
    drug = (st.selectbox("Drug", options=list(report.drugs)) if len(report.drugs) > 1 else report.drugs[0])

    st.divider()
    focus_years = [yr for yr in report.years if year_range[0] <= yr <= year_range[1]]
    focus_year = st.selectbox("Comparison year", options=focus_years, index=len(focus_years) - 1,
                              help="Used by the regional and age/sex comparisons.")
    detail_region = st.selectbox(
        "Region for age/sex comparison", options=list(report.regions),
        index=list(report.regions).index(regions[0]) if regions else 0,
        help="Shows exactly one source region at a time. It may differ from the trend regions.",
    )
    st.caption("Regional ranking shows all individual regions, independent of the trend region selector.")
    if report.warnings:
        st.warning("Data audit notes:\n\n" + "\n\n".join(report.warnings))

metric = MEASURES[measure_key]
if measure_key.endswith("_count"):
    st.info(
        "You selected absolute counts. Population sizes vary across years, regions, "
        "sexes and age groups. For comparisons of differently sized populations, "
        "use the corresponding published per-1,000 rate."
    )
try:
    trend_rows = prepare_trend(
        frame, year_range=year_range, regions=regions, sex=sex, age=age,
        drug=drug, measure_key=measure_key,
    )
    regional_rows, national_reference = prepare_regional(
        frame, year=focus_year, sex=sex, age=age, drug=drug, measure_key=measure_key,
    )
except DataValidationError as error:
    st.error(f"The current selection cannot be plotted safely: {error}")
    st.stop()

# Every value card corresponds either to a single source row or to the number
# of distinct selected rows/categories. We never sum patient/dispensing counts.
st.subheader("At a glance · current trend selection")
if trend_rows.empty:
    st.info("No observations match the trend filters. Select at least one region or broaden the filters.")
elif len(regions) == 1:
    latest_year = int(trend_rows["År"].max())
    earliest_year = int(trend_rows["År"].min())
    newest = trend_rows.loc[trend_rows["År"].eq(latest_year), "Värde"].iloc[0]
    oldest = trend_rows.loc[trend_rows["År"].eq(earliest_year), "Värde"].iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric(f"{latest_year} · {metric.label}", formatted_value(newest, measure_key))
    col2.metric(f"{earliest_year} · {metric.label}", formatted_value(oldest, measure_key))
    col3.metric("Source observations", f"{len(trend_rows):,}")
    st.caption(f"Region: {regions[0]} · Sex: {sex} · Age group: {normalize_age_label(age)} · Unit: {metric.unit}")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Regions selected", str(trend_rows["Region"].nunique()))
    col2.metric("Years represented", str(trend_rows["År"].nunique()))
    col3.metric("Source observations", f"{len(trend_rows):,}")
    st.caption("Counts above describe source rows, regions and years, never a sum of patient counts.")

st.subheader("01 · Time trends")
st.caption(
    f"A published observation per region and year; {sex}, age {normalize_age_label(age)}. "
    f"Y-axis: {metric.label}. All selected regions remain separate."
)
if trend_rows.empty or trend_rows["Värde"].isna().all():
    st.info("No reported values are available for the trend chart with the selected filters.")
else:
    st.plotly_chart(make_trend_chart(trend_rows, measure_key), use_container_width=True)
measurement_notes(trend_rows, measure_key)
data_section(trend_rows, measure_key, "trend", expanded=True)

st.divider()
st.subheader("02 · Compare Sweden's regions")
st.caption(
    f"Individual regions in {focus_year}; {sex}, age {normalize_age_label(age)}. "
    "Riket is excluded from the region ranking. When present, a dashed line marks "
    "its **published national observation**, not an average of regions. "
    "This chart intentionally uses all individual regions regardless of trend-region selection."
)
if regional_rows.empty or regional_rows["Värde"].isna().all():
    st.info("No reported regional values are available for this comparison.")
else:
    st.plotly_chart(make_regional_chart(regional_rows, measure_key, national_reference), use_container_width=True)
measurement_notes(regional_rows, measure_key)

# Export the national reference row *as an observation*, separately from the
# individual-region rows in the chart; it is never part of the ranking.
reference_rows = filter_observations(
    frame, years=[focus_year], regions=["Riket"], sex=sex, age=age, drug=drug,
)
regional_export = pd.concat([regional_rows, reference_rows], ignore_index=True)
st.caption("The regional download also includes the separately shown Riket reference observation, if available.")
data_section(regional_export, measure_key, "regions")

st.divider()
st.subheader("03 · Age and sex detail")
dimension = st.radio("Compare by", options=["Age groups", "Sex"], horizontal=True)
breakdown_kind = "age" if dimension == "Age groups" else "sex"
try:
    demographic_rows = prepare_demographics(
        frame, year=focus_year, region=detail_region, drug=drug,
        measure_key=measure_key, dimension=breakdown_kind, sex=sex, age=age,
    )
except DataValidationError as error:
    # An unfamiliar/overlapping category should disable only the unsafe view.
    # Other single-category plots and the provenance section remain available.
    st.warning(f"Demographic comparison unavailable: {error}")
else:
    if breakdown_kind == "age":
        st.caption(
            f"{focus_year}, {detail_region}, {sex}: non-overlapping source age groups only. "
            f"The aggregate age category ({normalize_age_label(all_ages)}) is excluded."
        )
    else:
        st.caption(
            f"{focus_year}, {detail_region}, age {normalize_age_label(age)}: sex-specific values only. "
            f"The aggregate ({both_sexes}) is excluded."
        )
    if demographic_rows.empty or demographic_rows["Värde"].isna().all():
        st.info("No reported demographic observations are available for this selection.")
    else:
        st.plotly_chart(make_demographic_chart(demographic_rows, measure_key, breakdown_kind), use_container_width=True)
    measurement_notes(demographic_rows, measure_key)
    data_section(demographic_rows, measure_key, "demographic")

st.divider()
st.subheader("Definitions, provenance & limitations")
with st.expander("What do these values mean?", expanded=True):
    st.markdown(
        "- **Patients** = distinct people who filled the medication at least once during "
        "the reporting year; this is not a count of people continuously treated.\n"
        "- **Dispensings** = pharmacy dispensing events, not distinct people. "
        "Dose-dispensed prescriptions can produce more dispensings than standard prescriptions.\n"
        "- **Per 1,000 inhabitants** = the rate published by Socialstyrelsen. "
        "Use rates rather than raw counts for populations of different sizes. "
        "These published rates are **not** averages calculated across regions. "
        "Rates are rounded to two decimals: 0.00 can coincide with a positive count.\n"
        "- **Riket**, **Båda könen** and the all-ages record are source aggregates. "
        "Do not add them to their constituent regions, sexes or age groups.\n"
        "- The source is **dispensed prescriptions**, not all medication use: "
        "over-the-counter and healthcare-administered medicines are outside the register; "
        "some records can lack personal identifiers.\n"
        "- The register does **not** document why semaglutide was prescribed. "
        "Do not infer diagnoses, indications, treatment outcomes, or causes of changes. "
        "Patient counts must not be summed across reporting years or overlapping groups."
    )
    st.caption(
        "Scope: the supplied extract is for A10BJ06 Semaglutid. This explorer "
        "must not be interpreted as a census of all semaglutide administration, "
        "individual treatment, or prescribing indications."
    )
    st.markdown(
        "**Primary data:** [Socialstyrelsen statistics portal](https://sdb.socialstyrelsen.se/if_lak/val.aspx)  "
        "\n**Workshop source, dataset and original limitations:** "
        "[SciLifeLab workshop materials](https://github.com/ScilifelabDataCentre/ddls-2026-workshop-materials/tree/main/semaglutid)  "
        "\n**App methodology:** simple reading, filtering and charting of the supplied "
        "CSV, with no predictive or inferential calculations."
    )

st.caption("Researcher review is required before using these descriptive observations in a scientific conclusion.")
