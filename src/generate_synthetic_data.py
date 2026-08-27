"""Generate synthetic fed-batch data for the project demo.

The generated values are educational and do not represent a real
manufacturing process or an operating recipe.
"""

from pathlib import Path

import numpy as np
import pandas as pd


RANDOM_SEED = 42
NUMBER_OF_REFERENCE_BATCHES = 20
TIME_HOURS = np.arange(0, 241, 1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "synthetic"

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


def create_base_profiles(time_h: np.ndarray) -> dict[str, np.ndarray]:
    """Create the common expected process trajectories."""

    ph = (
        7.10
        - 0.12 * (1 - np.exp(-time_h / 70))
        + 0.035 / (1 + np.exp(-(time_h - 150) / 15))
    )

    dissolved_oxygen = (
        40
        + 3.0 * np.sin(time_h / 18)
        + 1.5 * np.sin(time_h / 6)
    )

    temperature = np.where(time_h < 120, 36.8, 35.8)

    agitation = (
        100
        + 0.65 * time_h
        + 5 * np.sin(time_h / 18)
    )

    feed_rate = np.where(
        time_h < 24,
        0,
        4 + 0.18 * (time_h - 24),
    )

    return {
        "ph": ph,
        "dissolved_oxygen_pct": dissolved_oxygen,
        "temperature_c": temperature,
        "agitation_rpm": agitation,
        "feed_rate_ml_h": feed_rate,
    }


def generate_batch(
    batch_id: str,
    batch_role: str,
    rng: np.random.Generator,
    inject_anomalies: bool = False,
) -> pd.DataFrame:
    """Generate one batch with realistic small batch-to-batch variation."""

    base = create_base_profiles(TIME_HOURS)
    number_of_points = len(TIME_HOURS)

    ph = (
        base["ph"]
        + rng.normal(0, 0.015)
        + rng.normal(0, 0.008, number_of_points)
    )

    dissolved_oxygen = (
        base["dissolved_oxygen_pct"]
        + rng.normal(0, 1.5)
        + rng.normal(0, 0.8, number_of_points)
    )

    temperature = (
        base["temperature_c"]
        + rng.normal(0, 0.08)
        + rng.normal(0, 0.03, number_of_points)
    )

    agitation = (
        base["agitation_rpm"]
        + rng.normal(0, 4)
        + rng.normal(0, 1.5, number_of_points)
    )

    feed_rate = base["feed_rate_ml_h"] * rng.normal(1, 0.03)
    feed_rate = feed_rate + np.where(
        TIME_HOURS < 24,
        0,
        rng.normal(0, 0.15, number_of_points),
    )

    if inject_anomalies:
        feed_event = (TIME_HOURS >= 120) & (TIME_HOURS <= 144)
        feed_rate[feed_event] *= 0.65

        oxygen_event = (TIME_HOURS >= 170) & (TIME_HOURS <= 190)
        dissolved_oxygen[oxygen_event] -= 12
        agitation[oxygen_event] += 45

    return pd.DataFrame(
        {
            "batch_id": batch_id,
            "batch_role": batch_role,
            "elapsed_time_h": TIME_HOURS,
            "ph": np.round(ph, 3),
            "dissolved_oxygen_pct": np.round(
                np.clip(dissolved_oxygen, 0, 100), 2
            ),
            "temperature_c": np.round(temperature, 2),
            "agitation_rpm": np.round(np.clip(agitation, 0, None), 1),
            "feed_rate_ml_h": np.round(np.clip(feed_rate, 0, None), 2),
        }
    )


def validate_generated_data(data: pd.DataFrame) -> None:
    """Stop generation if the output breaks the data contract."""

    if list(data.columns) != REQUIRED_COLUMNS:
        raise ValueError("Generated columns do not match the data contract.")

    if data.isna().any().any():
        raise ValueError("Generated data contain missing values.")

    if data.duplicated(["batch_id", "elapsed_time_h"]).any():
        raise ValueError("Generated data contain duplicate observations.")

    reference_count = data.loc[
        data["batch_role"] == "reference", "batch_id"
    ].nunique()

    assessment_count = data.loc[
        data["batch_role"] == "assessment", "batch_id"
    ].nunique()

    if reference_count != NUMBER_OF_REFERENCE_BATCHES:
        raise ValueError("Incorrect number of reference batches.")

    if assessment_count != 1:
        raise ValueError("The dataset must contain one assessment batch.")


def main() -> None:
    """Generate, validate, and save the synthetic datasets."""

    rng = np.random.default_rng(RANDOM_SEED)

    batches = [
        generate_batch(
            batch_id=f"REF_{batch_number:03d}",
            batch_role="reference",
            rng=rng,
        )
        for batch_number in range(1, NUMBER_OF_REFERENCE_BATCHES + 1)
    ]

    batches.append(
        generate_batch(
            batch_id="ASSESS_001",
            batch_role="assessment",
            rng=rng,
            inject_anomalies=True,
        )
    )

    data = pd.concat(batches, ignore_index=True)
    validate_generated_data(data)

    anomaly_ground_truth = pd.DataFrame(
        [
            {
                "event_id": "EVENT_001",
                "batch_id": "ASSESS_001",
                "start_time_h": 120,
                "end_time_h": 144,
                "affected_variables": "feed_rate_ml_h",
                "injected_change": "Feed rate multiplied by 0.65",
            },
            {
                "event_id": "EVENT_002",
                "batch_id": "ASSESS_001",
                "start_time_h": 170,
                "end_time_h": 190,
                "affected_variables": (
                    "dissolved_oxygen_pct; agitation_rpm"
                ),
                "injected_change": (
                    "Dissolved oxygen reduced by 12 percentage points; "
                    "agitation increased by 45 rpm"
                ),
            },
        ]
    )

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    data_path = OUTPUT_DIRECTORY / "bioprocess_batches.csv"
    truth_path = OUTPUT_DIRECTORY / "anomaly_ground_truth.csv"

    data.to_csv(data_path, index=False)
    anomaly_ground_truth.to_csv(truth_path, index=False)

    print(f"Created: {data_path}")
    print(f"Created: {truth_path}")
    print(f"Batches: {data['batch_id'].nunique()}")
    print(f"Rows: {len(data)}")


if __name__ == "__main__":
    main()
    
