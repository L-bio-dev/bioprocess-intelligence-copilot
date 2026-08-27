"""Automated tests for model evaluation."""

from pathlib import Path

import pandas as pd

from src.model_evaluation import (
    calculate_metrics,
    evaluate_models,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_metric_calculation() -> None:
    """Check metric calculations with a simple controlled example."""

    metrics = calculate_metrics(
        expected={1, 2},
        predicted={2, 3},
        all_hours={0, 1, 2, 3},
    )

    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["true_negatives"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1_score"] == 0.5


def test_models_meet_demo_performance_floor() -> None:
    """Confirm that both models meet documented demo performance."""

    data_path = (
        PROJECT_ROOT
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    truth_path = (
        PROJECT_ROOT
        / "data"
        / "synthetic"
        / "anomaly_ground_truth.csv"
    )

    data = pd.read_csv(data_path)
    ground_truth = pd.read_csv(truth_path)

    evaluation, _, _, _ = evaluate_models(
        data,
        ground_truth,
    )

    robust_result = evaluation.loc[
        evaluation["model"] == "Robust Z-score"
    ].iloc[0]

    isolation_result = evaluation.loc[
        evaluation["model"] == "Isolation Forest"
    ].iloc[0]

    assert robust_result["precision"] == 1.0
    assert robust_result["recall"] == 1.0
    assert robust_result["f1_score"] == 1.0

    assert isolation_result["precision"] >= 0.80
    assert isolation_result["recall"] >= 0.90
    assert isolation_result["f1_score"] >= 0.85