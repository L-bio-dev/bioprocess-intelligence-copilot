"""Score an assessment batch against reference-batch trajectories."""

from pathlib import Path

import numpy as np
import pandas as pd

from src.data_validation import validate_dataset


PROCESS_VARIABLES = [
    "ph",
    "dissolved_oxygen_pct",
    "temperature_c",
    "agitation_rpm",
    "feed_rate_ml_h",
]

ROBUST_Z_THRESHOLD = 5.0


def calculate_reference_statistics(
    values: pd.Series,
) -> tuple[float, float]:
    """Calculate a robust centre and scale for reference values."""

    numeric_values = values.to_numpy(dtype=float)
    median = float(np.median(numeric_values))

    median_absolute_deviation = float(
        np.median(np.abs(numeric_values - median))
    )

    robust_scale = 1.4826 * median_absolute_deviation

    if robust_scale < 1e-9:
        standard_deviation = float(
            np.std(numeric_values, ddof=1)
        )
        robust_scale = max(standard_deviation, 1e-9)

    return median, robust_scale


def score_assessment_batch(data: pd.DataFrame) -> pd.DataFrame:
    """Compare every assessment value with references at the same time."""

    validation = validate_dataset(data)

    if not validation.is_valid:
        raise ValueError(
            "Dataset validation failed: "
            + "; ".join(validation.errors)
        )

    reference_data = data[data["batch_role"] == "reference"]
    assessment_data = data[data["batch_role"] == "assessment"]

    assessment_batch_id = assessment_data["batch_id"].unique()[0]

    references_by_time = {
        elapsed_time: time_data
        for elapsed_time, time_data in reference_data.groupby(
            "elapsed_time_h"
        )
    }

    records = []

    for row in assessment_data.sort_values(
        "elapsed_time_h"
    ).itertuples(index=False):
        elapsed_time = row.elapsed_time_h
        reference_at_time = references_by_time[elapsed_time]

        for variable in PROCESS_VARIABLES:
            reference_median, reference_scale = (
                calculate_reference_statistics(
                    reference_at_time[variable]
                )
            )

            assessment_value = float(getattr(row, variable))

            robust_z_score = (
                assessment_value - reference_median
            ) / reference_scale

            records.append(
                {
                    "batch_id": assessment_batch_id,
                    "elapsed_time_h": elapsed_time,
                    "variable": variable,
                    "assessment_value": assessment_value,
                    "reference_median": reference_median,
                    "reference_scale": reference_scale,
                    "robust_z_score": robust_z_score,
                    "absolute_score": abs(robust_z_score),
                    "is_anomaly": (
                        abs(robust_z_score)
                        >= ROBUST_Z_THRESHOLD
                    ),
                }
            )

    return pd.DataFrame(records)


def main() -> None:
    """Score the synthetic assessment batch and save the results."""

    project_root = Path(__file__).resolve().parents[1]

    input_path = (
        project_root
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    output_directory = project_root / "data" / "processed"
    output_path = output_directory / "anomaly_scores.csv"

    data = pd.read_csv(input_path)
    scores = score_assessment_batch(data)

    output_directory.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_path, index=False)

    flagged_scores = scores[scores["is_anomaly"]]

    print(f"Created: {output_path}")
    print(f"Scored observations: {len(scores)}")
    print(f"Flagged observations: {len(flagged_scores)}")

    if not flagged_scores.empty:
        print("\nFlags by variable:")
        print(
            flagged_scores.groupby("variable")
            .size()
            .sort_values(ascending=False)
        )


if __name__ == "__main__":
    main()