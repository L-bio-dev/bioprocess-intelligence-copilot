"""Combine detector outputs into process-level event summaries."""

from pathlib import Path

import pandas as pd

from src.anomaly_detection import score_assessment_batch
from src.isolation_forest_detection import (
    score_with_isolation_forest,
)


def create_hourly_consensus(
    interpretable_scores: pd.DataFrame,
    ml_scores: pd.DataFrame,
) -> pd.DataFrame:
    """Combine both detector outputs at each assessment time point."""

    ml_by_time = ml_scores.set_index("elapsed_time_h")
    records = []

    for elapsed_time, time_scores in interpretable_scores.groupby(
        "elapsed_time_h",
        sort=True,
    ):
        robust_flags = time_scores[
            time_scores["is_anomaly"]
        ]

        robust_anomaly = not robust_flags.empty

        flagged_variables = sorted(
            robust_flags["variable"].unique()
        )

        ml_row = ml_by_time.loc[elapsed_time]
        ml_anomaly = bool(ml_row["is_ml_anomaly"])

        if robust_anomaly and ml_anomaly:
            detector_status = "corroborated"
        elif robust_anomaly:
            detector_status = "interpretable_only"
        elif ml_anomaly:
            detector_status = "ml_only_review"
        else:
            detector_status = "normal"

        records.append(
            {
                "elapsed_time_h": elapsed_time,
                "robust_anomaly": robust_anomaly,
                "ml_anomaly": ml_anomaly,
                "detector_status": detector_status,
                "flagged_variables": "; ".join(
                    flagged_variables
                ),
                "maximum_robust_score": float(
                    time_scores["absolute_score"].max()
                ),
                "ml_anomaly_score": float(
                    ml_row["ml_anomaly_score"]
                ),
                "ml_threshold": float(
                    ml_row["ml_threshold"]
                ),
            }
        )

    return pd.DataFrame(records)


def group_consecutive_hours(
    hours: set[int],
) -> list[tuple[int, int]]:
    """Group one-hour consecutive flags into intervals."""

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


def summarize_process_events(
    consensus: pd.DataFrame,
) -> pd.DataFrame:
    """Group flagged consecutive observations, preserving their actual times."""

    columns = [
        "event_id",
        "start_time_h",
        "end_time_h",
        "flagged_time_points",
        "affected_variables",
        "ml_corroborated_time_points",
        "ml_corroboration_pct",
        "maximum_robust_score",
    ]
    if consensus.empty:
        return pd.DataFrame(columns=columns)

    ordered = consensus.sort_values("elapsed_time_h").copy()
    flags = ordered["robust_anomaly"].astype(bool)
    # Each normal observation breaks an event. ML-only flags cannot start one.
    ordered["_event_group"] = flags.ne(flags.shift(fill_value=False)).cumsum()
    flagged = ordered.loc[flags]
    events = []

    for event_number, (_, event_data) in enumerate(
        flagged.groupby("_event_group", sort=True), start=1
    ):
        variables = set()
        for value in event_data["flagged_variables"]:
            if value:
                variables.update(value.split("; "))

        flagged_time_points = len(event_data)
        ml_corroborated_points = int(event_data["ml_anomaly"].sum())

        events.append(
            {
                "event_id": f"EVENT_{event_number:03d}",
                "start_time_h": float(event_data["elapsed_time_h"].iloc[0]),
                "end_time_h": float(event_data["elapsed_time_h"].iloc[-1]),
                "flagged_time_points": flagged_time_points,
                "affected_variables": "; ".join(sorted(variables)),
                "ml_corroborated_time_points": ml_corroborated_points,
                "ml_corroboration_pct": round(
                    100 * ml_corroborated_points / flagged_time_points, 1
                ),
                "maximum_robust_score": float(
                    event_data["maximum_robust_score"].max()
                ),
            }
        )

    return pd.DataFrame(events, columns=columns)


def main() -> None:
    """Generate consensus and event-summary CSV files."""

    project_root = Path(__file__).resolve().parents[1]

    input_path = (
        project_root
        / "data"
        / "synthetic"
        / "bioprocess_batches.csv"
    )

    output_directory = project_root / "data" / "processed"

    consensus_path = (
        output_directory
        / "hourly_detector_consensus.csv"
    )

    events_path = (
        output_directory
        / "process_events.csv"
    )

    data = pd.read_csv(input_path)

    interpretable_scores = score_assessment_batch(data)
    ml_scores = score_with_isolation_forest(data)

    consensus = create_hourly_consensus(
        interpretable_scores,
        ml_scores,
    )

    events = summarize_process_events(consensus)

    output_directory.mkdir(parents=True, exist_ok=True)

    consensus.to_csv(consensus_path, index=False)
    events.to_csv(events_path, index=False)

    ml_only_hours = consensus.loc[
        consensus["detector_status"] == "ml_only_review",
        "elapsed_time_h",
    ].astype(int).tolist()

    print(f"Created: {consensus_path}")
    print(f"Created: {events_path}")
    print(f"Process events: {len(events)}")
    print()

    for event in events.itertuples(index=False):
        print(
            f"{event.event_id}: "
            f"{event.start_time_h:g}–{event.end_time_h:g} h | "
            f"{event.affected_variables} | "
            "ML corroboration: "
            f"{event.ml_corroboration_pct:.1f}%"
        )

    print()
    print("ML-only review hours:", ml_only_hours)


if __name__ == "__main__":
    main()