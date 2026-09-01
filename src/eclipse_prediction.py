"""Earth/Moon eclipse event prediction along a propagated J2000 trajectory."""

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from constants import R_EARTH, R_MOON
from moon import (
    get_moon_position,
    get_moon_position_apparent,
    get_sun_position,
)
from solar_radiation_pressure import (
    occulting_body_geometry,
    occulting_body_sunlight_fraction,
    solar_occultation_geometry,
    sunlight_fraction,
)
from time_utils import format_csv_utc, utc_to_et


ECLIPSE_CONTACT_TOLERANCE_SECONDS = 1.0e-3

# How far a contact time moves when the geometry is off by one millidegree.
# A contact is only as certain as the rate at which the limb margin crosses
# zero: deep in the shadow the crossing is steep and the time is sharp, while
# at the first and last eclipse of a season the satellite skims the limb, the
# margin flattens out, and the same geometric error moves the contact by far
# longer. Reporting this turns an unexplained large residual into a stated
# confidence.
CONTACT_REFERENCE_MILLIDEGREE_RADIANS = math.radians(1.0e-3)

# Boundaries for the human-readable label, taken from the measured spread of
# public synthetic contact-conditioning study: a mid-season crossing sits near
# first eclipse of the season near 1.4, and the last one near 2.5 - which is
# also where the largest residual against the reference appears.
SHARP_CONTACT_SECONDS_PER_MILLIDEGREE = 0.5
GRAZING_CONTACT_SECONDS_PER_MILLIDEGREE = 2.0


@dataclass(frozen=True)
class EclipseGeometryOptions:
    """Optional refinements to the occultation geometry.

    Both default to off so the bundled synthetic reference remains a simple,
    deterministic baseline.  Enabling either option is a sensitivity study;
    it changes the geometry convention and is not an empirical correction.
    """

    oblate_earth_shadow: bool = False
    light_time_moon: bool = False


DEFAULT_ECLIPSE_GEOMETRY = EclipseGeometryOptions()


@dataclass(frozen=True)
class EclipseEvent:
    """One Earth or Moon occultation of the Sun seen by the satellite."""

    penumbra_entry_utc: datetime | None
    umbra_entry_utc: datetime | None
    umbra_exit_utc: datetime | None
    penumbra_exit_utc: datetime | None
    shadow_body: str = "EARTH"
    penumbra_entry_sensitivity: float | None = None
    umbra_entry_sensitivity: float | None = None
    umbra_exit_sensitivity: float | None = None
    penumbra_exit_sensitivity: float | None = None

    @property
    def total_duration_seconds(self):
        if self.penumbra_entry_utc is None or self.penumbra_exit_utc is None:
            return None
        return (
            self.penumbra_exit_utc - self.penumbra_entry_utc
        ).total_seconds()

    @property
    def umbra_duration_seconds(self):
        if self.umbra_entry_utc is None or self.umbra_exit_utc is None:
            return None
        return (self.umbra_exit_utc - self.umbra_entry_utc).total_seconds()

    @property
    def worst_contact_sensitivity(self):
        """Return the least certain contact, in seconds per millidegree."""

        values = [
            value
            for value in (
                self.penumbra_entry_sensitivity,
                self.umbra_entry_sensitivity,
                self.umbra_exit_sensitivity,
                self.penumbra_exit_sensitivity,
            )
            if value is not None
        ]
        return max(values) if values else None

    @property
    def conditioning(self):
        """Return SHARP, SOFT or GRAZING for this event's contact geometry."""

        worst = self.worst_contact_sensitivity
        if worst is None:
            return "UNKNOWN"
        if worst < SHARP_CONTACT_SECONDS_PER_MILLIDEGREE:
            return "SHARP"
        if worst < GRAZING_CONTACT_SECONDS_PER_MILLIDEGREE:
            return "SOFT"
        return "GRAZING"

    @property
    def is_grazing(self):
        return self.conditioning == "GRAZING"


@dataclass(frozen=True)
class EclipsePrediction:
    """Sample illumination and refined eclipse intervals."""

    elapsed_seconds: np.ndarray
    illumination_fraction: np.ndarray
    states: tuple[str, ...]
    events: tuple[EclipseEvent, ...]
    source_step_seconds: float


@dataclass(frozen=True)
class YearlyEclipseScheduleRow:
    """One display/export row in a selected UTC year's daily schedule."""

    date_utc: date
    status: str
    event_number: int | None
    event: EclipseEvent | None


@dataclass(frozen=True)
class YearlyEclipseSchedule:
    """Daily eclipse schedule with explicit rows for days without events."""

    year: int
    source_step_seconds: float
    rows: tuple[YearlyEclipseScheduleRow, ...]

    @property
    def event_count(self):
        return sum(row.event is not None for row in self.rows)

    @property
    def skipped_day_count(self):
        return sum(row.status == "SKIPPED" for row in self.rows)


class EclipsePredictionCancelled(RuntimeError):
    """Raised when eclipse classification is cancelled by the UI."""


def _csv_utc(value):
    """Return one timezone-aware datetime in the application CSV format."""

    if value is None:
        return ""
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Eclipse CSV datetimes must be timezone-aware.")
    return format_csv_utc(value)


def save_eclipse_prediction_csv(prediction, initial_epoch, file_path):
    """Export an eclipse timeline and its refined event table to two CSVs.

    ``file_path`` is the timeline path selected by the user.  The companion
    event table is saved beside it with an ``_events.csv`` suffix.  Returning
    both resolved paths lets the UI report exactly what was written.
    """

    if not isinstance(initial_epoch, datetime) or initial_epoch.tzinfo is None:
        raise ValueError("initial_epoch must be a timezone-aware datetime.")

    elapsed = np.asarray(prediction.elapsed_seconds, dtype=float)
    illumination = np.asarray(prediction.illumination_fraction, dtype=float)
    states = tuple(prediction.states)
    if elapsed.ndim != 1 or illumination.shape != elapsed.shape:
        raise ValueError("Eclipse timeline arrays must be matching 1-D arrays.")
    if len(states) != len(elapsed):
        raise ValueError("Eclipse state labels must match the timeline length.")
    if not np.all(np.isfinite(elapsed)) or not np.all(np.isfinite(illumination)):
        raise ValueError("Eclipse timeline contains non-finite values.")

    timeline_path = Path(file_path)
    if timeline_path.suffix.lower() != ".csv":
        timeline_path = timeline_path.with_suffix(".csv")
    event_stem = (
        timeline_path.stem[:-9]
        if timeline_path.stem.lower().endswith("_timeline")
        else timeline_path.stem
    )
    events_path = timeline_path.with_name(f"{event_stem}_events.csv")

    with timeline_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "UTC",
                "ElapsedSeconds",
                "SunlightFraction",
                "SunlightPercent",
                "EclipseState",
            )
        )
        for seconds, fraction, state in zip(elapsed, illumination, states):
            epoch = initial_epoch + timedelta(seconds=float(seconds))
            writer.writerow(
                (
                    _csv_utc(epoch),
                    f"{seconds:.6f}",
                    f"{fraction:.12f}",
                    f"{100.0 * fraction:.9f}",
                    state,
                )
            )

    with events_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "Event",
                "ShadowBody",
                "PenumbraEntryUTC",
                "UmbraEntryUTC",
                "UmbraExitUTC",
                "PenumbraExitUTC",
                "TotalDurationSeconds",
                "UmbraDurationSeconds",
            )
        )
        for index, event in enumerate(prediction.events, start=1):
            writer.writerow(
                (
                    index,
                    event.shadow_body,
                    _csv_utc(event.penumbra_entry_utc),
                    _csv_utc(event.umbra_entry_utc),
                    _csv_utc(event.umbra_exit_utc),
                    _csv_utc(event.penumbra_exit_utc),
                    "" if event.total_duration_seconds is None else (
                        f"{event.total_duration_seconds:.6f}"
                    ),
                    "" if event.umbra_duration_seconds is None else (
                        f"{event.umbra_duration_seconds:.6f}"
                    ),
                )
            )

    return timeline_path, events_path


def build_yearly_eclipse_schedule(prediction, year):
    """Group refined events by UTC day and mark empty days as ``SKIPPED``."""

    year = int(year)
    if not 1 <= year <= 9998:
        raise ValueError("year must be between 1 and 9998.")

    start_date = date(year, 1, 1)
    end_date = date(year + 1, 1, 1)
    events_by_date = {}
    for event_number, event in enumerate(prediction.events, start=1):
        reference_epoch = next(
            (
                value
                for value in (
                    event.penumbra_entry_utc,
                    event.umbra_entry_utc,
                    event.umbra_exit_utc,
                    event.penumbra_exit_utc,
                )
                if value is not None
            ),
            None,
        )
        if reference_epoch is None:
            continue
        event_date = reference_epoch.astimezone(timezone.utc).date()
        if start_date <= event_date < end_date:
            events_by_date.setdefault(event_date, []).append(
                (event_number, event)
            )

    rows = []
    current_date = start_date
    while current_date < end_date:
        daily_events = events_by_date.get(current_date, ())
        if not daily_events:
            rows.append(
                YearlyEclipseScheduleRow(
                    date_utc=current_date,
                    status="SKIPPED",
                    event_number=None,
                    event=None,
                )
            )
        else:
            for event_number, event in daily_events:
                rows.append(
                    YearlyEclipseScheduleRow(
                        date_utc=current_date,
                        status="ECLIPSE",
                        event_number=event_number,
                        event=event,
                    )
                )
        current_date += timedelta(days=1)

    return YearlyEclipseSchedule(
        year=year,
        source_step_seconds=float(prediction.source_step_seconds),
        rows=tuple(rows),
    )


def save_yearly_eclipse_schedule_csv(schedule, file_path):
    """Export the selected year's event/``SKIPPED`` daily schedule."""

    output_path = Path(file_path)
    if output_path.suffix.lower() != ".csv":
        output_path = output_path.with_suffix(".csv")

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "DateUTC",
                "Status",
                "Event",
                "ShadowBody",
                "PenumbraEntryUTC",
                "UmbraEntryUTC",
                "UmbraExitUTC",
                "PenumbraExitUTC",
                "TotalDurationSeconds",
                "UmbraDurationSeconds",
                "SearchStepSeconds",
            )
        )
        for row in schedule.rows:
            event = row.event
            writer.writerow(
                (
                    row.date_utc.strftime("%d/%m/%Y"),
                    row.status,
                    "" if row.event_number is None else row.event_number,
                    "" if event is None else event.shadow_body,
                    "" if event is None else _csv_utc(
                        event.penumbra_entry_utc
                    ),
                    "" if event is None else _csv_utc(event.umbra_entry_utc),
                    "" if event is None else _csv_utc(event.umbra_exit_utc),
                    "" if event is None else _csv_utc(
                        event.penumbra_exit_utc
                    ),
                    "" if event is None or event.total_duration_seconds is None
                    else f"{event.total_duration_seconds:.6f}",
                    "" if event is None or event.umbra_duration_seconds is None
                    else f"{event.umbra_duration_seconds:.6f}",
                    f"{schedule.source_step_seconds:.6f}",
                )
            )

    return output_path


def _sun_position_at(epoch, sun_position_at_epoch):
    if sun_position_at_epoch is not None:
        return np.asarray(sun_position_at_epoch(epoch), dtype=float)
    return np.asarray(get_sun_position(utc_to_et(epoch)), dtype=float)


def _moon_position_at(epoch, moon_position_at_epoch, light_time=False):
    """Return the Moon position to use for occultation geometry.

    Light-time corrected, not geometric: the sunlight that reaches the
    satellite passed the Moon where light-time places it. The offset is about
    19 arcsec, near 1% of the lunar apparent radius. Third-body gravity keeps
    using the geometric position through ``moon.get_moon_position``.
    """

    if moon_position_at_epoch is not None:
        return np.asarray(moon_position_at_epoch(epoch), dtype=float)
    reader = (
        get_moon_position_apparent if light_time else get_moon_position
    )
    return np.asarray(reader(utc_to_et(epoch)), dtype=float)


def _occultation_margins(
    r_sat,
    r_sun,
    occulting_body_position=None,
    occulting_body_radius_km=R_EARTH,
    oblate_earth=False,
):
    if occulting_body_position is None:
        sun_radius, body_radius, separation = solar_occultation_geometry(
            r_sat,
            r_sun,
            oblate_earth=oblate_earth,
        )
    else:
        sun_radius, body_radius, separation = occulting_body_geometry(
            r_sat,
            r_sun,
            occulting_body_position,
            occulting_body_radius_km,
        )
    # ANY eclipse begins when the apparent limbs first touch. Full occultation
    # begins when the Earth disc contains the complete Sun disc.
    penumbra_margin = separation - (body_radius + sun_radius)
    umbra_margin = (
        separation - (body_radius - sun_radius)
        if body_radius > sun_radius
        else np.inf
    )
    return float(penumbra_margin), float(umbra_margin)


def _interpolate_state(time_value, t0, t1, state0, state1):
    """Cubic Hermite state interpolation between propagation samples."""

    span = float(t1 - t0)
    if span <= 0.0:
        return np.asarray(state0, dtype=float).copy()
    fraction = float(np.clip((time_value - t0) / span, 0.0, 1.0))
    f2 = fraction * fraction
    f3 = f2 * fraction
    h00 = 2.0 * f3 - 3.0 * f2 + 1.0
    h10 = f3 - 2.0 * f2 + fraction
    h01 = -2.0 * f3 + 3.0 * f2
    h11 = f3 - f2
    position = (
        h00 * state0[:3]
        + h10 * span * state0[3:]
        + h01 * state1[:3]
        + h11 * span * state1[3:]
    )
    velocity = (1.0 - fraction) * state0[3:] + fraction * state1[3:]
    return np.concatenate((position, velocity))


def _refine_transition(
    margin_index,
    t0,
    t1,
    state0,
    state1,
    initial_epoch,
    sun_position_at_epoch,
    shadow_body,
    moon_position_at_epoch,
    geometry=DEFAULT_ECLIPSE_GEOMETRY,
):
    """Bisect one limb-contact transition to millisecond time tolerance.

    Returns ``(time, sensitivity)`` where the sensitivity is how many seconds
    the contact moves per millidegree of geometric error, taken from the rate
    at which the limb margin crosses zero.
    """

    def margin_at(time_value):
        state = _interpolate_state(
            time_value,
            t0,
            t1,
            state0,
            state1,
        )
        epoch = initial_epoch + timedelta(seconds=float(time_value))
        sun = _sun_position_at(epoch, sun_position_at_epoch)
        body_position = (
            None
            if shadow_body == "EARTH"
            else _moon_position_at(
                epoch,
                moon_position_at_epoch,
                geometry.light_time_moon,
            )
        )
        body_radius = R_EARTH if shadow_body == "EARTH" else R_MOON
        return _occultation_margins(
            state[:3],
            sun,
            body_position,
            body_radius,
            oblate_earth=geometry.oblate_earth_shadow,
        )[margin_index]

    def sensitivity_at(time_value):
        """Seconds of contact movement per millidegree of geometric error."""

        span = max(1.0e-6, float(t1 - t0))
        step = min(0.5, 0.25 * span)
        before = margin_at(max(float(t0), time_value - step))
        after = margin_at(min(float(t1), time_value + step))
        slope = abs(after - before) / (2.0 * step)
        if slope <= 0.0:
            return float("inf")
        return float(CONTACT_REFERENCE_MILLIDEGREE_RADIANS / slope)

    lower = float(t0)
    upper = float(t1)
    lower_margin = margin_at(lower)
    upper_margin = margin_at(upper)
    if lower_margin == 0.0:
        return lower, sensitivity_at(lower)
    if upper_margin == 0.0:
        return upper, sensitivity_at(upper)

    for _ in range(64):
        if upper - lower <= ECLIPSE_CONTACT_TOLERANCE_SECONDS:
            break
        midpoint = 0.5 * (lower + upper)
        middle_margin = margin_at(midpoint)
        if (lower_margin <= 0.0) == (middle_margin <= 0.0):
            lower = midpoint
            lower_margin = middle_margin
        else:
            upper = midpoint
            upper_margin = middle_margin
    root = 0.5 * (lower + upper)
    return root, sensitivity_at(root)


def _sensitivity_fields(measured):
    """Map refined-contact sensitivities onto the EclipseEvent field names."""

    return {
        f"{name}_sensitivity": measured.get(name)
        for name in (
            "penumbra_entry",
            "umbra_entry",
            "umbra_exit",
            "penumbra_exit",
        )
    }


def predict_eclipses(
    elapsed_seconds,
    states,
    initial_epoch,
    *,
    sun_position_at_epoch=None,
    shadow_body="EARTH",
    moon_position_at_epoch=None,
    geometry=DEFAULT_ECLIPSE_GEOMETRY,
    cancel_check=None,
    progress_callback=None,
):
    """Predict Earth or Moon penumbra/umbra events from state samples.

    Transition times are refined inside the bracketing propagation interval
    using cubic Hermite position interpolation and the Sun position evaluated
    at each trial UTC epoch. The source output step must still be short enough
    to sample every eclipse at least once.
    """

    times = np.asarray(elapsed_seconds, dtype=float)
    trajectory = np.asarray(states, dtype=float)
    if times.ndim != 1 or len(times) < 2:
        raise ValueError("At least two propagation times are required.")
    if trajectory.shape != (len(times), 6):
        raise ValueError("states must have shape (len(elapsed_seconds), 6).")
    if not isinstance(initial_epoch, datetime) or initial_epoch.tzinfo is None:
        raise ValueError("initial_epoch must be a timezone-aware datetime.")
    if np.any(np.diff(times) <= 0.0):
        raise ValueError("elapsed_seconds must be strictly increasing.")
    shadow_body = str(shadow_body).strip().upper()
    if shadow_body not in {"EARTH", "MOON"}:
        raise ValueError("shadow_body must be EARTH or MOON.")

    illumination = np.empty(len(times), dtype=float)
    penumbra_margins = np.empty(len(times), dtype=float)
    umbra_margins = np.empty(len(times), dtype=float)
    sample_states = []
    for index, (time_value, state) in enumerate(zip(times, trajectory)):
        if index % 256 == 0:
            if cancel_check is not None and cancel_check():
                raise EclipsePredictionCancelled(
                    "Eclipse prediction cancelled by user."
                )
            if progress_callback is not None:
                progress_callback(
                    int(100.0 * index / max(len(times) - 1, 1))
                )
        epoch = initial_epoch + timedelta(seconds=float(time_value))
        sun = _sun_position_at(epoch, sun_position_at_epoch)
        if shadow_body == "EARTH":
            body_position = None
            body_radius = R_EARTH
            illumination[index] = sunlight_fraction(
                state[:3],
                sun,
                oblate_earth=geometry.oblate_earth_shadow,
            )
        else:
            body_position = _moon_position_at(
                epoch,
                moon_position_at_epoch,
                geometry.light_time_moon,
            )
            body_radius = R_MOON
            illumination[index] = occulting_body_sunlight_fraction(
                state[:3],
                sun,
                body_position,
                body_radius,
            )
        (
            penumbra_margins[index],
            umbra_margins[index],
        ) = _occultation_margins(
            state[:3],
            sun,
            body_position,
            body_radius,
            oblate_earth=geometry.oblate_earth_shadow,
        )
        if umbra_margins[index] <= 0.0:
            sample_states.append("UMBRA")
        elif penumbra_margins[index] <= 0.0:
            sample_states.append("PENUMBRA")
        else:
            sample_states.append("FULL SUN")

    penumbra_inside = penumbra_margins <= 0.0
    umbra_inside = umbra_margins <= 0.0
    events = []
    def new_active(penumbra_entry=False, umbra_entry=False):
        return {
            "penumbra_entry": penumbra_entry,
            "umbra_entry": umbra_entry,
            "umbra_exit": False,
            "penumbra_exit": False,
            "sensitivity": {},
        }

    active = (
        new_active(
            penumbra_entry=None,
            umbra_entry=None if umbra_inside[0] else False,
        )
        if penumbra_inside[0]
        else None
    )

    for index in range(len(times) - 1):
        penumbra_changed = penumbra_inside[index] != penumbra_inside[index + 1]
        umbra_changed = umbra_inside[index] != umbra_inside[index + 1]

        penumbra_transition = None
        penumbra_sensitivity = None
        if penumbra_changed:
            penumbra_transition, penumbra_sensitivity = _refine_transition(
                0,
                times[index],
                times[index + 1],
                trajectory[index],
                trajectory[index + 1],
                initial_epoch,
                sun_position_at_epoch,
                shadow_body,
                moon_position_at_epoch,
                geometry,
            )
            if not penumbra_inside[index] and penumbra_inside[index + 1]:
                active = new_active(penumbra_entry=penumbra_transition)
                active["sensitivity"]["penumbra_entry"] = penumbra_sensitivity

        if umbra_changed and active is not None:
            umbra_transition, umbra_sensitivity = _refine_transition(
                1,
                times[index],
                times[index + 1],
                trajectory[index],
                trajectory[index + 1],
                initial_epoch,
                sun_position_at_epoch,
                shadow_body,
                moon_position_at_epoch,
                geometry,
            )
            if not umbra_inside[index] and umbra_inside[index + 1]:
                active["umbra_entry"] = umbra_transition
                active["sensitivity"]["umbra_entry"] = umbra_sensitivity
            else:
                active["umbra_exit"] = umbra_transition
                active["sensitivity"]["umbra_exit"] = umbra_sensitivity

        if (
            penumbra_changed
            and penumbra_inside[index]
            and not penumbra_inside[index + 1]
            and active is not None
        ):
            active["penumbra_exit"] = penumbra_transition
            active["sensitivity"]["penumbra_exit"] = penumbra_sensitivity

            def as_epoch(value):
                if value is False or value is None:
                    return None
                return initial_epoch + timedelta(seconds=float(value))

            events.append(
                EclipseEvent(
                    penumbra_entry_utc=as_epoch(active["penumbra_entry"]),
                    umbra_entry_utc=as_epoch(active["umbra_entry"]),
                    umbra_exit_utc=as_epoch(active["umbra_exit"]),
                    penumbra_exit_utc=as_epoch(active["penumbra_exit"]),
                    shadow_body=shadow_body,
                    **_sensitivity_fields(active["sensitivity"]),
                )
            )
            active = None

    if active is not None:
        def as_epoch(value):
            if value is False or value is None:
                return None
            return initial_epoch + timedelta(seconds=float(value))

        events.append(
            EclipseEvent(
                penumbra_entry_utc=as_epoch(active["penumbra_entry"]),
                umbra_entry_utc=as_epoch(active["umbra_entry"]),
                umbra_exit_utc=as_epoch(active["umbra_exit"]),
                penumbra_exit_utc=None,
                shadow_body=shadow_body,
                **_sensitivity_fields(active["sensitivity"]),
            )
        )

    if progress_callback is not None:
        progress_callback(100)

    return EclipsePrediction(
        elapsed_seconds=times.copy(),
        illumination_fraction=illumination,
        states=tuple(sample_states),
        events=tuple(events),
        source_step_seconds=float(np.max(np.diff(times))),
    )
