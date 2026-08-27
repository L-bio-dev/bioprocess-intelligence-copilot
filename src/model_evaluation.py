"""Evaluate anomaly detectors against synthetic ground truth."""

from pathlib import Path

import pandas as pd

from src.anomaly_detection import score_assessment_batch
from src.isolation_forest_detection import (
    score_with_isolation_forest,
)


def create_expected_anomaly_hours(
    ground_truth: pd.DataFrame,
) -> set[int]:
    """Convert documented anomaly intervals into individual hours."""

    expected_hours = set()

    for event in ground_truth.itertuples(index=False):
        expected_hours.update(
            range(
                int(event.start_time_h),
                int(event.end_time_h) + 1,
            )
        )

    return expected_hours


def calculate_metrics(
    expected: set[int],
    predicted: set[int],
    all_hours: set[int],
) -> dict[str, float | int]:
    """Calculate time-point classification metrics."""

    true_positives = len(expected & predicted)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)
    true_negatives = len(all_hours - (expected | predicted))

    precision = (
        true_positives
        / (true_positives + false_positives)
        if true_positives + false_positives > 0
        else 0.0
    )

    recall = (
        true_positives
        / (true_positives + false_negatives)
        if true_positives + false_negatives > 0
        else 0.0
    )

    f1_score = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
    }


def evaluate_models(
    data: pd.DataFrame,
    ground_truth: pd.DataFrame,
) -> tuple[pd.DataFrame, set[int], set[int], set[int]]:
    """Evaluate both detectors using the same expected anomaly hours."""

    expected_hours = create_expected_anomaly_hours(
        ground_truth
    )

    all_hours = set(
        data.loc[
            data["batch_role"] == "assessment",
            "elapsed_time_h",
        ].astype(int)
    )

    interpretable_scores = score_assessment_batch(data)

    interpretable_flags = set(
        interpretable_scores.loc[
            interpretable_scores["is_anomaly"],
            "elapsed_time_h",
        ].astype(int)
    )

    ml_scores = score_with_isolation_forest(data)

    ml_flags = set(
        ml_scores.loc[
            ml_scores["is_ml_anomaly"],
            "elapsed_time_h",
        ].astype(int)
    )

    evaluation = pd.DataFrame(
        [
            {
                "model": "Robust Z-score",
                **calculate_metrics(
                    expected_hours,
                    interpretable_flags,
                    all_hours,
                ),
            },
            {
                "model": "Isolation Forest",
                **calculate_metrics(
                    expected_hours,
                    ml_flags,
                    all_hours,
                ),
            },
        ]
    )

    return (
        evaluation,
        expected_hours,
        interpretable_flags,
        ml_flags,
    )


def main() -> None:
    """Evaluate the models and save the comparison."""

    project_root = Path(__file__).resolve().parents[1]

    data_path = (
        project_root
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    truth_path = (
        project_root
        / "data"
        / "synthetic"
        / "anomaly_ground_truth.csv"
    )

    output_path = (
        project_root
        / "data"
        / "processed"
        / "model_evaluation.csv"
    )

    data = pd.read_csv(data_path)
    ground_truth = pd.read_csv(truth_path)

    (
        evaluation,
        expected_hours,
        _,
        ml_flags,
    ) = evaluate_models(data, ground_truth)

    evaluation.to_csv(output_path, index=False)

    display = evaluation.copy()

    percentage_columns = [
        "precision",
        "recall",
        "f1_score",
    ]

    display[percentage_columns] = (
        display[percentage_columns] * 100
    ).round(1)

    print(f"Created: {output_path}")
    print()
    print(display.to_string(index=False))
    print()
    print(
        "Isolation Forest missed hours:",
        sorted(expected_hours - ml_flags),
    )
    print(
        "Isolation Forest false-positive hours:",
        sorted(ml_flags - expected_hours),
    )


if __name__ == "__main__":
    main()