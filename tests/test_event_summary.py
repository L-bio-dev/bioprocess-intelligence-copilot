"""Automated tests for process-event summarization."""

from pathlib import Path

import pandas as pd
import pytest

from src.anomaly_detection import score_assessment_batch
from src.event_summary import (
    create_hourly_consensus,
    summarize_process_events,
)
from src.isolation_forest_detection import (
    score_with_isolation_forest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def summary_outputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create detector consensus and process events once."""

    data_path = (
        PROJECT_ROOT
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    data = pd.read_csv(data_path)

    interpretable_scores = score_assessment_batch(data)
    ml_scores = score_with_isolation_forest(data)

    consensus = create_hourly_consensus(
        interpretable_scores,
        ml_scores,
    )

    events = summarize_process_events(consensus)

    return consensus, events


def test_hourly_consensus_categories(
    summary_outputs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Confirm the expected detector-agreement categories."""

    consensus, _ = summary_outputs

    status_counts = (
        consensus["detector_status"]
        .value_counts()
        .to_dict()
    )

    assert len(consensus) == 241
    assert status_counts["normal"] == 185
    assert status_counts["corroborated"] == 42
    assert status_counts["interpretable_only"] == 4
    assert status_counts["ml_only_review"] == 10

    ml_only_hours = consensus.loc[
        consensus["detector_status"] == "ml_only_review",
        "elapsed_time_h",
    ].astype(int).tolist()

    assert ml_only_hours == [
        30,
        35,
        38,
        90,
        104,
        145,
        219,
        221,
        231,
        236,
    ]


def test_process_events_are_summarized_correctly(
    summary_outputs: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Confirm the two known process-event summaries."""

    _, events = summary_outputs

    assert len(events) == 2

    feed_event = events.iloc[0]
    oxygen_event = events.iloc[1]

    assert feed_event["event_id"] == "EVENT_001"
    assert feed_event["start_time_h"] == 120
    assert feed_event["end_time_h"] == 144
    assert feed_event["flagged_time_points"] == 25
    assert feed_event["affected_variables"] == "feed_rate_ml_h"
    assert feed_event["ml_corroborated_time_points"] == 21
    assert feed_event["ml_corroboration_pct"] == 84.0

    assert oxygen_event["event_id"] == "EVENT_002"
    assert oxygen_event["start_time_h"] == 170
    assert oxygen_event["end_time_h"] == 190
    assert oxygen_event["flagged_time_points"] == 21
    assert oxygen_event["affected_variables"] == (
        "agitation_rpm; dissolved_oxygen_pct"
    )
    assert oxygen_event["ml_corroborated_time_points"] == 21
    assert oxygen_event["ml_corroboration_pct"] == 100.0