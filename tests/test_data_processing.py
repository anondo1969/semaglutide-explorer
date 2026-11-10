"""Scientific integrity checks, independent of the Streamlit interface."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "app"))
from data_processing import (  # noqa: E402
    DATA_FILE, MEASURES, DataValidationError, detect_all_ages, detect_both_sexes,
    exported_csv, filter_observations, formatted_value, load_source,
    normalize_age_label, ordered_ages, paired_measure_columns,
    prepare_demographics, prepare_regional, prepare_trend,
    rounded_zero_rate_rows, select_measure, validate_source,
    verify_disjoint_age_groups, verify_disjoint_sex_groups,
)


@pytest.fixture(scope="module")
def data():
    return load_source()


@pytest.fixture(scope="module")
def categories(data):
    report = validate_source(data)
    return report, detect_all_ages(report.ages), detect_both_sexes(report.sexes)


def csv_observation(*, year: int, region: str, sex: str, age: str) -> dict[str, str]:
    """Check reference values *against raw lines*, not the processing module."""
    with DATA_FILE.open(encoding="utf-8-sig", newline="") as input_file:
        next(input_file)  # Known source title line.
        matches = [row for row in csv.DictReader(input_file, delimiter=";") if
                   row["År"] == str(year) and row["Region"] == region and
                   row["Kön"] == sex and row["Ålder"] == age]
    assert len(matches) == 1
    return matches[0]


def test_full_coverage_and_no_problem_rows(data, categories):
    report, all_ages, both_sexes = categories
    assert len(data) == report.observations == 12540
    assert report.years == tuple(range(2016, 2026))
    assert len(report.regions) == 22 and "Riket" in report.regions
    assert report.sexes == ("Män", "Kvinnor", "Båda könen")
    assert len(report.ages) == 19
    assert len(report.drugs) == 1
    assert not report.errors and not report.warnings
    assert normalize_age_label(all_ages) == "0–85+"
    assert both_sexes == "Båda könen"


def test_2025_national_published_reference(data, categories):
    report, age, both = categories
    selection = filter_observations(
        data, years=[2025], regions=["Riket"], sex=both, age=age, drug=report.drugs[0]
    )
    assert len(selection) == 1
    observed = selection.iloc[0]
    raw = csv_observation(year=2025, region="Riket", sex=both, age=age)
    assert raw["Antal patienter"] == "260677"
    assert raw["Patienter/1000 invånare"] == "24,62"
    assert int(observed["Antal patienter"]) == 260677
    assert float(observed["Patienter/1000 invånare"]) == 24.62
    assert int(observed["Antal expedieringar"]) == 1306902
    assert float(observed["Expedieringar/1000 invånare"]) == 123.44


def test_other_plot_values_against_original_csv(data, categories):
    report, age, both = categories
    for year, region in [(2024, "Riket"), (2025, "Jämtlands län"), (2023, "Stockholms län")]:
        raw = csv_observation(year=year, region=region, sex=both, age=age)
        trend = prepare_trend(
            data, year_range=(year, year), regions=[region], sex=both, age=age,
            drug=report.drugs[0], measure_key="patients_rate"
        )
        assert len(trend) == 1
        assert float(trend.iloc[0]["Värde"]) == float(raw["Patienter/1000 invånare"].replace(",", "."))


def test_regional_ranking_only_regions_and_national_reference(data, categories):
    report, age, both = categories
    regional, national = prepare_regional(
        data, year=2025, sex=both, age=age, drug=report.drugs[0], measure_key="patients_rate"
    )
    assert len(regional) == 21
    assert (regional["Region"] != "Riket").all()
    assert national == 24.62
    # An unweighted mean of regional rates is *not* the national published rate.
    assert round(float(regional["Värde"].mean()), 2) != national


def test_nonoverlapping_age_and_sex_comparisons(data, categories):
    report, age, both = categories
    params = dict(
        frame=data, year=2025, region="Riket", drug=report.drugs[0],
        measure_key="patients_rate", age=age, sex=both
    )
    ages = prepare_demographics(**params, dimension="age")
    sexes = prepare_demographics(**params, dimension="sex")
    assert len(ages) == 18 and age not in ages["Ålder"].tolist()
    assert len(sexes) == 2 and both not in sexes["Kön"].tolist()
    assert all(normalize_age_label(v) == v for v in ages["Jämförelsegrupp"])
    assert set(sexes["Kön"]) == {"Män", "Kvinnor"}
    assert ages["Jämförelsegrupp"].iloc[0] == "0–4"


@pytest.mark.parametrize("key,column", [(key, metric.source_column) for key, metric in MEASURES.items()])
def test_selected_measure_changes_values_and_csv(data, categories, key, column):
    report, age, both = categories
    trend = prepare_trend(
        data, year_range=(2025, 2025), regions=["Riket"], sex=both, age=age,
        drug=report.drugs[0], measure_key=key
    )
    assert len(trend) == 1
    assert trend.iloc[0]["Värde"] == trend.iloc[0][column]
    assert trend.iloc[0]["Enhet"] == MEASURES[key].unit
    out = exported_csv(trend, key).decode("utf-8-sig")
    parsed = list(csv.DictReader(StringIO(out), delimiter=";"))
    assert len(parsed) == 1
    assert parsed[0]["Mått"] == MEASURES[key].label
    assert parsed[0]["Enhet"] == MEASURES[key].unit
    assert float(parsed[0]["Värde"].replace(",", ".")) == float(trend.iloc[0][column])
    assert column in parsed[0]
    assert set(parsed[0]).issubset(set(trend.columns))


def test_selection_cannot_sum_multiple_sex_aggregates(data, categories):
    report, age, _ = categories
    mixed = filter_observations(
        data, years=[2025], regions=["Riket"], age=age, drug=report.drugs[0]
    )
    assert len(mixed) == 3
    with pytest.raises(DataValidationError):
        prepare_trend(
            mixed, year_range=(2025, 2025), regions=["Riket"],
            sex=None, age=age, drug=report.drugs[0], measure_key="patients_count"
        )


def test_empty_selection_no_crash(data, categories):
    report, age, both = categories
    result = prepare_trend(
        data, year_range=(2025, 2025), regions=["Fictional region"],
        sex=both, age=age, drug=report.drugs[0], measure_key="patients_rate"
    )
    assert result.empty
    assert len(exported_csv(result, "patients_rate")) > 10  # header survives


def test_missing_measurements_retained_with_warning(data):
    changed = data.copy()
    changed.loc[changed.index[1], "Patienter/1000 invånare"] = pd.NA
    changed.loc[changed.index[1], "Antal patienter"] = pd.NA
    report = validate_source(changed)
    assert report.warnings
    assert "missing measurements" in " ".join(report.warnings)
    assert len(changed) == len(data)


def test_duplicate_key_is_reported_and_plot_rejected(data, categories):
    report, age, both = categories
    chosen = filter_observations(
        data, years=[2025], regions=["Riket"], sex=both, age=age, drug=report.drugs[0]
    )
    doubled = pd.concat([data, chosen], ignore_index=True)
    assert any("Duplicate" in e for e in validate_source(doubled).errors)
    with pytest.raises(DataValidationError, match="multiple source observations"):
        prepare_trend(
            doubled, year_range=(2025, 2025), regions=["Riket"],
            sex=both, age=age, drug=report.drugs[0], measure_key="patients_rate"
        )


def test_added_drug_is_reported_and_not_mixed(data):
    other = data.iloc[[0]].copy()
    other["Läkemedel"] = "OTHER DRUG"
    changed = pd.concat([data, other], ignore_index=True)
    report = validate_source(changed)
    assert any("drugs" in message for message in report.warnings)
    assert len(filter_observations(changed, drug="OTHER DRUG")) == 1


def test_loader_with_nonstandard_encoding_and_missing_value(tmp_path):
    cols = "År;Läkemedel;Region;Kön;Ålder;Antal patienter;Patienter/1000 invånare;Antal expedieringar;Expedieringar/1000 invånare;Befolkning"
    record = "2025;A10BJ06 Semaglutid;Riket;Båda könen;0‐85+;;24,62;20;1,25;1 000"
    file = tmp_path / "new.csv"
    file.write_bytes(("Läkemedelsstatistik\n" + cols + "\n" + record + "\n").encode("cp1252", errors="replace"))
    frame = load_source(file)
    assert len(frame) == 1
    assert pd.isna(frame.iloc[0]["Antal patienter"])
    assert frame.iloc[0]["Befolkning"] == 1000
    assert float(frame.iloc[0]["Patienter/1000 invånare"]) == 24.62
    assert normalize_age_label("0\u201085+") == "0–85+"


def test_unknown_numeric_source_raises(tmp_path):
    cols = "År;Läkemedel;Region;Kön;Ålder;Antal patienter;Patienter/1000 invånare;Antal expedieringar;Expedieringar/1000 invånare;Befolkning"
    row = "2025;X;Riket;Båda könen;0-85+;twelve;1,00;1;1,00;1000"
    file = tmp_path / "bad.csv"
    file.write_text(cols + "\n" + row, encoding="utf-8")
    with pytest.raises(DataValidationError, match="Unrecognized numeric"):
        load_source(file)


def test_ordered_ages_and_readable_formatting(categories):
    report, age, _ = categories
    ordered = ordered_ages(report.ages)
    assert ordered[-1] == age
    assert ordered[0] == report.ages[0]
    assert formatted_value(260677, "patients_count") == "260,677"
    assert formatted_value(24.62, "patients_rate") == "24.62"
    assert formatted_value(pd.NA, "patients_rate") == "Not reported"


def test_unknown_metric_rejected(data):
    with pytest.raises(ValueError, match="Unknown measurement"):
        select_measure(data, "not_a_metric")


def test_published_zero_rates_can_mean_positive_counts(data):
    assert paired_measure_columns("patients_rate") == (
        "Antal patienter", "Patienter/1000 invånare"
    )
    assert rounded_zero_rate_rows(data, "patients_rate") == 12
    assert rounded_zero_rate_rows(data, "dispensings_rate") == 3
    assert rounded_zero_rate_rows(data, "patients_count") == 0
    sample = data.loc[
        (data["År"] == 2024) & (data["Region"] == "Riket")
        & (data["Kön"] == "Båda könen")
        & (data["Ålder (visning)"] == "5\u20139")
    ]
    assert len(sample) == 1
    assert int(sample.iloc[0]["Antal patienter"]) == 2
    assert float(sample.iloc[0]["Patienter/1000 invånare"]) == 0


def test_export_keeps_original_two_decimal_precision(data, categories):
    report, age, both = categories
    selected = filter_observations(
        data, years=[2022], regions=["Riket"], sex=both, age=age,
        drug=report.drugs[0],
    )
    rows = list(csv.DictReader(
        StringIO(exported_csv(selected, "patients_rate").decode("utf-8-sig")), delimiter=";"
    ))
    assert len(rows) == 1
    assert rows[0]["Patienter/1000 invånare"] == "8,00"
    assert rows[0]["Värde"] == "8,00"


def test_overlapping_age_group_is_reported_and_not_plotted(data, categories):
    report, all_ages, both = categories
    new = data.iloc[[0]].copy()
    new["Ålder"] = "5\u201319"
    new["Ålder (visning)"] = "5\u201319"
    changed = pd.concat([data, new], ignore_index=True)
    observed = validate_source(changed)
    assert any("Age breakdown unsafe: Overlapping" in warning for warning in observed.warnings)
    with pytest.raises(DataValidationError, match="Overlapping age groups"):
        prepare_demographics(
            changed, year=2025, region="Riket", drug=report.drugs[0],
            measure_key="patients_rate", dimension="age", sex=both, age=all_ages,
        )
    # A pre-existing, precisely selected age group remains safe to view.
    trend = prepare_trend(
        changed, year_range=(2025, 2025), regions=["Riket"],
        sex=both, age=all_ages, drug=report.drugs[0], measure_key="patients_rate",
    )
    assert len(trend) == 1
    verify_disjoint_age_groups(report.ages)


def test_unknown_sex_breakdown_is_blocked(data, categories):
    report, all_ages, both = categories
    extra = data.iloc[[0]].copy()
    extra["Kön"] = "Unknown"
    changed = pd.concat([data, extra], ignore_index=True)
    assert any("Sex breakdown unsafe" in w for w in validate_source(changed).warnings)
    with pytest.raises(DataValidationError, match="Cannot verify disjoint sex-specific"):
        prepare_demographics(
            changed, year=2025, region="Riket", drug=report.drugs[0],
            measure_key="patients_rate", dimension="sex", sex=both, age=all_ages,
        )
    verify_disjoint_sex_groups(report.sexes)


def test_rate_consistency_audit_preserves_published_numbers(data):
    changed = data.copy()
    original = float(changed.loc[0, "Patienter/1000 invånare"])
    changed.loc[0, "Patienter/1000 invånare"] = original + 0.1
    report = validate_source(changed)
    assert any("disagree with count/population" in warning for warning in report.warnings)
    assert float(changed.loc[0, "Patienter/1000 invånare"]) == pytest.approx(original + 0.1)
    # Rates remain source observations: validation does not rewrite them.


def test_invalid_age_interval_is_not_misrepresented(data):
    labels = list(data["Ålder"].unique())
    labels.append("Unknown")
    with pytest.raises(DataValidationError, match="Cannot verify"):
        verify_disjoint_age_groups(labels)
    labels[-1] = "20\u201310"
    with pytest.raises(DataValidationError, match="Invalid age interval"):
        verify_disjoint_age_groups(labels)
