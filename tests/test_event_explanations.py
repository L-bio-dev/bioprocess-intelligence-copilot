"""Check that event explanations stay faithful to numerical evidence."""

import unittest

import pandas as pd

from src.event_explanations import explain_event


def make_event(start=0.5, end=1.0, count=2, corroborated=1):
    return pd.Series({
        "event_id": "EVENT_001",
        "start_time_h": start,
        "end_time_h": end,
        "flagged_time_points": count,
        "ml_corroborated_time_points": corroborated,
    })


def make_scores(z_values, times=None, variable="ph"):
    times = times if times is not None else [0.5, 1.0]
    return pd.DataFrame({
        "elapsed_time_h": times,
        "variable": variable,
        "robust_z_score": z_values,
        "is_anomaly": [abs(value) >= 5 for value in z_values],
        "assessment_value": [7 + value * 0.01 for value in z_values],
        "reference_median": 7.0,
    })


class EventExplanationTests(unittest.TestCase):
    def test_negative_deviations_use_absolute_peak(self):
        result = explain_event(make_event(), make_scores([-6, -9]))
        note = result["variable_notes"][0]
        self.assertIn("below the reference median", note)
        self.assertIn("9.00 at 1 h", note)
        self.assertIn("measured value: 6.91", note)
        self.assertIn("reference median: 7", note)

    def test_positive_and_mixed_directions(self):
        for values, direction in [
            ([6, 8], "above the reference median"),
            ([-6, 8], "on both sides of the reference median"),
        ]:
            with self.subTest(values=values):
                result = explain_event(make_event(), make_scores(values))
                self.assertIn(direction, result["variable_notes"][0])

    def test_non_flagged_and_outside_event_scores_do_not_enter_explanation(self):
        scores = make_scores([100, -6, 1, -8, -100],
                             times=[0, 0.5, 0.75, 1, 1.5])
        result = explain_event(make_event(), scores)
        self.assertIn("2 flagged observations", result["variable_notes"][0])
        self.assertIn("below the reference median", result["variable_notes"][0])
        self.assertIn("8.00 at 1 h", result["variable_notes"][0])

    def test_fractional_single_point_is_not_reported_as_a_duration(self):
        result = explain_event(make_event(end=0.5, count=1, corroborated=0),
                               make_scores([-6], times=[0.5]))
        self.assertTrue(result["overview"].startswith("At 0.5 h"))
        self.assertIn("1 observation in", result["overview"])
        self.assertIn("0 of the 1 flagged time point (0.0%)", result["agreement"])

    def test_corroboration_uses_time_points_not_variable_flag_count(self):
        scores = pd.concat([
            make_scores([-6, -8]),
            make_scores([6, 7], variable="agitation_rpm"),
        ], ignore_index=True)
        result = explain_event(make_event(), scores)
        self.assertEqual(len(result["variable_notes"]), 2)
        self.assertIn("1 of the 2 flagged time points (50.0%)", result["agreement"])
        self.assertIn("flagged 2 observations", result["overview"])

    def test_complete_corroboration_does_not_claim_confirmed_cause(self):
        result = explain_event(make_event(corroborated=2), make_scores([6, 8]))
        self.assertIn("(100.0%)", result["agreement"])
        self.assertIn("not a probability", result["agreement"])
        self.assertIn("do not establish a root cause", result["limitation"])

    def test_inconsistent_counts_and_missing_evidence_are_rejected(self):
        for event in [make_event(count=0), make_event(corroborated=3)]:
            with self.subTest(event=event.to_dict()):
                with self.assertRaises(ValueError):
                    explain_event(event, make_scores([6, 8]))
        with self.assertRaises(ValueError):
            explain_event(make_event(), make_scores([1, 2]))


if __name__ == "__main__":
    unittest.main()
