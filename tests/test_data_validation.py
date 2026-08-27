"""Automated tests for the data-validation component."""

import pandas as pd

from src.data_validation import validate_dataset


def create_valid_dataset() -> pd.DataFrame:
    """Create a small valid dataset used by the tests."""

    rows = []

    batch_definitions = [
        *[
            (f"REF_{number:03d}", "reference")
            for number in range(1, 11)
        ],
        ("ASSESS_001", "assessment"),
    ]

    for batch_id, batch_role in batch_definitions:
        for elapsed_time_h in [0, 1]:
            rows.append(
                {
                    "batch_id": batch_id,
                    "batch_role": batch_role,
                    "elapsed_time_h": elapsed_time_h,
                    "ph": 7.10,
                    "dissolved_oxygen_pct": 40.0,
                    "temperature_c": 36.8,
                    "agitation_rpm": 100.0,
                    "feed_rate_ml_h": 0.0,
                }
            )

    return pd.DataFrame(rows)


def test_valid_dataset_is_accepted() -> None:
    data = create_valid_dataset()

    result = validate_dataset(data)

    assert result.is_valid
    assert result.errors == []


def test_missing_column_is_rejected() -> None:
    data = create_valid_dataset().drop(columns=["ph"])

    result = validate_dataset(data)

    assert not result.is_valid
    assert any("Missing required columns" in error for error in result.errors)


def test_duplicate_observation_is_rejected() -> None:
    data = create_valid_dataset()
    data = pd.concat([data, data.iloc[[0]]], ignore_index=True)

    result = validate_dataset(data)

    assert not result.is_valid
    assert any("duplicated" in error for error in result.errors)


def test_multiple_assessment_batches_are_rejected() -> None:
    data = create_valid_dataset()
    data.loc[
        data["batch_id"] == "REF_001",
        "batch_role",
    ] = "assessment"

    result = validate_dataset(data)

    assert not result.is_valid
    assert any(
        "Exactly one assessment batch" in error
        for error in result.errors
    )


def test_non_numeric_value_is_rejected() -> None:
    data = create_valid_dataset()
    data["ph"] = data["ph"].astype(object)
    data.loc[0, "ph"] = "not-a-number"

    result = validate_dataset(data)

    assert not result.is_valid
    assert any("non-numeric" in error for error in result.errors)


def test_invalid_ph_is_rejected() -> None:
    data = create_valid_dataset()
    data.loc[0, "ph"] = 15.0

    result = validate_dataset(data)

    assert not result.is_valid
    assert any(
        "between 0 and 14" in error
        for error in result.errors
    )


def test_inconsistent_time_grid_is_rejected() -> None:
    data = create_valid_dataset()
    data = data[
        ~(
            (data["batch_id"] == "REF_001")
            & (data["elapsed_time_h"] == 1)
        )
    ]

    result = validate_dataset(data)

    assert not result.is_valid
    assert any(
        "same measurement times" in error
        for error in result.errors
    )