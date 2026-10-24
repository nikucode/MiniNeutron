"""Controlled temporal-association cases for the truth/DAQ comparison."""

import unittest

import pandas as pd

from analysis.compare_truth_reco import compare_events


def truth(*pairs):
    return pd.DataFrame([
        {"event": event, "pulse_time_s": time,
         "total_edep_MeV": 0.5, "response_amplitude_V": 0.5}
        for event, time in pairs
    ], columns=["event", "pulse_time_s", "total_edep_MeV",
                "response_amplitude_V"])


def reco(*windows):
    return pd.DataFrame([
        {"event_id": event, "trigger_time_s": start,
         "peak_time_s": start, "peak_voltage_V": 1.0,
         "end_time_s": end, "duration_s": end - start}
        for event, start, end in windows
    ], columns=["event_id", "trigger_time_s", "peak_time_s",
                "peak_voltage_V", "end_time_s", "duration_s"])


class TestTemporalAssociation(unittest.TestCase):
    def test_individual_merged_missed_and_unmatched(self):
        t, r = compare_events(
            truth((1, 1.000), (2, 2.000), (3, 2.010), (4, 4.000)),
            reco((10, 1.002, 1.020), (11, 2.002, 2.020),
                 (12, 3.000, 3.020)),
        )
        self.assertEqual(t.set_index("event")["status"].to_dict(), {
            1: "individual", 2: "merged", 3: "merged", 4: "missed"
        })
        self.assertEqual(r["n_truth_matches"].tolist(), [1, 2, 0])
        self.assertEqual(r["matched_truth_events"].tolist(), ["1", "2;3", ""])

    def test_overlap_is_ambiguous_instead_of_last_reco_wins(self):
        t, r = compare_events(
            truth((7, 1.003)),
            reco((10, 1.002, 1.004), (11, 1.006, 1.010)),
        )
        self.assertEqual(t.loc[0, "status"], "ambiguous")
        self.assertTrue(pd.isna(t.loc[0, "reco_event_id"]))
        self.assertTrue(pd.isna(t.loc[0, "n_truth_in_reco"]))
        self.assertEqual(t.loc[0, "candidate_reco_event_ids"], "10;11")
        self.assertEqual(r["n_ambiguous_truth_matches"].tolist(), [1, 1])

    def test_empty_reconstruction_keeps_output_schema(self):
        t, r = compare_events(truth((1, 1.0)), reco())
        self.assertEqual(t.loc[0, "status"], "missed")
        self.assertTrue(r.empty)
        self.assertIn("n_truth_matches", r.columns)

    def test_negative_window_and_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "pre_window"):
            compare_events(truth((1, 1.0)), reco(), -0.001)
        with self.assertRaisesRegex(ValueError, "unique integers"):
            compare_events(truth((1, 1.0), (1, 2.0)), reco())


if __name__ == "__main__":
    unittest.main()
