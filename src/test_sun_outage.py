"""Sun-transit geometry, contact refinement and export regressions."""

from datetime import date
import csv
from pathlib import Path
import tempfile
import unittest

from sun_outage import (
    SunOutageStation,
    half_power_beamwidth_deg,
    predict_sun_outages,
    save_sun_outage_csv,
)


class SunOutageTests(unittest.TestCase):

    def setUp(self):
        self.station = SunOutageStation(
            "SYNTHETIC-TEST",
            "SYNTHETIC TEST STATION",
            40.4,
            49.9,
            0.0,
        )

    def test_itu_half_power_beamwidth_equation(self):
        expected = 70.0 * 299_792_458.0 / (11.0e9 * 3.7)
        self.assertAlmostEqual(half_power_beamwidth_deg(11.0, 3.7), expected, 12)

    def test_refined_contacts_enclose_peak(self):
        prediction = predict_sun_outages(
            year=2026,
            station=self.station,
            satellite_longitude_deg=46.0,
            frequency_ghz=11.0,
            antenna_diameter_m=3.7,
            candidate_dates=(date(2026, 3, 3), date(2026, 3, 4), date(2026, 3, 5)),
        )
        self.assertEqual(len(prediction.events), 3)
        closest = min(prediction.events, key=lambda event: event.minimum_separation_deg)
        self.assertEqual(closest.peak_utc.date(), date(2026, 3, 4))
        for event in prediction.events:
            self.assertLess(event.start_utc, event.peak_utc)
            self.assertLess(event.peak_utc, event.end_utc)
            self.assertLessEqual(event.minimum_separation_deg, event.threshold_deg)
            self.assertGreater(event.duration_seconds, 0.0)
            self.assertLess(event.duration_seconds, 3600.0)

    def test_csv_contains_only_prediction_fields(self):
        prediction = predict_sun_outages(
            year=2026,
            station=self.station,
            satellite_longitude_deg=46.0,
            frequency_ghz=11.0,
            antenna_diameter_m=3.7,
            candidate_dates=(date(2026, 3, 4),),
        )
        with tempfile.TemporaryDirectory(prefix="opa-sun-outage-") as directory:
            path = save_sun_outage_csv(
                prediction,
                Path(directory) / "schedule.csv",
            )
            with path.open(newline="", encoding="utf-8-sig") as stream:
                rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Station ID"], "SYNTHETIC-TEST")
        self.assertEqual(rows[0]["Peak UTC"][:10], "04/03/2026")
        self.assertIn("ITU-R S.1525-1", rows[0]["Method"])


if __name__ == "__main__":
    unittest.main()
