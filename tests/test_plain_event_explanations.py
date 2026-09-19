"""Check the numerical meaning of the plain-language examples."""

import unittest

import pandas as pd

from src.event_explanations import explain_event


def example(variable, measured, reference, z_score=-12.87):
    event = pd.Series({
        "start_time_h": 136, "end_time_h": 136,
        "flagged_time_points": 1, "ml_corroborated_time_points": 1,
    })
    scores = pd.DataFrame([{
        "elapsed_time_h": 136, "variable": variable,
        "robust_z_score": z_score, "is_anomaly": True,
        "assessment_value": measured, "reference_median": reference,
    }])
    return explain_event(event, scores)


class PlainExplanationTests(unittest.TestCase):
    def test_feed_example_reports_relative_change_with_units(self):
        text = example("feed_rate_ml_h", 15.96, 23.69)["plain_notes"][0]
        self.assertIn("15.96 mL/h", text)
        self.assertIn("23.69 mL/h", text)
        self.assertIn("33% lower", text)

    def test_zero_reference_does_not_divide_by_zero(self):
        text = example("feed_rate_ml_h", 1, 0, 10)["plain_notes"][0]
        self.assertIn("percentage comparison is not defined", text)

    def test_no_relative_percent_for_ph_or_celsius(self):
        for variable in ["ph", "temperature_c"]:
            with self.subTest(variable=variable):
                text = example(variable, 6.5, 7)["plain_notes"][0]
                self.assertNotIn("%", text)

    def test_agitation_increase_and_agreement_are_distinct(self):
        result = example("agitation_rpm", 248.8, 213, 15.09)
        self.assertIn("17% higher", result["plain_notes"][0])
        self.assertIn("1 of the 1 time point", result["plain_agreement"])
        self.assertIn("does not establish the cause", result["plain_agreement"])


if __name__ == "__main__":
    unittest.main()
