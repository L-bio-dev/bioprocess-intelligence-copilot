"""Check scenario labels, paired data and benchmark metric conventions."""

import unittest

import numpy as np
import pandas as pd

from src.data_validation import validate_dataset
from src.generate_synthetic_data import create_base_profiles
from src.model_evaluation import create_expected_anomaly_hours
from src.scenario_evaluation import (
    SCENARIOS,
    create_scenario,
    rates_from_counts,
    run_evaluation,
    summarize_runs,
)


class TestScenarioEvaluation(unittest.TestCase):
    def test_all_scenarios_satisfy_contract_and_have_expected_labels(self):
        expected_sizes = (0, 46, 46, 61, 0, 46)
        for scenario, expected_size in zip(SCENARIOS, expected_sizes):
            with self.subTest(scenario=scenario):
                data, truth = create_scenario(1001, scenario)
                validation = validate_dataset(data)
                self.assertTrue(validation.is_valid, validation.errors)
                self.assertEqual(len(data), 21 * 241)
                self.assertEqual(len(create_expected_anomaly_hours(truth)), expected_size)

    def test_fixed_seed_reproduces_data_and_other_seed_changes_it(self):
        first, truth = create_scenario(1001, "clear_deviations")
        repeat, repeated_truth = create_scenario(1001, "clear_deviations")
        other, _ = create_scenario(1002, "clear_deviations")
        pd.testing.assert_frame_equal(first, repeat)
        pd.testing.assert_frame_equal(truth, repeated_truth)
        self.assertFalse(first.equals(other))

    def test_injections_leave_references_and_unlabelled_hours_unchanged(self):
        normal, _ = create_scenario(1001, "no_injected_anomalies")
        for scenario in ("clear_deviations", "mild_deviations", "gradual_feed_drift"):
            with self.subTest(scenario=scenario):
                changed, truth = create_scenario(1001, scenario)
                expected = create_expected_anomaly_hours(truth)
                outside = normal.batch_role.eq("reference") | ~normal.elapsed_time_h.isin(expected)
                pd.testing.assert_frame_equal(normal.loc[outside], changed.loc[outside])
                numeric_columns = list(create_base_profiles(np.array([0])))
                actually_changed = (normal[numeric_columns] != changed[numeric_columns]).any(axis=1)
                self.assertEqual(set(changed.loc[actually_changed, "elapsed_time_h"]), expected)

    def test_mild_changes_have_specified_magnitude(self):
        normal, _ = create_scenario(1001, "no_injected_anomalies")
        mild, _ = create_scenario(1001, "mild_deviations")
        normal = normal[normal.batch_role.eq("assessment")].set_index("elapsed_time_h")
        mild = mild[mild.batch_role.eq("assessment")].set_index("elapsed_time_h")
        np.testing.assert_allclose(mild.loc[120:144, "feed_rate_ml_h"], normal.loc[120:144, "feed_rate_ml_h"] * .9)
        np.testing.assert_allclose(mild.loc[170:190, "dissolved_oxygen_pct"], normal.loc[170:190, "dissolved_oxygen_pct"] - 3)
        np.testing.assert_allclose(mild.loc[170:190, "agitation_rpm"], normal.loc[170:190, "agitation_rpm"] + 10)

    def test_drift_is_nonzero_at_start_increases_and_ends_at_35_percent(self):
        normal, _ = create_scenario(1001, "no_injected_anomalies")
        drift, _ = create_scenario(1001, "gradual_feed_drift")
        mask = normal.batch_role.eq("assessment") & normal.elapsed_time_h.between(120, 180)
        reductions = 1 - drift.loc[mask, "feed_rate_ml_h"] / normal.loc[mask, "feed_rate_ml_h"]
        self.assertGreater(reductions.iloc[0], 0)
        self.assertTrue((np.diff(reductions) > 0).all())
        self.assertAlmostEqual(reductions.iloc[-1], .35)

    def test_variability_increases_in_both_roles(self):
        normal, _ = create_scenario(1001, "no_injected_anomalies")
        wider, truth = create_scenario(1001, "higher_variability_no_anomalies")
        self.assertTrue(truth.empty)
        base = create_base_profiles(normal.elapsed_time_h.to_numpy())
        for role in ("reference", "assessment"):
            mask = normal.batch_role.eq(role).to_numpy()
            for variable in ("ph", "temperature_c", "agitation_rpm"):
                np.testing.assert_allclose(
                    wider.loc[mask, variable] - base[variable][mask],
                    2 * (normal.loc[mask, variable] - base[variable][mask]),
                )

    def test_high_variability_injection_preserves_paired_references(self):
        normal, _ = create_scenario(1001, "higher_variability_no_anomalies")
        changed, _ = create_scenario(1001, "higher_variability_clear_deviations")
        refs = normal.batch_role.eq("reference")
        pd.testing.assert_frame_equal(normal.loc[refs], changed.loc[refs])
        mask = normal.batch_role.eq("assessment") & normal.elapsed_time_h.between(120, 144)
        np.testing.assert_allclose(changed.loc[mask, "feed_rate_ml_h"], normal.loc[mask, "feed_rate_ml_h"] * .65)

    def test_no_anomaly_rates_do_not_report_undefined_recall_as_zero(self):
        rates = rates_from_counts(dict(true_positives=0, false_positives=2, false_negatives=0, true_negatives=239))
        self.assertTrue(np.isnan(rates["recall"]))
        self.assertTrue(np.isnan(rates["f1_score"]))
        self.assertEqual(rates["precision"], 0)
        self.assertAlmostEqual(rates["false_positive_rate"], 2 / 241)
        no_flags = rates_from_counts(dict(true_positives=0, false_positives=0, false_negatives=0, true_negatives=241))
        self.assertTrue(np.isnan(no_flags["precision"]))
        self.assertEqual(no_flags["false_positive_rate"], 0)

    def test_summary_pools_counts_instead_of_averaging_precision(self):
        records = []
        for seed, tp, fp, fn, tn in ((1, 1, 0, 9, 90), (2, 9, 9, 1, 81)):
            counts = dict(true_positives=tp, false_positives=fp, false_negatives=fn, true_negatives=tn)
            records.append(dict(scenario="example", model="example", seed=seed, **counts, **rates_from_counts(counts)))
        summary = summarize_runs(pd.DataFrame(records)).iloc[0]
        self.assertAlmostEqual(summary.precision, 10 / 19)
        self.assertAlmostEqual(summary.recall, .5)
        self.assertAlmostEqual(summary.false_positive_rate, 9 / 180)
        self.assertAlmostEqual(summary.batches_with_false_alarms_fraction, .5)
        self.assertEqual(summary.false_positives_per_batch_min, 0)
        self.assertEqual(summary.false_positives_per_batch_max, 9)

    def test_invalid_seeds_and_scenarios_are_rejected_before_evaluation(self):
        for seeds in ((), (1, 1), (-1,)):
            with self.assertRaises(ValueError):
                run_evaluation(seeds)
        for scenarios in ((), ("unknown",), (SCENARIOS[0], SCENARIOS[0])):
            with self.assertRaises(ValueError):
                run_evaluation((1001,), scenarios)

    def test_actual_detectors_cover_every_time_point_on_clean_batch(self):
        runs, summary = run_evaluation((1001,), ("no_injected_anomalies",))
        self.assertEqual(set(runs.model), {"Robust Z-score", "Isolation Forest"})
        self.assertEqual(len(summary), 2)
        for row in runs.itertuples(index=False):
            self.assertEqual(row.true_positives + row.false_negatives, 0)
            self.assertEqual(row.false_positives + row.true_negatives, 241)
            self.assertTrue(np.isnan(row.recall))


if __name__ == "__main__":
    unittest.main()
