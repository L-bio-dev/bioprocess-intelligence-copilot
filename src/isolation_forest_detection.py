"""Detect multivariate anomalies with Isolation Forest."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.anomaly_detection import (
    PROCESS_VARIABLES,
    calculate_reference_statistics,
)
from src.data_validation import validate_dataset


RANDOM_SEED = 42
REFERENCE_SCORE_QUANTILE = 0.995


def create_normalized_features(
    data: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Normalize each variable against references at the same time."""

    validation = validate_dataset(data)

    if not validation.is_valid:
        raise ValueError(
            "Dataset validation failed: "
            + "; ".join(validation.errors)
        )

    reference_data = data[data["batch_role"] == "reference"]
    assessment_data = data[data["batch_role"] == "assessment"]

    reference_features = []
    assessment_features = []
    assessment_metadata = []

    measurement_times = sorted(
        assessment_data["elapsed_time_h"].unique()
    )

    for elapsed_time in measurement_times:
        reference_at_time = reference_data[
            reference_data["elapsed_time_h"] == elapsed_time
        ]

        assessment_at_time = assessment_data[
            assessment_data["elapsed_time_h"] == elapsed_time
        ].iloc[0]

        statistics = {
            variable: calculate_reference_statistics(
                reference_at_time[variable]
            )
            for variable in PROCESS_VARIABLES
        }

        for reference_row in reference_at_time.itertuples(
            index=False
        ):
            reference_features.append(
                [
                    (
                        float(getattr(reference_row, variable))
                        - statistics[variable][0]
                    )
                    / statistics[variable][1]
                    for variable in PROCESS_VARIABLES
                ]
            )

        assessment_features.append(
            [
                (
                    float(assessment_at_time[variable])
                    - statistics[variable][0]
                )
                / statistics[variable][1]
                for variable in PROCESS_VARIABLES
            ]
        )

        assessment_metadata.append(
            {
                "batch_id": assessment_at_time["batch_id"],
                "elapsed_time_h": elapsed_time,
            }
        )

    return (
        np.asarray(reference_features, dtype=float),
        np.asarray(assessment_features, dtype=float),
        pd.DataFrame(assessment_metadata),
    )


def score_with_isolation_forest(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """Train on reference behaviour and score the assessment batch."""

    (
        reference_features,
        assessment_features,
        assessment_metadata,
    ) = create_normalized_features(data)

    model = IsolationForest(
        n_estimators=300,
        contamination="auto",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    model.fit(reference_features)

    reference_scores = -model.score_samples(reference_features)
    assessment_scores = -model.score_samples(assessment_features)

    threshold = float(
        np.quantile(
            reference_scores,
            REFERENCE_SCORE_QUANTILE,
        )
    )

    results = assessment_metadata.copy()
    results["ml_anomaly_score"] = assessment_scores
    results["ml_threshold"] = threshold
    results["is_ml_anomaly"] = assessment_scores >= threshold

    return results


def group_consecutive_hours(
    hours: list[float],
) -> list[tuple[float, float]]:
    """Group one-hour consecutive flags into readable intervals."""

    if not hours:
        return []

    ordered_hours = sorted(hours)
    intervals = []

    start = ordered_hours[0]
    previous = ordered_hours[0]

    for current in ordered_hours[1:]:
        if current == previous + 1:
            previous = current
            continue

        intervals.append((start, previous))
        start = current
        previous = current

    intervals.append((start, previous))

    return intervals


def main() -> None:
    """Run Isolation Forest on the synthetic demonstration data."""

    project_root = Path(__file__).resolve().parents[1]

    input_path = (
        project_root
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    output_directory = project_root / "data" / "processed"
    output_path = (
        output_directory
        / "isolation_forest_scores.csv"
    )

    data = pd.read_csv(input_path)
    results = score_with_isolation_forest(data)

    output_directory.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)

    flagged_hours = results.loc[
        results["is_ml_anomaly"],
        "elapsed_time_h",
    ].tolist()

    intervals = group_consecutive_hours(flagged_hours)

    print(f"Created: {output_path}")
    print(f"Assessment time points: {len(results)}")
    print(f"ML-flagged time points: {len(flagged_hours)}")
    print("ML-flagged intervals:")

    for start, end in intervals:
        print(f"  {start:g} h to {end:g} h")


if __name__ == "__main__":
    main()