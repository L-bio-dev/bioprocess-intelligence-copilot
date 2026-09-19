"""Regression checks for bounded uploads and event timing."""

from io import BytesIO
import unittest
from unittest.mock import patch

import pandas as pd

from src.input_limits import (
    MAX_DATA_COLUMNS,
    MAX_DATA_ROWS,
    MAX_REFERENCE_BATCHES,
    MAX_TIME_POINTS_PER_BATCH,
    UploadLimitError,
    read_uploaded_csv,
    resource_limit_errors,
)
from src.event_summary import summarize_process_events


class UploadLimitTests(unittest.TestCase):
    def test_row_boundary(self):
        data = pd.DataFrame({"value": range(MAX_DATA_ROWS + 1)})
        self.assertEqual(resource_limit_errors(data.iloc[:-1]), [])
        self.assertTrue(resource_limit_errors(data))

    def test_column_boundary(self):
        data = pd.DataFrame([[0] * (MAX_DATA_COLUMNS + 1)])
        self.assertEqual(resource_limit_errors(data.iloc[:, :-1]), [])
        self.assertTrue(resource_limit_errors(data))

    def test_reference_batch_boundary(self):
        data = pd.DataFrame({
            "batch_id": [f"REF_{n}" for n in range(MAX_REFERENCE_BATCHES + 1)],
            "batch_role": "reference",
        })
        self.assertEqual(resource_limit_errors(data.iloc[:-1]), [])
        self.assertTrue(resource_limit_errors(data))

    def test_observations_per_batch_boundary(self):
        data = pd.DataFrame({
            "batch_id": ["REF_001"] * (MAX_TIME_POINTS_PER_BATCH + 1),
        })
        self.assertEqual(resource_limit_errors(data.iloc[:-1]), [])
        self.assertTrue(resource_limit_errors(data))

    def test_demo_size_is_allowed(self):
        data = pd.DataFrame({
            "batch_id": [f"B{batch}" for batch in range(21) for _ in range(241)],
            "batch_role": [
                "assessment" if batch == 20 else "reference"
                for batch in range(21) for _ in range(241)
            ],
        })
        self.assertEqual(resource_limit_errors(data), [])

    def test_csv_is_not_silently_truncated(self):
        content = b"value\n" + b"1\n" * (MAX_DATA_ROWS + 1)
        with self.assertRaises(UploadLimitError):
            read_uploaded_csv(BytesIO(content))
        allowed = b"value\n" + b"1\n" * MAX_DATA_ROWS
        self.assertEqual(len(read_uploaded_csv(BytesIO(allowed))), MAX_DATA_ROWS)

    def test_byte_limit_and_bounded_read(self):
        class TrackedFile(BytesIO):
            def read(self, size=-1):
                self.requested_size = size
                return super().read(size)

        uploaded = TrackedFile(b"x" * 1000)
        with patch("src.input_limits.MAX_UPLOAD_BYTES", 64):
            with self.assertRaises(UploadLimitError):
                read_uploaded_csv(uploaded)
        self.assertEqual(uploaded.requested_size, 65)

    def test_reader_rewinds_for_repeated_analysis(self):
        uploaded = BytesIO(b"value\n1\n2\n")
        first = read_uploaded_csv(uploaded)
        pd.testing.assert_frame_equal(first, read_uploaded_csv(uploaded))

    def test_empty_csv_is_rejected(self):
        with self.assertRaises(pd.errors.EmptyDataError):
            read_uploaded_csv(BytesIO(b""))


def consensus(times, robust, ml=None):
    return pd.DataFrame({
        "elapsed_time_h": times,
        "robust_anomaly": robust,
        "ml_anomaly": ml if ml is not None else robust,
        "flagged_variables": ["ph" if flag else "" for flag in robust],
        "maximum_robust_score": [6.0 if flag else 0.0 for flag in robust],
    })


class EventTimingTests(unittest.TestCase):
    def test_fractional_times_preserved_and_corroboration_correct(self):
        data = consensus([0.0, 0.5, 1.0, 1.5],
                         [False, True, True, False],
                         [False, True, False, False])
        event = summarize_process_events(data).iloc[0]
        self.assertEqual(event["start_time_h"], 0.5)
        self.assertEqual(event["end_time_h"], 1.0)
        self.assertEqual(event["flagged_time_points"], 2)
        self.assertEqual(event["ml_corroboration_pct"], 50.0)

    def test_single_fractional_flag_does_not_divide_by_zero(self):
        event = summarize_process_events(consensus([0.5], [True])).iloc[0]
        self.assertEqual(event["start_time_h"], 0.5)
        self.assertEqual(event["end_time_h"], 0.5)
        self.assertEqual(event["flagged_time_points"], 1)

    def test_normal_and_ml_only_points_separate_events(self):
        events = summarize_process_events(consensus(
            [0.0, 0.5, 1.0], [True, False, True], [True, True, True]
        ))
        self.assertEqual(len(events), 2)

    def test_unordered_rows_are_processed_chronologically(self):
        events = summarize_process_events(consensus(
            [1.0, 0.0, 0.5], [True, False, True]
        ))
        self.assertEqual(len(events), 1)
        self.assertEqual(events.iloc[0]["start_time_h"], 0.5)

    def test_sparse_grid_uses_observation_adjacency(self):
        event = summarize_process_events(consensus([0.5, 4.5], [True, True]))
        self.assertEqual(len(event), 1)
        self.assertEqual(event.iloc[0]["flagged_time_points"], 2)

    def test_empty_and_normal_results_keep_export_headers(self):
        for data in [pd.DataFrame(), consensus([0.0, 0.5], [False, False])]:
            events = summarize_process_events(data)
            self.assertTrue(events.empty)
            self.assertIn("event_id", events.to_csv(index=False))

    def test_hourly_demo_intervals_remain_unchanged(self):
        times = list(range(241))
        robust = [120 <= time <= 144 or 170 <= time <= 190 for time in times]
        events = summarize_process_events(consensus(times, robust))
        self.assertEqual(events["start_time_h"].tolist(), [120.0, 170.0])
        self.assertEqual(events["end_time_h"].tolist(), [144.0, 190.0])
        self.assertEqual(events["flagged_time_points"].tolist(), [25, 21])


if __name__ == "__main__":
    unittest.main()
