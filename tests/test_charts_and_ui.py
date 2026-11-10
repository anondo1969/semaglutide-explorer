"""Plotly and app wiring tests. Runs without an installed Streamlit server.

A lightweight fake Streamlit surface executes the real app.py selection logic.
This is NOT a substitute for browser/UI testing with installed Streamlit.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
import runpy
import sys
from types import ModuleType

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "app"))
from charts import make_demographic_chart, make_regional_chart, make_trend_chart  # noqa: E402
from data_processing import (  # noqa: E402
    MEASURES, SOURCE_COLUMNS, detect_all_ages, detect_both_sexes, load_source,
    normalize_age_label, prepare_demographics, prepare_regional, prepare_trend, validate_source,
)


class FakeStreamlit(ModuleType):
    def __init__(self, overrides=None):
        super().__init__("streamlit")
        self.overrides = overrides or {}
        self.figures = []
        self.downloads = {}
        self.metrics = []
        self.infos = []
        self.errors = []
        self.warnings = []
        self.captions = []
        self.sidebar = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def cache_data(self, **kwargs):
        return lambda fn: fn

    def selectbox(self, label, options, index=0, **kwargs):
        result = self.overrides.get(label, options[index])
        assert result in options, (label, result, options)
        return result

    def multiselect(self, label, options, default=(), **kwargs):
        result = self.overrides.get(label, default)
        assert set(result) <= set(options)
        return result

    def slider(self, label, value, **kwargs):
        return self.overrides.get(label, value)

    def select_slider(self, label, options, value, **kwargs):
        selection = self.overrides.get(label, value)
        assert all(year in options for year in selection)
        return selection

    def radio(self, label, options, **kwargs):
        return self.overrides.get(label, options[0])

    def columns(self, count):
        return [self] * count

    def expander(self, *args, **kwargs):
        return self

    def metric(self, label, value, **kwargs):
        self.metrics.append((label, value))

    def plotly_chart(self, figure, **kwargs):
        self.figures.append(figure)
        figure.to_json()  # catch invalid Plotly serialization

    def download_button(self, label, data, file_name, mime, **kwargs):
        self.downloads[file_name] = data

    def info(self, text, **kwargs):
        self.infos.append(text)

    def error(self, text, **kwargs):
        self.errors.append(text)

    def warning(self, text, **kwargs):
        self.warnings.append(text)

    def caption(self, text, **kwargs):
        self.captions.append(text)

    # Most visual text API is an inert sink. Controls above are real test inputs.
    def __getattr__(self, name):
        if name in {"set_page_config", "title", "markdown", "caption", "header", "subheader",
                    "divider", "dataframe", "warning", "write"}:
            return lambda *args, **kwargs: None
        raise AttributeError(name)


def run_app(monkeypatch, overrides=None) -> FakeStreamlit:
    fake = FakeStreamlit(overrides)
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    runpy.run_path(str(PROJECT / "app" / "app.py"), run_name="__main__")
    return fake


def decode_csv(csv_bytes):
    return list(csv.DictReader(StringIO(csv_bytes.decode("utf-8-sig")), delimiter=";"))


def test_default_app_views_and_export(monkeypatch):
    fake = run_app(monkeypatch)
    assert not fake.errors
    assert len(fake.figures) == 3
    assert len(fake.downloads) == 3
    assert any("24.62" in str(metric[1]) for metric in fake.metrics)
    trend = decode_csv(fake.downloads["semaglutide_trend_patients_rate.csv"])
    regions = decode_csv(fake.downloads["semaglutide_regions_patients_rate.csv"])
    demographics = decode_csv(fake.downloads["semaglutide_demographic_patients_rate.csv"])
    assert len(trend) == 10
    assert len(regions) == 22  # 21 region bars plus a distinct published reference row
    assert len(demographics) == 18
    assert trend[-1]["Värde"] == "24,62"
    assert set(SOURCE_COLUMNS).issubset(trend[0])
    assert trend[-1]["Antal patienter"] == "260677"
    assert trend[-1]["Antal expedieringar"] == "1306902"
    assert next(row for row in regions if row["Region"] == "Riket")["Värde"] == "24,62"
    assert "Riket" not in fake.figures[1].data[0]["y"]
    assert len(fake.figures[1].layout.shapes) == 1


def test_measure_changed_updates_ui_exports_and_charts(monkeypatch):
    fake = run_app(monkeypatch, {"Measurement": "patients_count", "Comparison year": 2025})
    assert any("260,677" in str(metric[1]) for metric in fake.metrics)
    trend = decode_csv(fake.downloads["semaglutide_trend_patients_count.csv"])
    assert trend[-1]["Värde"] == "260677"
    assert trend[-1]["Enhet"] == "patients"
    assert "Number of patients" in str(fake.figures[0].layout.yaxis.title.text)
    assert "Number of patients" in str(fake.figures[1].layout.xaxis.title.text)
    assert any("absolute counts" in text for text in fake.infos)


def test_multiregion_and_sex_filter_changes_every_relevant_view(monkeypatch):
    fake = run_app(monkeypatch, {
        "Year range": (2023, 2025),
        "Regions for trend": ["Riket", "Stockholms län"],
        "Sex for trend and regional comparison": "Kvinnor",
        "Compare by": "Sex",
        "Region for age/sex comparison": "Stockholms län",
        "Measurement": "dispensings_rate",
    })
    assert not fake.errors and len(fake.figures) == 3
    trend = decode_csv(fake.downloads["semaglutide_trend_dispensings_rate.csv"])
    regional = decode_csv(fake.downloads["semaglutide_regions_dispensings_rate.csv"])
    sexes = decode_csv(fake.downloads["semaglutide_demographic_dispensings_rate.csv"])
    assert len(trend) == 6
    assert {row["Region"] for row in trend} == {"Riket", "Stockholms län"}
    assert {row["Kön"] for row in trend} == {"Kvinnor"}
    assert {row["År"] for row in trend} == {"2023", "2024", "2025"}
    assert all(row["Kön"] == "Kvinnor" for row in regional)
    assert {row["Kön"] for row in sexes} == {"Kvinnor", "Män"}
    assert {row["Region"] for row in sexes} == {"Stockholms län"}
    assert all(row["Enhet"] == "dispensings / 1,000 inhabitants" for row in trend)
    assert fake.figures[2].data[0]["x"].shape[0] == 2


def test_empty_trend_selection_has_message_not_failure(monkeypatch):
    fake = run_app(monkeypatch, {"Regions for trend": []})
    assert not fake.errors
    assert len(fake.figures) == 2  # regional and age view remain available
    assert any("No observations" in text for text in fake.infos)
    assert decode_csv(fake.downloads["semaglutide_trend_patients_rate.csv"]) == []


def test_rounded_zero_explained_and_count_visible(monkeypatch):
    data = load_source()
    younger = next(age for age in data["Ålder"].unique() if normalize_age_label(age) == "5\u20139")
    fake = run_app(monkeypatch, {
        "Year range": (2024, 2024),
        "Comparison year": 2024,
        "Age group for trend and regional comparison": younger,
    })
    assert not fake.errors
    assert any("0.00 per 1,000 despite a positive" in text for text in fake.captions)
    trend = decode_csv(fake.downloads["semaglutide_trend_patients_rate.csv"])
    assert len(trend) == 1
    assert trend[0]["Värde"] == "0,00"
    assert trend[0]["Patienter/1000 invånare"] == "0,00"
    assert trend[0]["Antal patienter"] == "2"


def test_age_chart_is_horizontal_and_national_is_not_a_region_bar(monkeypatch):
    fake = run_app(monkeypatch)
    age_chart = fake.figures[2]
    assert age_chart.data[0].orientation == "h"
    assert age_chart.data[0].y[0] == "0\u20134"
    assert age_chart.data[0].y[-1] == "85+"
    assert "per 1,000" in age_chart.layout.xaxis.title.text


def test_missing_regional_rate_not_drawn_as_a_ranked_bar():
    import pandas as pd
    from data_processing import exported_csv

    source = load_source()
    report = validate_source(source)
    age = detect_all_ages(report.ages)
    sex = detect_both_sexes(report.sexes)
    mask = (
        (source["År"] == 2025) & (source["Region"] == "Stockholms län")
        & (source["Kön"] == sex) & (source["Ålder"] == age)
    )
    assert mask.sum() == 1
    source.loc[mask, "Patienter/1000 invånare"] = pd.NA
    regional, reference = prepare_regional(
        source, year=2025, sex=sex, age=age, drug=report.drugs[0],
        measure_key="patients_rate",
    )
    assert len(regional) == 21 and reference == 24.62
    figure = make_regional_chart(regional, "patients_rate", reference)
    assert len(figure.data[0].y) == 20
    exported = decode_csv(exported_csv(regional, "patients_rate"))
    missing = next(row for row in exported if row["Region"] == "Stockholms län")
    assert missing["Värde"] == "" and missing["Patienter/1000 invånare"] == ""
    assert int(missing["Antal patienter"]) > 0


def test_unknown_overlap_disables_only_demographic_view(monkeypatch):
    import data_processing

    original = load_source()
    added = original.iloc[[0]].copy()
    added["Ålder"] = "5\u201319"
    added["Ålder (visning)"] = "5\u201319"
    changed = __import__("pandas").concat([original, added], ignore_index=True)
    monkeypatch.setattr(data_processing, "load_source", lambda *args, **kwargs: changed)
    fake = run_app(monkeypatch)
    assert not fake.errors
    assert len(fake.figures) == 2  # trend and regions still valid
    assert len(fake.downloads) == 2
    assert any("Demographic comparison unavailable" in text for text in fake.warnings)


@pytest.mark.parametrize("measure", list(MEASURES))
def test_figures_change_with_measure_and_preserve_source_values(measure):
    data = load_source()
    report = validate_source(data)
    age = detect_all_ages(report.ages)
    sex = detect_both_sexes(report.sexes)
    common = dict(frame=data, measure_key=measure, drug=report.drugs[0])
    trend = prepare_trend(**common, year_range=(2024, 2025), regions=["Riket"], sex=sex, age=age)
    regions, reference = prepare_regional(**common, year=2025, sex=sex, age=age)
    age_rows = prepare_demographics(**common, year=2025, region="Riket", sex=sex, age=age, dimension="age")
    plot1 = make_trend_chart(trend, measure)
    plot2 = make_regional_chart(regions, measure, reference)
    plot3 = make_demographic_chart(age_rows, measure, "age")
    assert "Number" in str(plot1.layout.yaxis.title.text) if MEASURES[measure].decimals == 0 else "per 1,000" in str(plot1.layout.yaxis.title.text)
    assert plot1.data[0]["y"][-1] == trend.iloc[-1]["Värde"]
    assert len(plot2.data[0]["y"]) == 21
    assert len(plot3.data[0]["y"]) == 18
    assert plot3.data[0].orientation == "h"
    assert len(plot2.layout.shapes) == 1
    assert float(plot2.layout.shapes[0].x0) == reference
