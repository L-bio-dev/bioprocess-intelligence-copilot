"""Evaluate fixed detectors on paired, reproducible synthetic scenarios."""

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from src.anomaly_detection import ROBUST_Z_THRESHOLD
from src.generate_synthetic_data import (
    NUMBER_OF_REFERENCE_BATCHES,
    create_base_profiles,
    generate_batch,
)
from src.isolation_forest_detection import (
    RANDOM_SEED as ISOLATION_FOREST_SEED,
    REFERENCE_SCORE_QUANTILE,
)
from src.model_evaluation import evaluate_models


DEFAULT_SEEDS = (1001, 1002, 1003, 1004, 1005)
SCENARIOS = (
    "no_injected_anomalies",
    "clear_deviations",
    "mild_deviations",
    "gradual_feed_drift",
    "higher_variability_no_anomalies",
    "higher_variability_clear_deviations",
)
COUNT_COLUMNS = (
    "true_positives", "false_positives", "false_negatives", "true_negatives"
)
TRUTH_COLUMNS = (
    "event_id", "batch_id", "start_time_h", "end_time_h", "affected_variables"
)


def create_scenario(seed: int, scenario: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reuse the demo generator, then apply documented synthetic changes."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    rng = np.random.default_rng(seed)
    batches = [
        generate_batch(f"REF_{number:03d}", "reference", rng)
        for number in range(1, NUMBER_OF_REFERENCE_BATCHES + 1)
    ]
    batches.append(generate_batch("ASSESS_001", "assessment", rng))
    data = pd.concat(batches, ignore_index=True)

    # Paired scenarios reuse the same draws for each seed. Variability is
    # increased in BOTH reference and assessment batches before injection.
    if scenario.startswith("higher_variability"):
        base = create_base_profiles(data["elapsed_time_h"].to_numpy())
        for variable, profile in base.items():
            data[variable] = profile + 2.0 * (data[variable] - profile)
        data["ph"] = data["ph"].clip(0, 14)
        data["dissolved_oxygen_pct"] = data["dissolved_oxygen_pct"].clip(0, 100)
        for variable in ("agitation_rpm", "feed_rate_ml_h"):
            data[variable] = data[variable].clip(lower=0)

    assessment = data["batch_role"].eq("assessment")
    time = data["elapsed_time_h"]
    events = []

    def record(start: int, end: int, variables: str) -> None:
        events.append({
            "event_id": f"EVENT_{len(events) + 1:03d}",
            "batch_id": "ASSESS_001",
            "start_time_h": start,
            "end_time_h": end,
            "affected_variables": variables,
        })

    if scenario in (
        "clear_deviations", "mild_deviations",
        "higher_variability_clear_deviations",
    ):
        mild = scenario == "mild_deviations"
        feed_mask = assessment & time.between(120, 144)
        oxygen_mask = assessment & time.between(170, 190)
        data.loc[feed_mask, "feed_rate_ml_h"] *= 0.90 if mild else 0.65
        data.loc[oxygen_mask, "dissolved_oxygen_pct"] -= 3.0 if mild else 12.0
        data.loc[oxygen_mask, "agitation_rpm"] += 10.0 if mild else 45.0
        record(120, 144, "feed_rate_ml_h")
        record(170, 190, "dissolved_oxygen_pct; agitation_rpm")
    elif scenario == "gradual_feed_drift":
        mask = assessment & time.between(120, 180)
        reductions = 0.35 * np.arange(1, int(mask.sum()) + 1) / int(mask.sum())
        data.loc[mask, "feed_rate_ml_h"] *= 1.0 - reductions
        record(120, 180, "feed_rate_ml_h")

    data["dissolved_oxygen_pct"] = data["dissolved_oxygen_pct"].clip(lower=0)
    truth = pd.DataFrame(events, columns=TRUTH_COLUMNS)
    return data, truth


def rates_from_counts(counts: dict) -> dict[str, float]:
    """Return ratios; undefined metrics are NaN, exported as blank cells."""
    tp, fp, fn, tn = (int(counts[column]) for column in COUNT_COLUMNS)
    positives = tp + fn
    predictions = tp + fp
    negatives = fp + tn
    return {
        "precision": tp / predictions if predictions else np.nan,
        "recall": tp / positives if positives else np.nan,
        # We do not report anomaly F1 in a scenario with no positive labels.
        "f1_score": 2 * tp / (2 * tp + fp + fn) if positives else np.nan,
        "false_positive_rate": fp / negatives if negatives else np.nan,
    }


def summarize_runs(runs: pd.DataFrame) -> pd.DataFrame:
    """Pool counts within each scenario/model and retain between-run ranges."""
    records = []
    for (scenario, model), group in runs.groupby(["scenario", "model"], sort=False):
        counts = {column: int(group[column].sum()) for column in COUNT_COLUMNS}
        records.append({
            "scenario": scenario,
            "model": model,
            "runs": len(group),
            **counts,
            **rates_from_counts(counts),
            "false_positives_per_batch_mean": float(group["false_positives"].mean()),
            "false_positives_per_batch_min": int(group["false_positives"].min()),
            "false_positives_per_batch_max": int(group["false_positives"].max()),
            "batches_with_false_alarms_fraction": float(group["false_positives"].gt(0).mean()),
            "recall_min": float(group["recall"].min()),
            "recall_max": float(group["recall"].max()),
        })
    return pd.DataFrame(records)


def run_evaluation(
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    scenarios: tuple[str, ...] = SCENARIOS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run unchanged production detectors; labels are used only for scoring."""
    if not seeds or len(set(seeds)) != len(seeds) or any(seed < 0 for seed in seeds):
        raise ValueError("Use at least one unique, non-negative seed.")
    if not scenarios or len(set(scenarios)) != len(scenarios):
        raise ValueError("Use at least one unique scenario.")
    if any(scenario not in SCENARIOS for scenario in scenarios):
        raise ValueError("Unknown scenario.")
    records = []
    for scenario in scenarios:
        for seed in seeds:
            data, truth = create_scenario(seed, scenario)
            evaluation, expected, _, _ = evaluate_models(data, truth)
            for result in evaluation.to_dict("records"):
                counts = {column: int(result[column]) for column in COUNT_COLUMNS}
                if sum(counts.values()) != 241:
                    raise ValueError("Evaluation counts must cover all 241 time points.")
                if counts["true_positives"] + counts["false_negatives"] != len(expected):
                    raise ValueError("Positive counts do not match the injected labels.")
                records.append({
                    "scenario": scenario,
                    "seed": seed,
                    "model": result["model"],
                    **counts,
                    **rates_from_counts(counts),
                })
            print(f"Completed {scenario}, seed {seed}", flush=True)
    runs = pd.DataFrame(records)
    return runs, summarize_runs(runs)


def main() -> None:
    """Write a separate benchmark without overwriting the original demo."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "processed" / "scenario_evaluation",
    )
    args = parser.parse_args()
    runs, summary = run_evaluation(tuple(args.seeds))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.output_dir / "runs.csv", index=False)
    summary.to_csv(args.output_dir / "summary.csv", index=False)
    manifest = {
        "seeds": args.seeds,
        "scenarios": list(SCENARIOS),
        "reference_batches_per_run": NUMBER_OF_REFERENCE_BATCHES,
        "assessment_batches_per_run": 1,
        "time_grid": "0 to 240 hours inclusive, one-hour intervals",
        "robust_z_threshold": ROBUST_Z_THRESHOLD,
        "reference_score_quantile": REFERENCE_SCORE_QUANTILE,
        "isolation_forest_seed": ISOLATION_FOREST_SEED,
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ("numpy", "pandas", "scikit-learn")},
        "metric_units": "Ratios from 0 to 1; blank CSV cells mean undefined.",
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("\nPooled metrics (ratios from 0 to 1; NaN means undefined):")
    print(summary[[
        "scenario", "model", "precision", "recall", "f1_score",
        "false_positive_rate", "false_positives_per_batch_mean",
    ]].round(3).to_string(index=False))
    print(f"\nCreated runs.csv, summary.csv and manifest.json in {args.output_dir}")


if __name__ == "__main__":
    main()
