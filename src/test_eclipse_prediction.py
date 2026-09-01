"""Earth eclipse timeline regression tests."""

import csv
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

import numpy as np

from constants import MU_EARTH
from eclipse_prediction import (
    EclipseEvent,
    EclipseGeometryOptions,
    EclipsePrediction,
    build_yearly_eclipse_schedule,
    predict_eclipses,
    save_eclipse_prediction_csv,
    save_yearly_eclipse_schedule_csv,
)


class EclipsePredictionTests(unittest.TestCase):

    @staticmethod
    def _fixed_sun(_epoch):
        return np.array([149_597_870.7, 0.0, 0.0], dtype=float)

    @staticmethod
    def _circular_geo_trajectory(step_seconds=300.0):
        radius = 42164.0
        mean_motion = np.sqrt(MU_EARTH / radius**3)
        period = 2.0 * np.pi / mean_motion
        times = np.arange(0.0, period, step_seconds, dtype=float)
        times = np.append(times, period)
        angle = mean_motion * times
        states = np.column_stack(
            (
                radius * np.cos(angle),
                radius * np.sin(angle),
                np.zeros_like(angle),
                -radius * mean_motion * np.sin(angle),
                radius * mean_motion * np.cos(angle),
                np.zeros_like(angle),
            )
        )
        return times, states, period

    def test_geo_day_contains_ordered_penumbra_and_umbra_event(self):
        epoch = datetime(2025, 3, 20, tzinfo=timezone.utc)
        times, states, period = self._circular_geo_trajectory()

        prediction = predict_eclipses(
            times,
            states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
        )

        self.assertEqual(len(prediction.events), 1)
        event = prediction.events[0]
        self.assertLess(event.penumbra_entry_utc, event.umbra_entry_utc)
        self.assertLess(event.umbra_entry_utc, event.umbra_exit_utc)
        self.assertLess(event.umbra_exit_utc, event.penumbra_exit_utc)
        midpoint = event.umbra_entry_utc + (
            event.umbra_exit_utc - event.umbra_entry_utc
        ) / 2
        self.assertAlmostEqual(
            (midpoint - epoch).total_seconds(),
            period / 2.0,
            delta=2.0,
        )
        self.assertEqual(float(np.min(prediction.illumination_fraction)), 0.0)
        self.assertGreater(event.total_duration_seconds, 3000.0)
        self.assertGreater(event.umbra_duration_seconds, 3000.0)

    def test_sample_labels_follow_sun_penumbra_umbra_states(self):
        epoch = datetime(2025, 3, 20, tzinfo=timezone.utc)
        times, states, _period = self._circular_geo_trajectory(60.0)
        prediction = predict_eclipses(
            times,
            states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
        )

        self.assertIn("FULL SUN", prediction.states)
        self.assertIn("PENUMBRA", prediction.states)
        self.assertIn("UMBRA", prediction.states)

    def test_contact_refinement_is_stable_across_output_cadences(self):
        epoch = datetime(2025, 3, 20, tzinfo=timezone.utc)
        coarse_times, coarse_states, _period = self._circular_geo_trajectory(
            300.0
        )
        fine_times, fine_states, _period = self._circular_geo_trajectory(10.0)

        coarse = predict_eclipses(
            coarse_times,
            coarse_states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
        ).events[0]
        fine = predict_eclipses(
            fine_times,
            fine_states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
        ).events[0]

        for coarse_contact, fine_contact in zip(
            (
                coarse.penumbra_entry_utc,
                coarse.umbra_entry_utc,
                coarse.umbra_exit_utc,
                coarse.penumbra_exit_utc,
            ),
            (
                fine.penumbra_entry_utc,
                fine.umbra_entry_utc,
                fine.umbra_exit_utc,
                fine.penumbra_exit_utc,
            ),
        ):
            self.assertLess(
                abs((coarse_contact - fine_contact).total_seconds()),
                0.01,
            )

    def test_moon_apparent_disc_produces_refined_moon_event(self):
        epoch = datetime(2026, 7, 14, 17, 45, tzinfo=timezone.utc)
        times = np.arange(0.0, 601.0, 60.0)
        states = np.tile(
            np.array([42164.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            (len(times), 1),
        )

        def moving_moon(value):
            seconds = (value - epoch).total_seconds()
            return np.array(
                [384400.0, 25.0 * (seconds - 300.0), 0.0],
                dtype=float,
            )

        prediction = predict_eclipses(
            times,
            states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
            shadow_body="MOON",
            moon_position_at_epoch=moving_moon,
        )

        self.assertEqual(len(prediction.events), 1)
        event = prediction.events[0]
        self.assertEqual(event.shadow_body, "MOON")
        self.assertLess(event.penumbra_entry_utc, event.umbra_entry_utc)
        self.assertLess(event.umbra_entry_utc, event.umbra_exit_utc)
        self.assertLess(event.umbra_exit_utc, event.penumbra_exit_utc)
        self.assertEqual(float(np.min(prediction.illumination_fraction)), 0.0)

    def test_csv_export_writes_timeline_and_refined_events(self):
        epoch = datetime(2025, 3, 20, tzinfo=timezone.utc)
        times, states, _period = self._circular_geo_trajectory(300.0)
        prediction = predict_eclipses(
            times,
            states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
        )

        with tempfile.TemporaryDirectory() as directory:
            timeline_path, events_path = save_eclipse_prediction_csv(
                prediction,
                epoch,
                Path(directory) / "eclipse_timeline.csv",
            )

            with timeline_path.open(newline="", encoding="utf-8") as handle:
                timeline_rows = list(csv.DictReader(handle))
            with events_path.open(newline="", encoding="utf-8") as handle:
                event_rows = list(csv.DictReader(handle))

        self.assertEqual(len(timeline_rows), len(times))
        self.assertEqual(timeline_rows[0]["UTC"], "20/03/2025 00:00:00.000")
        self.assertEqual(timeline_rows[0]["EclipseState"], prediction.states[0])
        self.assertEqual(len(event_rows), 1)
        self.assertEqual(event_rows[0]["Event"], "1")
        self.assertEqual(event_rows[0]["ShadowBody"], "EARTH")
        self.assertRegex(
            event_rows[0]["PenumbraEntryUTC"],
            r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}\.\d{3}$",
        )
        self.assertRegex(
            event_rows[0]["PenumbraExitUTC"],
            r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}\.\d{3}$",
        )

    def test_year_schedule_marks_empty_days_skipped_and_exports_csv(self):
        epoch = datetime(2025, 1, 1, tzinfo=timezone.utc)
        event = EclipseEvent(
            penumbra_entry_utc=datetime(
                2025, 3, 20, 20, 0, tzinfo=timezone.utc
            ),
            umbra_entry_utc=datetime(
                2025, 3, 20, 20, 2, tzinfo=timezone.utc
            ),
            umbra_exit_utc=datetime(
                2025, 3, 20, 21, 0, tzinfo=timezone.utc
            ),
            penumbra_exit_utc=datetime(
                2025, 3, 20, 21, 2, tzinfo=timezone.utc
            ),
        )
        prediction = EclipsePrediction(
            elapsed_seconds=np.array([0.0, 60.0]),
            illumination_fraction=np.ones(2),
            states=("FULL SUN", "FULL SUN"),
            events=(event,),
            source_step_seconds=60.0,
        )

        schedule = build_yearly_eclipse_schedule(prediction, 2025)

        self.assertEqual(len(schedule.rows), 365)
        self.assertEqual(schedule.event_count, 1)
        self.assertEqual(schedule.skipped_day_count, 364)
        eclipse_row = next(
            row for row in schedule.rows if row.status == "ECLIPSE"
        )
        self.assertEqual(eclipse_row.date_utc.isoformat(), "2025-03-20")

        with tempfile.TemporaryDirectory() as directory:
            output_path = save_yearly_eclipse_schedule_csv(
                schedule,
                Path(directory) / "year_schedule.csv",
            )
            with output_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 365)
        self.assertEqual(rows[0]["Status"], "SKIPPED")
        exported_event = next(row for row in rows if row["Status"] == "ECLIPSE")
        self.assertEqual(exported_event["DateUTC"], "20/03/2025")
        self.assertEqual(exported_event["ShadowBody"], "EARTH")
        self.assertEqual(exported_event["SearchStepSeconds"], "60.000000")


    def test_contacts_report_how_certain_they_are(self):
        """A deep shadow crossing is far better conditioned than a graze."""

        epoch = datetime(2025, 3, 20, tzinfo=timezone.utc)
        times, states, _period = self._circular_geo_trajectory()

        prediction = predict_eclipses(
            times,
            states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
        )
        event = prediction.events[0]

        self.assertIsNotNone(event.penumbra_entry_sensitivity)
        self.assertGreater(event.penumbra_entry_sensitivity, 0.0)
        self.assertEqual(event.conditioning, "SHARP")
        self.assertFalse(event.is_grazing)
        self.assertEqual(
            event.worst_contact_sensitivity,
            max(
                event.penumbra_entry_sensitivity,
                event.umbra_entry_sensitivity,
                event.umbra_exit_sensitivity,
                event.penumbra_exit_sensitivity,
            ),
        )

    def test_conditioning_labels_follow_the_measured_sensitivity(self):
        thresholds = (
            (0.1, "SHARP"),
            (1.0, "SOFT"),
            (9.0, "GRAZING"),
            (None, "UNKNOWN"),
        )
        for sensitivity, expected in thresholds:
            event = EclipseEvent(
                penumbra_entry_utc=None,
                umbra_entry_utc=None,
                umbra_exit_utc=None,
                penumbra_exit_utc=None,
                penumbra_entry_sensitivity=sensitivity,
            )
            self.assertEqual(event.conditioning, expected)

    def test_geometry_refinements_are_off_unless_requested(self):
        """The defaults must reproduce the bundled reference convention."""

        default = EclipseGeometryOptions()
        self.assertFalse(default.oblate_earth_shadow)
        self.assertFalse(default.light_time_moon)

        epoch = datetime(2025, 3, 20, tzinfo=timezone.utc)
        times, states, _period = self._circular_geo_trajectory()

        spherical = predict_eclipses(
            times,
            states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
        ).events[0]
        oblate = predict_eclipses(
            times,
            states,
            epoch,
            sun_position_at_epoch=self._fixed_sun,
            geometry=EclipseGeometryOptions(oblate_earth_shadow=True),
        ).events[0]

        # The Sun sits in the equatorial plane here, so the satellite crosses
        # the widest part of the shadow and flattening barely shows.
        self.assertLess(
            abs(
                (
                    oblate.penumbra_entry_utc - spherical.penumbra_entry_utc
                ).total_seconds()
            ),
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
