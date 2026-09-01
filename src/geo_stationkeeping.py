"""Non-mutating GEO station-keeping analysis and planning estimates.

The module consumes an already propagated J2000 trajectory plus geocentric
Earth-fixed longitude. It never calls the propagator, changes a state, or
creates a burn command.

EW is a first-order, near-circular GEO drift-arrest estimate. Starting with
Kepler's ``dn/n = -3/2 da/a`` and the small tangential-impulse relation
``da = 2 a dv/v``, ``|dv| = a_GEO |d(lambda)/dt| / 3``. NS uses the ideal
instantaneous plane-change equation ``dv = 2 v_GEO sin(|i|/2)``. Propellant
uses ``m_prop = m0 * (1 - exp(-dv / (Isp * g0)))``. These are engineering
advisories, not flight-certified maneuver solutions.

Inclination-vector components use ``[i cos(Omega), i sin(Omega)]`` in radians.
Eccentricity-vector components are the J2000 equatorial-plane projection of
the Cartesian eccentricity vector. Scientific sources are exposed through
``SCIENTIFIC_PROVENANCE`` and documented in ``docs/GEO_OPERATIONS.md``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any

import numpy as np

from constants import MU_EARTH
from orbital_elements import cartesian_to_keplerian


EARTH_SIDEREAL_RATE_RAD_S = 7.2921150e-5
NOMINAL_GEO_RADIUS_KM = (MU_EARTH / EARTH_SIDEREAL_RATE_RAD_S**2) ** (1.0 / 3.0)
NOMINAL_GEO_SPEED_KM_S = math.sqrt(MU_EARTH / NOMINAL_GEO_RADIUS_KM)
STANDARD_GRAVITY_M_S2 = 9.80665
LONGITUDE_WARNING_FRACTION = 0.80

SCIENTIFIC_PROVENANCE = (
    {
        "topic": "east-west station keeping",
        "source": "NASA TN D-5600, Synchronous Satellite Station-Keeping",
        "url": "https://ntrs.nasa.gov/api/citations/19710001770/downloads/19710001770.pdf",
        "use": "Small tangential impulse / osculating semi-major-axis relation.",
    },
    {
        "topic": "plane change",
        "source": "JPL Fundamentals of Orbital Mechanics, Chapter 7",
        "url": "https://spsweb.fltops.jpl.nasa.gov/portaldataops/mpg/MPG_Docs/MPG%20Book/Release/Chapter7-OrbitalMechanics.pdf",
        "use": "Ideal instantaneous plane-change equation.",
    },
    {
        "topic": "propellant estimate",
        "source": "NASA Glenn Ideal Rocket Equation",
        "url": "https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/",
        "use": "Tsiolkovsky ideal rocket equation and specific impulse.",
    },
    {
        "topic": "operational limitation",
        "source": "NASA/JPL Basics of Space Flight, Chapter 13",
        "url": "https://science.nasa.gov/learn/basics-of-space-flight/chapter13-1/",
        "use": "Maneuver design is handed to engineering teams for commands.",
    },
)


class StationKeepingError(ValueError):
    """Raised when trajectory inputs cannot support a GEO analysis."""


def _finite(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise StationKeepingError(f"{name} must be numeric.") from error
    if not math.isfinite(number):
        raise StationKeepingError(f"{name} must be finite.")
    return number


def _optional_nonnegative(value: Any, name: str) -> float | None:
    if value is None:
        return None
    number = _finite(value, name)
    if number < 0.0:
        raise StationKeepingError(f"{name} cannot be negative.")
    return number


def normalize_longitude(longitude_deg: float) -> float:
    """Normalize longitude to ``[-180, 180)``."""

    value = _finite(longitude_deg, "Longitude")
    return (value + 180.0) % 360.0 - 180.0


def wrap_longitude_error(longitude_deg: Any, target_deg: float) -> np.ndarray:
    values = np.asarray(longitude_deg, dtype=float)
    target = _finite(target_deg, "Target longitude")
    return (values - target + 180.0) % 360.0 - 180.0


def estimate_propellant_kg(delta_v_m_s: float, mass_kg: float, isp_s: float) -> float:
    """Return ideal propellant mass using the Tsiolkovsky equation."""

    delta_v = _finite(delta_v_m_s, "Delta-v")
    mass = _finite(mass_kg, "Spacecraft mass")
    isp = _finite(isp_s, "Specific impulse")
    if delta_v < 0.0 or mass <= 0.0 or isp <= 0.0:
        raise StationKeepingError("Mass/Isp must be positive and delta-v non-negative.")
    return mass * (1.0 - math.exp(-delta_v / (isp * STANDARD_GRAVITY_M_S2)))


def east_west_delta_v_m_s(drift_rate_deg_day: float) -> float:
    """First-order tangential delta-v magnitude needed to arrest GEO drift."""

    drift = _finite(drift_rate_deg_day, "Longitude drift rate")
    delta_n_rad_s = math.radians(drift) / 86400.0
    return abs(delta_n_rad_s) * NOMINAL_GEO_RADIUS_KM * 1000.0 / 3.0


def north_south_delta_v_m_s(inclination_deg: float) -> float:
    """Ideal single plane-change delta-v magnitude to remove inclination."""

    inclination = _finite(inclination_deg, "Inclination")
    if inclination < 0.0:
        raise StationKeepingError("Inclination cannot be negative.")
    angle = math.radians(inclination)
    return 2.0 * NOMINAL_GEO_SPEED_KM_S * 1000.0 * math.sin(angle / 2.0)


def _validate_limits(
    target_longitude_deg: Any,
    station_box_half_width_deg: Any,
    inclination_warning_deg: Any,
    inclination_limit_deg: Any,
    eccentricity_warning: Any,
    eccentricity_limit: Any,
) -> tuple[float, float, float, float, float, float]:
    target = _finite(target_longitude_deg, "Target longitude")
    half_width = _finite(station_box_half_width_deg, "Station-box half-width")
    inc_warning = _finite(inclination_warning_deg, "Inclination warning")
    inc_limit = _finite(inclination_limit_deg, "Inclination limit")
    ecc_warning = _finite(eccentricity_warning, "Eccentricity warning")
    ecc_limit = _finite(eccentricity_limit, "Eccentricity limit")
    if not -180.0 <= target <= 180.0:
        raise StationKeepingError("Target longitude must be between -180 and 180 degrees.")
    if not 0.0 < half_width <= 180.0:
        raise StationKeepingError("Station-box half-width must be in (0, 180] degrees.")
    if not 0.0 <= inc_warning <= inc_limit:
        raise StationKeepingError(
            "Inclination warning must be non-negative and no greater than its limit."
        )
    if not 0.0 <= ecc_warning <= ecc_limit < 1.0:
        raise StationKeepingError(
            "Eccentricity warning/limit must satisfy 0 <= warning <= limit < 1."
        )
    return target, half_width, inc_warning, inc_limit, ecc_warning, ecc_limit


def _station_box_status(longitude_error: float, half_width: float) -> tuple[str, str]:
    magnitude = abs(longitude_error)
    tolerance = 1.0e-12 * max(1.0, half_width)
    if magnitude > half_width + tolerance:
        return "OUTSIDE", "longitude outside station box"
    if magnitude >= LONGITUDE_WARNING_FRACTION * half_width - tolerance:
        return "WARNING", "longitude near station-box boundary"
    return "NOMINAL", "longitude inside station box"


def _overall_status(
    station_box_status: str,
    station_box_reason: str,
    inclination: float,
    inc_warning: float,
    inc_limit: float,
    eccentricity: float,
    ecc_warning: float,
    ecc_limit: float,
) -> tuple[str, tuple[str, ...]]:
    reasons = [] if station_box_status == "NOMINAL" else [station_box_reason]
    outside = station_box_status == "OUTSIDE"
    warning = station_box_status == "WARNING"
    if inclination > inc_limit:
        outside = True
        reasons.append("inclination above limit")
    elif inclination > inc_warning:
        warning = True
        reasons.append("inclination warning")
    if eccentricity > ecc_limit:
        outside = True
        reasons.append("eccentricity above limit")
    elif eccentricity > ecc_warning:
        warning = True
        reasons.append("eccentricity warning")
    return ("OUTSIDE" if outside else "WARNING" if warning else "NOMINAL", tuple(reasons))


def _first_boundary_crossing(
    times: np.ndarray, unwrapped_errors: np.ndarray, half_width: float
) -> tuple[int | None, float | None, str | None, bool]:
    """Interpolate the first propagated crossing of either longitude limit."""

    if abs(float(unwrapped_errors[0])) >= half_width:
        side = "EAST" if unwrapped_errors[0] >= 0.0 else "WEST"
        return 0, float(times[0]), side, False
    for index in range(1, len(times)):
        previous = float(unwrapped_errors[index - 1])
        current = float(unwrapped_errors[index])
        if abs(current) < half_width:
            continue
        boundary = math.copysign(half_width, current)
        denominator = current - previous
        fraction = 1.0 if denominator == 0.0 else (boundary - previous) / denominator
        fraction = min(1.0, max(0.0, fraction))
        crossing = float(times[index - 1] + fraction * (times[index] - times[index - 1]))
        return index, crossing, "EAST" if boundary > 0.0 else "WEST", fraction < 1.0
    return None, None, None, False


def _linear_boundary_estimate_seconds(
    current_error_deg: float, drift_rate_deg_day: float, half_width: float
) -> tuple[float | None, str | None]:
    if abs(current_error_deg) >= half_width:
        return 0.0, "EAST" if current_error_deg >= 0.0 else "WEST"
    if abs(drift_rate_deg_day) < 1.0e-15:
        return None, None
    boundary = half_width if drift_rate_deg_day > 0.0 else -half_width
    days = (boundary - current_error_deg) / drift_rate_deg_day
    if days < 0.0 or not math.isfinite(days):
        return None, None
    return days * 86400.0, "EAST" if boundary > 0.0 else "WEST"


def _ew_direction(drift_rate_deg_day: float) -> tuple[str, str]:
    if drift_rate_deg_day > 1.0e-15:
        return (
            "EASTWARD",
            "PROGRADE · INCREASE OSCULATING SEMI-MAJOR AXIS · LOWER MEAN MOTION",
        )
    if drift_rate_deg_day < -1.0e-15:
        return (
            "WESTWARD",
            "RETROGRADE · DECREASE OSCULATING SEMI-MAJOR AXIS · RAISE MEAN MOTION",
        )
    return "ZERO DRIFT", "NO EAST-WEST CORRECTION INDICATED"


def _propellant_summary(
    ew_delta_v: float,
    ns_delta_v: float,
    mass_kg: float | None,
    isp_s: float | None,
    available_propellant_mass_kg: float | None,
) -> dict[str, Any]:
    mass = _optional_nonnegative(mass_kg, "Spacecraft mass")
    isp = _optional_nonnegative(isp_s, "Specific impulse")
    inventory = _optional_nonnegative(
        available_propellant_mass_kg, "Available propellant mass"
    )
    if mass == 0.0:
        raise StationKeepingError("Spacecraft mass must be positive.")
    if isp == 0.0:
        raise StationKeepingError("Specific impulse must be positive.")
    if mass is None or isp is None:
        missing = []
        if mass is None:
            missing.append("TOTAL MASS")
        if isp is None:
            missing.append("ISP")
        return {
            "east_west_propellant_estimate_kg": None,
            "north_south_propellant_estimate_kg": None,
            "propellant_estimate_kg": None,
            "propellant_status": "INSUFFICIENT DATA — " + " AND ".join(missing),
            "available_propellant_mass_kg": inventory,
            "propellant_margin_kg": None,
        }
    ew_propellant = estimate_propellant_kg(ew_delta_v, mass, isp)
    ns_propellant = estimate_propellant_kg(ns_delta_v, mass, isp)
    total_propellant = estimate_propellant_kg(ew_delta_v + ns_delta_v, mass, isp)
    if inventory is None:
        status = "ESTIMATE AVAILABLE · PROPELLANT INVENTORY NOT CONFIGURED"
        margin = None
    else:
        margin = inventory - total_propellant
        status = (
            "WITHIN CONFIGURED PROPELLANT INVENTORY"
            if margin >= 0.0
            else "WARNING · ESTIMATE EXCEEDS CONFIGURED PROPELLANT"
        )
    return {
        "east_west_propellant_estimate_kg": ew_propellant,
        "north_south_propellant_estimate_kg": ns_propellant,
        "propellant_estimate_kg": total_propellant,
        "propellant_status": status,
        "available_propellant_mass_kg": inventory,
        "propellant_margin_kg": margin,
    }


def _budget_summary(
    total_delta_v: float,
    annual_budget_m_s: float | None,
    annual_used_m_s: float | None,
) -> dict[str, Any]:
    budget = _optional_nonnegative(annual_budget_m_s, "Annual delta-v budget")
    used = _optional_nonnegative(annual_used_m_s, "Annual delta-v used")
    if budget is None:
        return {
            "annual_delta_v_budget_m_s": None,
            "annual_delta_v_used_m_s": used or 0.0,
            "annual_budget_remaining_before_m_s": None,
            "annual_budget_remaining_m_s": None,
            "annual_budget_fraction_after_advisory": None,
            "annual_budget_status": "NOT CONFIGURED",
        }
    used = used or 0.0
    remaining_before = budget - used
    remaining_after = remaining_before - total_delta_v
    if remaining_before < 0.0:
        status = "EXCEEDED BEFORE THIS ADVISORY"
    elif remaining_after < 0.0:
        status = "ADVISORY EXCEEDS REMAINING BUDGET"
    else:
        status = "WITHIN CONFIGURED BUDGET"
    return {
        "annual_delta_v_budget_m_s": budget,
        "annual_delta_v_used_m_s": used,
        "annual_budget_remaining_before_m_s": remaining_before,
        "annual_budget_remaining_m_s": remaining_after,
        "annual_budget_fraction_after_advisory": (
            remaining_after / budget if budget > 0.0 else None
        ),
        "annual_budget_status": status,
    }


def analyze_geo_trajectory(
    elapsed_seconds: Any,
    states: Any,
    longitudes_deg: Any,
    epoch: datetime,
    *,
    target_longitude_deg: float,
    station_box_half_width_deg: float,
    inclination_warning_deg: float,
    inclination_limit_deg: float,
    eccentricity_warning: float,
    eccentricity_limit: float,
    mass_kg: float | None = None,
    isp_s: float | None = None,
    available_propellant_mass_kg: float | None = None,
    annual_delta_v_budget_m_s: float | None = None,
    annual_delta_v_used_m_s: float | None = 0.0,
) -> dict[str, Any]:
    """Analyze a propagated GEO arc without mutating caller-owned input."""

    times = np.asarray(elapsed_seconds, dtype=float)
    trajectory = np.asarray(states, dtype=float)
    longitude = np.asarray(longitudes_deg, dtype=float)
    if not isinstance(epoch, datetime) or epoch.tzinfo is None:
        raise StationKeepingError("Epoch must be timezone-aware.")
    if times.ndim != 1 or len(times) < 2:
        raise StationKeepingError("At least two trajectory samples are required.")
    if trajectory.shape != (len(times), 6) or longitude.shape != (len(times),):
        raise StationKeepingError("Trajectory, time and longitude shapes do not match.")
    if not (
        np.all(np.isfinite(times))
        and np.all(np.isfinite(trajectory))
        and np.all(np.isfinite(longitude))
    ):
        raise StationKeepingError("Trajectory contains non-finite values.")
    if np.any(np.diff(times) <= 0.0):
        raise StationKeepingError("Elapsed times must be strictly increasing.")
    (
        target,
        half_width,
        inc_warning,
        inc_limit,
        ecc_warning,
        ecc_limit,
    ) = _validate_limits(
        target_longitude_deg,
        station_box_half_width_deg,
        inclination_warning_deg,
        inclination_limit_deg,
        eccentricity_warning,
        eccentricity_limit,
    )

    longitude_errors = wrap_longitude_error(longitude, target)
    unwrapped_errors = np.degrees(np.unwrap(np.radians(longitude_errors)))
    fit_end = min(float(times[-1]), float(times[0]) + 86400.0)
    fit_mask = times <= fit_end
    if int(np.count_nonzero(fit_mask)) < 2:
        fit_mask = np.zeros(len(times), dtype=bool)
        fit_mask[:2] = True
    fit_times = times[fit_mask]
    fit_errors = unwrapped_errors[fit_mask]
    slope_deg_s = float(np.polyfit(fit_times - fit_times[0], fit_errors, 1)[0])
    drift_rate_deg_day = slope_deg_s * 86400.0

    elements = [cartesian_to_keplerian(state) for state in trajectory]
    semimajor = np.asarray([item["a_km"] for item in elements], dtype=float)
    eccentricity = np.asarray([item["e"] for item in elements], dtype=float)
    inclination = np.asarray([item["i_deg"] for item in elements], dtype=float)
    if not (
        np.all(np.isfinite(semimajor))
        and np.all(np.isfinite(eccentricity))
        and np.all(np.isfinite(inclination))
    ):
        raise StationKeepingError("Orbital elements contain non-finite values.")
    raan = np.radians(np.asarray([item["raan_deg"] for item in elements], dtype=float))
    inc_rad = np.radians(inclination)
    inclination_vectors = np.column_stack(
        (inc_rad * np.cos(raan), inc_rad * np.sin(raan))
    )
    eccentricity_vectors = np.asarray(
        [item["eccentricity_vector"][:2] for item in elements], dtype=float
    )

    boundary_index, boundary_elapsed, boundary_side, interpolated = (
        _first_boundary_crossing(times, unwrapped_errors, half_width)
    )
    epoch_utc = epoch.astimezone(timezone.utc)
    boundary_utc = (
        epoch_utc + timedelta(seconds=boundary_elapsed)
        if boundary_elapsed is not None
        else None
    )
    time_to_boundary = (
        boundary_elapsed - float(times[0]) if boundary_elapsed is not None else None
    )
    linear_seconds, linear_side = _linear_boundary_estimate_seconds(
        float(longitude_errors[0]), drift_rate_deg_day, half_width
    )
    linear_boundary_utc = (
        epoch_utc + timedelta(seconds=float(times[0]) + linear_seconds)
        if boundary_utc is None and linear_seconds is not None
        else None
    )

    current_error = float(longitude_errors[0])
    current_inc = float(inclination[0])
    current_ecc = float(eccentricity[0])
    station_box_status, station_box_reason = _station_box_status(
        current_error, half_width
    )
    status, reasons = _overall_status(
        station_box_status,
        station_box_reason,
        current_inc,
        inc_warning,
        inc_limit,
        current_ecc,
        ecc_warning,
        ecc_limit,
    )

    drift_direction, ew_correction = _ew_direction(drift_rate_deg_day)
    ew_delta_v = east_west_delta_v_m_s(drift_rate_deg_day)
    ns_delta_v = north_south_delta_v_m_s(current_inc)
    total_delta_v = ew_delta_v + ns_delta_v
    propellant = _propellant_summary(
        ew_delta_v, ns_delta_v, mass_kg, isp_s, available_propellant_mass_kg
    )
    budget = _budget_summary(
        total_delta_v, annual_delta_v_budget_m_s, annual_delta_v_used_m_s
    )
    timeline_utc = tuple(
        epoch_utc + timedelta(seconds=float(value)) for value in times
    )

    result = {
        "status": status,
        "overall_status": status,
        "status_reasons": reasons,
        "station_box_status": station_box_status,
        "station_box_reason": station_box_reason,
        "current_longitude_deg": normalize_longitude(float(longitude[0])),
        "target_longitude_deg": target,
        "west_limit_longitude_deg": normalize_longitude(target - half_width),
        "east_limit_longitude_deg": normalize_longitude(target + half_width),
        "station_box_half_width_deg": half_width,
        "inclination_warning_deg": inc_warning,
        "inclination_limit_deg": inc_limit,
        "eccentricity_warning": ecc_warning,
        "eccentricity_limit": ecc_limit,
        "longitude_warning_fraction": LONGITUDE_WARNING_FRACTION,
        "analysis_epoch_utc": timeline_utc[0],
        "longitude_error_deg": current_error,
        "drift_rate_deg_day": drift_rate_deg_day,
        "drift_fit_span_seconds": float(fit_times[-1] - fit_times[0]),
        "drift_fit_sample_count": int(len(fit_times)),
        "semimajor_axis_km": float(semimajor[0]),
        "semimajor_offset_km": float(semimajor[0] - NOMINAL_GEO_RADIUS_KM),
        "inclination_deg": current_inc,
        "eccentricity": current_ecc,
        "inclination_vector_rad": inclination_vectors[0].copy(),
        "eccentricity_vector_xy": eccentricity_vectors[0].copy(),
        "boundary_index": boundary_index,
        "boundary_elapsed_seconds": boundary_elapsed,
        "boundary_side": boundary_side,
        "boundary_interpolated": interpolated,
        "boundary_utc": boundary_utc,
        "time_to_boundary_seconds": time_to_boundary,
        "linear_boundary_utc": linear_boundary_utc,
        "linear_boundary_side": linear_side if boundary_utc is None else None,
        "linear_time_to_boundary_seconds": linear_seconds if boundary_utc is None else None,
        "boundary_prediction_kind": (
            "PROPAGATED INTERPOLATION"
            if boundary_utc is not None and interpolated
            else "PROPAGATED SAMPLE"
            if boundary_utc is not None
            else "LINEAR ESTIMATE"
            if linear_boundary_utc is not None
            else "NO CROSSING FOUND"
        ),
        "east_west_direction": drift_direction,
        "east_west_correction_direction": ew_correction,
        "east_west_delta_v_m_s": ew_delta_v,
        "north_south_direction": (
            "NO PLANE CORRECTION INDICATED"
            if ns_delta_v == 0.0
            else "PLANE CHANGE TOWARD EQUATOR · NODE/TIMING REQUIRES MANEUVER DESIGN"
        ),
        "north_south_delta_v_m_s": ns_delta_v,
        "total_advisory_delta_v_m_s": total_delta_v,
        "elapsed_seconds": times.copy(),
        "timeline_utc": timeline_utc,
        "longitudes_deg": longitude.copy(),
        "longitude_errors_deg": longitude_errors.copy(),
        "semimajor_axis_series_km": semimajor,
        "inclination_series_deg": inclination,
        "eccentricity_series": eccentricity,
        "inclination_vector_series_rad": inclination_vectors,
        "eccentricity_vector_series_xy": eccentricity_vectors,
        "scientific_provenance": tuple(dict(item) for item in SCIENTIFIC_PROVENANCE),
        "assumptions": (
            "The first propagated sample is treated as the current analysis epoch.",
            "Longitude is geocentric and Earth-fixed; errors are shortest signed angles.",
            "The propagated boundary time is linearly interpolated between adjacent samples.",
            "Drift is a least-squares slope over up to the first 24 forecast hours.",
            "EW delta-v is a first-order circular-GEO drift-arrest estimate, not a dead-band reversal.",
            "NS delta-v is an ideal instantaneous plane-change estimate.",
            "Propellant excludes margins, finite-burn loss, duty cycle and residuals.",
            "No maneuver is applied, scheduled, converted to commands, or flight certified.",
        ),
    }
    result.update(propellant)
    result.update(budget)
    return result
