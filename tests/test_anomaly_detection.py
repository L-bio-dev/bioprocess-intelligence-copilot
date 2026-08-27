"""Automated tests for anomaly detection."""

from pathlib import Path

import pandas as pd

from src.anomaly_detection import score_assessment_batch


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_injected_anomalies_are_recovered_exactly() -> None:
    """Confirm that the detector recovers the known synthetic events."""

    data_path = (
        PROJECT_ROOT
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    data = pd.read_csv(data_path)
    scores = score_assessment_batch(data)

    flagged = scores[scores["is_anomaly"]]

    feed_times = set(
        flagged.loc[
            flagged["variable"] == "feed_rate_ml_h",
            "elapsed_time_h",
        ]
    )

    oxygen_times = set(
        flagged.loc[
            flagged["variable"] == "dissolved_oxygen_pct",
            "elapsed_time_h",
        ]
    )

    agitation_times = set(
        flagged.loc[
            flagged["variable"] == "agitation_rpm",
            "elapsed_time_h",
        ]
    )

    assert feed_times == set(range(120, 145))
    assert oxygen_times == set(range(170, 191))
    assert agitation_times == set(range(170, 191))

    assert not flagged["variable"].isin(
        ["ph", "temperature_c"]
    ).any()