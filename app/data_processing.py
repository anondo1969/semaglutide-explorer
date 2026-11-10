"""Framework-independent handling of published Socialstyrelsen aggregate observations.

IMPORTANT: each CSV row is already an aggregate observation. No counts are
summed, and no regional rates are averaged, anywhere in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

import pandas as pd

DATA_FILE = Path(__file__).resolve().parent / "data" / "socialstyrelsen_semaglutid_2016_2025.csv"

KEY_COLUMNS = ("År", "Läkemedel", "Region", "Kön", "Ålder")
COUNT_COLUMNS = ("Antal patienter", "Antal expedieringar", "Befolkning")
RATE_COLUMNS = ("Patienter/1000 invånare", "Expedieringar/1000 invånare")
SOURCE_COLUMNS = KEY_COLUMNS + (
    "Antal patienter",
    "Patienter/1000 invånare",
    "Antal expedieringar",
    "Expedieringar/1000 invånare",
    "Befolkning",
)


@dataclass(frozen=True)
class Measure:
    source_column: str
    label: str
    unit: str
    decimals: int


MEASURES: dict[str, Measure] = {
    "patients_rate": Measure(
        "Patienter/1000 invånare", "Patients per 1,000 inhabitants", "patients / 1,000 inhabitants", 2
    ),
    "patients_count": Measure("Antal patienter", "Number of patients", "patients", 0),
    "dispensings_rate": Measure(
        "Expedieringar/1000 invånare", "Dispensings per 1,000 inhabitants", "dispensings / 1,000 inhabitants", 2
    ),
    "dispensings_count": Measure("Antal expedieringar", "Number of dispensings", "dispensings", 0),
}

MISSING_NUMERIC_TOKENS = {"", "-", "–", "—", ".", "..", "...", "na", "n/a", "null", "sekretess"}
HYPHEN_EQUIVALENTS = "\u00ad\u2010\u2011\u2012\u2013\u2014\u2212\u002d\ufe63\uff0d"
TRANSLATE_HYPHENS = str.maketrans({ch: "–" for ch in HYPHEN_EQUIVALENTS})


class DataValidationError(ValueError):
    """Source is malformed or a selection violates one-row-per-category logic."""


@dataclass(frozen=True)
class ValidationReport:
    observations: int
    years: tuple[int, ...]
    regions: tuple[str, ...]
    sexes: tuple[str, ...]
    ages: tuple[str, ...]
    drugs: tuple[str, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def normalize_age_label(label: str) -> str:
    """Only normalize labels for display; never change their source key values."""
    return unicodedata.normalize("NFC", str(label)).translate(TRANSLATE_HYPHENS).strip()


def detect_all_ages(ages: list[str] | tuple[str, ...]) -> str:
    """Identify the aggregate in *actual* age labels; fail if ambiguous."""
    matching = []
    for source in ages:
        text = normalize_age_label(source).casefold()
        if (
            text in {"alla åldrar", "samtliga åldrar", "all ages", "totalt", "total"}
            or re.fullmatch(r"0–\d+\+", text)
        ):
            matching.append(source)
    if len(matching) != 1:
        raise DataValidationError(
            f"Expected exactly one all-ages aggregate, found {len(matching)}: {matching}. "
            "Review source categories before plotting."
        )
    return matching[0]


def detect_both_sexes(sexes: list[str] | tuple[str, ...]) -> str:
    matching = [s for s in sexes if s.casefold().strip() in {"båda könen", "alla kön", "both sexes", "total"}]
    if len(matching) != 1:
        raise DataValidationError(f"Expected one both-sexes aggregate; found {matching}.")
    return matching[0]


def verify_disjoint_age_groups(ages: list[str] | tuple[str, ...]) -> None:
    """Refuse an age breakdown unless source labels prove non-overlapping bins.

    This checks category boundaries, not population coverage. An unfamiliar or
    overlapping age label may still be selected for a single-observation trend,
    but must not be presented as a constituent of a disjoint age breakdown.
    """
    aggregate = detect_all_ages(ages)
    intervals: list[tuple[int, float, str]] = []
    normalized_labels: set[str] = set()
    for label in ages:
        if label == aggregate:
            continue
        text = normalize_age_label(label).replace("\u2013", "-")
        if text in normalized_labels:
            raise DataValidationError(f"Duplicate display age category: {text!r}.")
        normalized_labels.add(text)
        bounded = re.fullmatch(r"(\d+)-(\d+)", text)
        open_ended = re.fullmatch(r"(\d+)\+", text)
        if bounded:
            lower, upper = (int(value) for value in bounded.groups())
            if lower > upper:
                raise DataValidationError(f"Invalid age interval {text!r}.")
        elif open_ended:
            lower, upper = int(open_ended.group(1)), float("inf")
        else:
            raise DataValidationError(
                f"Cannot verify whether age category {text!r} overlaps another group."
            )
        intervals.append((lower, upper, text))
    intervals.sort(key=lambda record: (record[0], record[1]))
    for (_, previous_end, previous_label), (next_start, _, next_label) in zip(intervals, intervals[1:]):
        if next_start <= previous_end:
            raise DataValidationError(
                f"Overlapping age groups: {previous_label!r} and {next_label!r}."
            )


def verify_disjoint_sex_groups(sexes: list[str] | tuple[str, ...]) -> None:
    """The supplied data define exactly two known sex-specific groups."""
    aggregate = detect_both_sexes(sexes)
    members = [sex for sex in sexes if sex != aggregate]
    if len(members) != 2 or set(members) != {"M\u00e4n", "Kvinnor"}:
        raise DataValidationError(
            "Cannot verify disjoint sex-specific categories; review source definitions."
        )


def paired_measure_columns(measure_key: str) -> tuple[str, str]:
    """Return the original count and published rate for the same measure."""
    if measure_key not in MEASURES:
        raise ValueError(f"Unknown measurement {measure_key!r}")
    family = measure_key.split("_", 1)[0]
    return MEASURES[f"{family}_count"].source_column, MEASURES[f"{family}_rate"].source_column


def rounded_zero_rate_rows(rows: pd.DataFrame, measure_key: str) -> int:
    """Count observations whose published 0.00 rate masks a positive count."""
    if measure_key not in MEASURES:
        raise ValueError(f"Unknown measurement {measure_key!r}")
    if not measure_key.endswith("_rate"):
        return 0
    count_column, rate_column = paired_measure_columns(measure_key)
    condition = rows[rate_column].eq(0) & rows[count_column].gt(0)
    return int(condition.fillna(False).sum())


def _parse_numeric(column: pd.Series, *, integer: bool) -> pd.Series:
    raw = column.astype("string").str.strip()
    # Whitespace used as a thousands separator may occur in new exports.
    compact = (
        raw.str.replace("\u00a0", "", regex=False)
        .str.replace("\u202f", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    empty = compact.str.casefold().isin(MISSING_NUMERIC_TOKENS)
    numeric = pd.to_numeric(compact.mask(empty), errors="coerce")
    invalid = numeric.isna() & ~empty
    if invalid.any():
        bad = raw.loc[invalid].drop_duplicates().head(6).tolist()
        raise DataValidationError(f"Unrecognized numeric values in {column.name!r}: {bad}")
    if (numeric.dropna() < 0).any():
        raise DataValidationError(f"Negative counts/rates are not expected in {column.name!r}.")
    if integer:
        nonint = numeric.notna() & numeric.ne(numeric.round())
        if nonint.any():
            raise DataValidationError(f"Non-integer values in count column {column.name!r}.")
        return numeric.astype("Int64")
    return numeric.astype("Float64")


def load_source(path: str | Path = DATA_FILE) -> pd.DataFrame:
    """Load original CSV: optional title line, semicolons, decimal commas, Swedish Unicode.

    Original Swedish column names and row keys are kept unchanged. Missing
    measurements become pandas NA and remain present in the returned frame.
    """
    path = Path(path)
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with path.open("r", encoding=encoding) as source:
                first = source.readline().strip()
            if first.startswith("År;"):
                skiprows = 0
            elif first == "Läkemedelsstatistik":
                skiprows = 1
            else:
                raise DataValidationError(f"Unrecognized CSV title/header line: {first[:120]!r}")
            frame = pd.read_csv(
                path, sep=";", skiprows=skiprows, encoding=encoding,
                dtype="string", keep_default_na=False, on_bad_lines="error",
            )
            break
        except UnicodeDecodeError as error:
            last_error = error
    else:
        raise DataValidationError(f"Unable to decode CSV: {last_error}")

    if frame.columns.duplicated().any():
        raise DataValidationError("Duplicate source column headings.")
    missing_columns = set(SOURCE_COLUMNS) - set(frame.columns)
    if missing_columns:
        raise DataValidationError(f"Missing required CSV columns: {sorted(missing_columns)}")

    year_raw = frame["År"].astype("string").str.strip()
    years = pd.to_numeric(year_raw, errors="coerce")
    if years.isna().any() or years.ne(years.round()).any():
        raise DataValidationError("Year column must consist of whole years with no missing entries.")
    frame["År"] = years.astype("int64")
    for key in ("Läkemedel", "Region", "Kön", "Ålder"):
        frame[key] = frame[key].astype("string").str.strip()
    for col in COUNT_COLUMNS:
        frame[col] = _parse_numeric(frame[col], integer=True)
    for col in RATE_COLUMNS:
        frame[col] = _parse_numeric(frame[col], integer=False)

    frame["Ålder (visning)"] = frame["Ålder"].map(normalize_age_label)
    return frame


def validate_source(frame: pd.DataFrame) -> ValidationReport:
    """Return all discovered categories plus explicit data-quality findings."""
    missing = set(SOURCE_COLUMNS) - set(frame.columns)
    if missing:
        raise DataValidationError(f"Missing required columns: {sorted(missing)}")

    errors: list[str] = []
    warnings: list[str] = []
    years = tuple(sorted(int(v) for v in frame["År"].dropna().unique()))
    regions = tuple(sorted(str(v) for v in frame["Region"].dropna().unique()))
    sexes = tuple(str(v) for v in frame["Kön"].dropna().unique())
    ages = tuple(str(v) for v in frame["Ålder"].dropna().unique())
    drugs = tuple(str(v) for v in frame["Läkemedel"].dropna().unique())

    missing_keys = frame[list(KEY_COLUMNS)].isna().any(axis=1)
    for key in KEY_COLUMNS[1:]:
        missing_keys = missing_keys | frame[key].astype("string").str.strip().eq("").fillna(True)
    if missing_keys.any():
        errors.append(f"Missing/blank key fields in {int(missing_keys.sum())} rows.")
    duplicates = frame.duplicated(list(KEY_COLUMNS), keep=False)
    if duplicates.any():
        errors.append(f"Duplicate year/drug/region/sex/age keys in {int(duplicates.sum())} rows.")
    for col in COUNT_COLUMNS + RATE_COLUMNS:
        n = int(frame[col].isna().sum())
        if n:
            warnings.append(f"{col}: {n} missing measurements (retained as NA).")

    missing_years = sorted(set(range(2016, 2026)) - set(years))
    if missing_years:
        warnings.append(f"Expected 2016–2025 coverage; missing years: {missing_years}.")
    extra_years = sorted(set(years) - set(range(2016, 2026)))
    if extra_years:
        warnings.append(f"Years outside 2016–2025 source scope: {extra_years}.")
    if "Riket" not in regions:
        warnings.append("National summary region 'Riket' is absent.")
    if len(regions) != 22:
        warnings.append(f"Found {len(regions)} region categories (original dataset has 22).")
    unusual_regions = [r for r in regions if r != "Riket" and not r.casefold().endswith(" län")]
    if unusual_regions:
        warnings.append(f"Unusual region labels (inspect against source): {unusual_regions}.")
    if not drugs:
        errors.append("No drug category found.")
    elif len(drugs) != 1:
        warnings.append(f"Found {len(drugs)} drugs: choose a single drug for comparisons.")
    unknown_sexes = set(sexes) - {"Män", "Kvinnor", "Båda könen"}
    if unknown_sexes:
        warnings.append(f"Unrecognized sex labels: {sorted(unknown_sexes)}.")
    if len(ages) != 19:
        warnings.append(f"Found {len(ages)} age categories (original dataset has 19); inspect any additions.")
    try:
        total_age = detect_all_ages(ages)
        unusual_ages = [a for a in ages if a != total_age and not re.fullmatch(r"\d+–\d+|\d+\+", normalize_age_label(a))]
        if unusual_ages:
            warnings.append(f"Unusual age labels (inspect against source): {unusual_ages}.")
    except DataValidationError as err:
        errors.append(str(err))
    try:
        verify_disjoint_age_groups(ages)
    except DataValidationError as err:
        warnings.append(f"Age breakdown unsafe: {err}")
    try:
        detect_both_sexes(sexes)
    except DataValidationError as err:
        errors.append(str(err))
    try:
        verify_disjoint_sex_groups(sexes)
    except DataValidationError as err:
        warnings.append(f"Sex breakdown unsafe: {err}")

    # Consistency audit only. The app still plots the original published rates;
    # it never replaces them with the calculated check values.
    nonpositive_population = frame["Befolkning"].notna() & frame["Befolkning"].le(0)
    if nonpositive_population.any():
        errors.append(f"Non-positive population denominators in {int(nonpositive_population.sum())} rows.")
    for count_column, rate_column in (
        paired_measure_columns("patients_rate"), paired_measure_columns("dispensings_rate")
    ):
        usable = frame[[count_column, rate_column, "Befolkning"]].notna().all(axis=1)
        usable &= frame["Befolkning"].gt(0).fillna(False)
        difference = (
            frame.loc[usable, count_column] * 1000 / frame.loc[usable, "Befolkning"]
            - frame.loc[usable, rate_column]
        ).abs()
        mismatched = int((difference > 0.00501).sum())
        if mismatched:
            warnings.append(
                f"{rate_column}: {mismatched} rows disagree with count/population "
                "beyond two-decimal rounding; inspect source definitions."
            )

    return ValidationReport(
        observations=len(frame), years=years, regions=regions,
        sexes=sexes, ages=ages, drugs=drugs,
        errors=tuple(errors), warnings=tuple(warnings),
    )


def ordered_ages(ages: tuple[str, ...] | list[str], *, include_aggregate: bool = True) -> list[str]:
    values = list(ages)
    if not include_aggregate:
        total = detect_all_ages(values)
        values = [age for age in values if age != total]

    def key(label: str) -> tuple[int, int, str]:
        normalized = normalize_age_label(label)
        match = re.match(r"^(\d+)", normalized)
        # Push the aggregate to the end, after constituent groups.
        is_total = bool(re.fullmatch(r"0–\d+\+", normalized)) or normalized.casefold() in {
            "alla åldrar", "samtliga åldrar", "all ages", "totalt", "total"
        }
        return (1 if is_total else 0, int(match.group(1)) if match else 10**7, normalized)

    return sorted(values, key=key)


def filter_observations(
    frame: pd.DataFrame,
    *,
    year_range: tuple[int, int] | None = None,
    years: list[int] | None = None,
    regions: list[str] | None = None,
    sex: str | None = None,
    age: str | None = None,
    drug: str | None = None,
) -> pd.DataFrame:
    """Subset only; never sum or average across any categories."""
    mask = pd.Series(True, index=frame.index)
    if year_range is not None:
        first, last = year_range
        if first > last:
            raise ValueError("Year range must be ascending.")
        mask &= frame["År"].between(first, last)
    if years is not None:
        mask &= frame["År"].isin(years)
    if regions is not None:
        mask &= frame["Region"].isin(regions)
    if sex is not None:
        mask &= frame["Kön"].eq(sex)
    if age is not None:
        mask &= frame["Ålder"].eq(age)
    if drug is not None:
        mask &= frame["Läkemedel"].eq(drug)
    return frame.loc[mask].copy()


def select_measure(frame: pd.DataFrame, measure_key: str) -> pd.DataFrame:
    """Add one well-defined measurement; keep source columns for traceability."""
    if measure_key not in MEASURES:
        raise ValueError(f"Unknown measurement {measure_key!r}")
    metric = MEASURES[measure_key]
    selected = frame.copy()
    selected["Värde"] = selected[metric.source_column]
    selected["Mått"] = metric.label
    selected["Enhet"] = metric.unit
    return selected


def _require_unique(frame: pd.DataFrame, unique_by: list[str], view: str) -> None:
    if frame.duplicated(unique_by).any():
        raise DataValidationError(
            f"{view} would combine multiple source observations per {unique_by}. "
            "Select one non-overlapping category instead."
        )


def prepare_trend(
    frame: pd.DataFrame, *, year_range: tuple[int, int], regions: list[str],
    sex: str, age: str, drug: str, measure_key: str,
) -> pd.DataFrame:
    selected = filter_observations(
        frame, year_range=year_range, regions=regions, sex=sex, age=age, drug=drug
    )
    _require_unique(selected, ["År", "Region"], "Trend")
    return select_measure(selected, measure_key).sort_values(["Region", "År"])


def prepare_regional(
    frame: pd.DataFrame, *, year: int, sex: str, age: str,
    drug: str, measure_key: str,
) -> tuple[pd.DataFrame, float | None]:
    """Individual region rows only, plus original national value as separate reference."""
    selected = filter_observations(frame, years=[year], sex=sex, age=age, drug=drug)
    _require_unique(selected, ["Region"], "Regional comparison")
    selected = select_measure(selected, measure_key)
    national = selected.loc[selected["Region"].eq("Riket"), "Värde"].dropna()
    reference = float(national.iloc[0]) if len(national) == 1 else None
    regional = selected.loc[selected["Region"].ne("Riket")].copy()
    regional = regional.sort_values("Värde", ascending=True, na_position="first")
    return regional, reference


def prepare_demographics(
    frame: pd.DataFrame, *, year: int, region: str, drug: str,
    measure_key: str, dimension: str, sex: str, age: str,
) -> pd.DataFrame:
    """Compare non-overlapping age OR sex groups; never include total among parts."""
    selected = filter_observations(frame, years=[year], regions=[region], drug=drug)
    if dimension == "age":
        verify_disjoint_age_groups(list(frame["\u00c5lder"].dropna().unique()))
        selected = selected.loc[selected["Kön"].eq(sex)].copy()
        aggregate = detect_all_ages(list(frame["Ålder"].dropna().unique()))
        selected = selected.loc[selected["Ålder"].ne(aggregate)].copy()
        selected["Jämförelsegrupp"] = selected["Ålder (visning)"]
        selected["_sort"] = selected["Ålder"].map(
            {age: idx for idx, age in enumerate(ordered_ages(list(frame["Ålder"].unique()), include_aggregate=False))}
        )
        _require_unique(selected, ["Ålder"], "Age comparison")
        selected = selected.sort_values("_sort").drop(columns="_sort")
    elif dimension == "sex":
        verify_disjoint_sex_groups(list(frame["K\u00f6n"].dropna().unique()))
        selected = selected.loc[selected["Ålder"].eq(age)].copy()
        aggregate = detect_both_sexes(list(frame["Kön"].dropna().unique()))
        selected = selected.loc[selected["Kön"].ne(aggregate)].copy()
        selected["Jämförelsegrupp"] = selected["Kön"]
        _require_unique(selected, ["Kön"], "Sex comparison")
        selected = selected.sort_values("Kön")
    else:
        raise ValueError("dimension must be 'age' or 'sex'")
    return select_measure(selected, measure_key)


def exported_csv(rows: pd.DataFrame, measure_key: str) -> bytes:
    """Download the view's rows with all original fields and selected measurement.

    Use semicolon/decimal-comma Swedish CSV plus UTF-8 BOM for spreadsheet readers.
    No aggregation is applied in preparing the download.
    """
    if measure_key not in MEASURES:
        raise ValueError(f"Unknown measurement {measure_key}")
    metric = MEASURES[measure_key]
    # Some tests/callers may pass unmeasured filtered rows.
    displayed = select_measure(rows, measure_key)
    cols = list(SOURCE_COLUMNS) + ["Ålder (visning)", "Mått", "Värde", "Enhet"]
    output = displayed[cols].copy()
    # Preserve the source's two-decimal precision in the Swedish CSV export;
    # Pandas otherwise writes an exact published 0.00 rate as 0,0.
    def rate_text(value: object) -> str:
        return "" if pd.isna(value) else f"{float(value):.2f}".replace(".", ",")

    for column in RATE_COLUMNS:
        output[column] = output[column].map(rate_text)
    if metric.decimals == 2:
        output["Värde"] = output["Värde"].map(rate_text)
    return output.to_csv(index=False, sep=";", decimal=",", lineterminator="\n").encode("utf-8-sig")


def formatted_value(value: object, measure_key: str) -> str:
    if pd.isna(value):
        return "Not reported"
    metric = MEASURES[measure_key]
    return f"{float(value):,.{metric.decimals}f}"
