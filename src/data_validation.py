"""Validate uploaded bioprocess data against the MVP data contract."""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


MINIMUM_REFERENCE_BATCHES = 10

REQUIRED_COLUMNS = [
    "batch_id",
    "batch_role",
    "elapsed_time_h",
    "ph",
    "dissolved_oxygen_pct",
    "temperature_c",
    "agitation_rpm",
    "feed_rate_ml_h",
]

NUMERIC_COLUMNS = [
    "elapsed_time_h",
    "ph",
    "dissolved_oxygen_pct",
    "temperature_c",
    "agitation_rpm",
    "feed_rate_ml_h",
]

ALLOWED_BATCH_ROLES = {"reference", "assessment"}


@dataclass
class ValidationResult:
    """Store errors and warnings produced during validation."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_dataset(data: pd.DataFrame) -> ValidationResult:
    """Check a dataset against the documented MVP rules."""

    result = ValidationResult()

    if data.empty:
        result.errors.append("The dataset is empty.")
        return result

    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in data.columns
    ]

    if missing_columns:
        result.errors.append(
            f"Missing required columns: {', '.join(missing_columns)}."
        )
        return result

    extra_columns = [
        column for column in data.columns if column not in REQUIRED_COLUMNS
    ]

    if extra_columns:
        result.warnings.append(
            f"Extra columns will be ignored: {', '.join(extra_columns)}."
        )

    missing_value_count = int(data[REQUIRED_COLUMNS].isna().sum().sum())

    if missing_value_count > 0:
        result.errors.append(
            f"Found {missing_value_count} missing required values."
        )

    blank_batch_ids = (
        data["batch_id"].fillna("").astype(str).str.strip().eq("").sum()
    )

    if blank_batch_ids > 0:
        result.errors.append(
            f"Found {blank_batch_ids} empty batch identifiers."
        )

    invalid_roles = sorted(
        set(data["batch_role"].dropna().astype(str))
        - ALLOWED_BATCH_ROLES
    )

    if invalid_roles:
        result.errors.append(
            f"Invalid batch roles: {', '.join(invalid_roles)}."
        )

    roles_per_batch = data.groupby("batch_id")["batch_role"].nunique()

    if (roles_per_batch > 1).any():
        result.errors.append(
            "A batch identifier cannot have more than one batch role."
        )

    reference_count = data.loc[
        data["batch_role"] == "reference", "batch_id"
    ].nunique()

    assessment_count = data.loc[
        data["batch_role"] == "assessment", "batch_id"
    ].nunique()

    if reference_count < MINIMUM_REFERENCE_BATCHES:
        result.errors.append(
            "At least "
            f"{MINIMUM_REFERENCE_BATCHES} reference batches are required; "
            f"found {reference_count}."
        )

    if assessment_count != 1:
        result.errors.append(
            f"Exactly one assessment batch is required; found "
            f"{assessment_count}."
        )

    duplicate_count = int(
        data.duplicated(["batch_id", "elapsed_time_h"]).sum()
    )

    if duplicate_count > 0:
        result.errors.append(
            f"Found {duplicate_count} duplicated batch-time observations."
        )

    numeric_data = data[NUMERIC_COLUMNS].apply(
        pd.to_numeric,
        errors="coerce",
    )

    for column in NUMERIC_COLUMNS:
        invalid_count = int(
            (
                numeric_data[column].isna()
                & data[column].notna()
            ).sum()
        )

        if invalid_count > 0:
            result.errors.append(
                f"Column '{column}' contains "
                f"{invalid_count} non-numeric values."
            )

    if (numeric_data["elapsed_time_h"].dropna() < 0).any():
        result.errors.append("Elapsed time cannot be negative.")

    if (
        (numeric_data["ph"].dropna() < 0)
        | (numeric_data["ph"].dropna() > 14)
    ).any():
        result.errors.append("pH values must be between 0 and 14.")

    non_negative_columns = [
        "dissolved_oxygen_pct",
        "agitation_rpm",
        "feed_rate_ml_h",
    ]

    for column in non_negative_columns:
        if (numeric_data[column].dropna() < 0).any():
            result.errors.append(
                f"Column '{column}' cannot contain negative values."
            )

    finite_values = numeric_data.to_numpy(dtype=float)

    if not np.isfinite(finite_values[~np.isnan(finite_values)]).all():
        result.errors.append(
            "Numeric columns cannot contain infinite values."
        )

    time_data = data[["batch_id"]].copy()
    time_data["elapsed_time_h"] = numeric_data["elapsed_time_h"]

    if time_data["elapsed_time_h"].notna().all():
        time_grids: list[np.ndarray] = []

        for batch_id, batch_data in time_data.groupby(
            "batch_id",
            sort=False,
        ):
            times = batch_data["elapsed_time_h"]

            if not times.is_monotonic_increasing:
                result.warnings.append(
                    f"Batch '{batch_id}' is not ordered by elapsed time."
                )

            time_grids.append(np.sort(times.unique()))

        if time_grids:
            expected_grid = time_grids[0]

            if any(
                not np.array_equal(grid, expected_grid)
                for grid in time_grids[1:]
            ):
                result.errors.append(
                    "All batches must use the same measurement times."
                )

    return result


def main() -> None:
    """Validate the synthetic demonstration dataset."""

    project_root = Path(__file__).resolve().parents[1]
    data_path = (
        project_root
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    data = pd.read_csv(data_path)
    result = validate_dataset(data)

    print(f"File: {data_path}")
    print(f"Valid: {result.is_valid}")

    for error in result.errors:
        print(f"ERROR: {error}")

    for warning in result.warnings:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()