"""
Numerical orbit propagator.

Force model:
- Earth central gravity
- Earth EGM96 2x2 through validated 4x4 spherical harmonics (optional;
  default remains 4x4)
- Moon third-body perturbation using DE440 (optional)
- Sun third-body perturbation using DE440 (optional)
- Spacecraft solar radiation pressure with eclipse: generic box-wing or
  an explicit Sun-tracking effective-area model (optional)

Frame: Earth-centered J2000
Units: km, km/s, km/s^2, s
"""

from datetime import datetime

import numpy as np
from scipy.integrate import solve_ivp

from constants import (
    DEFAULT_ATOL,
    DEFAULT_MAX_STEP,
    DEFAULT_RTOL,
    EARTH_GRAVITY_DEGREE,
)
from earth_gravity import earth_gravity
from moon import get_moon_position, get_sun_position
from moon_perturbation import moon_perturbation
from sun_perturbation import sun_perturbation
from solar_radiation_pressure import (
    solar_pressure_coefficient_for_epoch,
    solar_radiation_pressure,
)
from time_utils import utc_to_et


class PropagationCancelled(RuntimeError):
    """Raised when a running numerical propagation is cancelled."""


def validate_state(state):
    state = np.asarray(state, dtype=float)

    if state.shape != (6,):
        raise ValueError(
            "state must contain exactly 6 elements: "
            "[x, y, z, vx, vy, vz]"
        )

    if not np.all(np.isfinite(state)):
        raise ValueError("state contains non-finite values.")

    if float(np.linalg.norm(state[:3])) <= 0.0:
        raise ValueError(
            "Satellite position magnitude must be greater than zero."
        )

    return state


def total_acceleration(
    et,
    r_sat,
    include_j2=True,
    include_moon=True,
    include_sun=False,
    include_srp=False,
    srp_coefficient=None,
    srp_area_m2=None,
    srp_mass_kg=None,
    include_tesseral=None,
    earth_harmonic_degree=None,
):
    r_sat = np.asarray(r_sat, dtype=float)

    if include_tesseral is None:
        include_tesseral = bool(include_j2)

    resolved_harmonic_degree = (
        EARTH_GRAVITY_DEGREE
        if earth_harmonic_degree is None
        else int(earth_harmonic_degree)
    )
    if resolved_harmonic_degree < 2 or resolved_harmonic_degree > EARTH_GRAVITY_DEGREE:
        raise ValueError(
            f"earth_harmonic_degree must be between 2 and {EARTH_GRAVITY_DEGREE}."
        )
    harmonic_degree = (
        resolved_harmonic_degree
        if include_j2 and include_tesseral
        else None
    )

    acceleration = earth_gravity(
        r_sat,
        include_j2=include_j2,
        et=et,
        include_tesseral=(
            include_tesseral and harmonic_degree is None
        ),
        harmonic_degree=harmonic_degree,
    )

    if include_moon:
        r_moon = get_moon_position(et)
        acceleration = acceleration + moon_perturbation(r_sat, r_moon)

    if include_sun:
        r_sun = get_sun_position(et)
        acceleration = acceleration + sun_perturbation(r_sat, r_sun)

    if include_srp:
        if srp_coefficient is None:
            raise ValueError("srp_coefficient is required when SRP is enabled.")
        r_sun = get_sun_position(et)
        acceleration = acceleration + solar_radiation_pressure(
            r_sat,
            r_sun,
            srp_coefficient,
            area_m2=srp_area_m2,
            mass_kg=srp_mass_kg,
        )

    return np.asarray(acceleration, dtype=float)


def equations_of_motion(
    t,
    state,
    initial_et,
    include_j2=True,
    include_moon=True,
    include_sun=False,
    include_srp=False,
    srp_coefficient=None,
    srp_area_m2=None,
    srp_mass_kg=None,
    include_tesseral=None,
    earth_harmonic_degree=None,
):
    state = np.asarray(state, dtype=float)

    r_sat = state[:3]
    velocity = state[3:]

    current_et = float(initial_et) + float(t)

    acceleration = total_acceleration(
        current_et,
        r_sat,
        include_j2=include_j2,
        include_moon=include_moon,
        include_sun=include_sun,
        include_srp=include_srp,
        srp_coefficient=srp_coefficient,
        srp_area_m2=srp_area_m2,
        srp_mass_kg=srp_mass_kg,
        include_tesseral=include_tesseral,
        earth_harmonic_degree=earth_harmonic_degree,
    )

    derivative = np.empty(6, dtype=float)
    derivative[:3] = velocity
    derivative[3:] = acceleration

    return derivative


def propagate_state(
    initial_state,
    initial_epoch,
    duration_seconds,
    include_j2=True,
    include_moon=True,
    include_sun=False,
    include_srp=False,
    srp_coefficient=None,
    srp_area_m2=None,
    srp_mass_kg=None,
    include_tesseral=None,
    rtol=DEFAULT_RTOL,
    atol=DEFAULT_ATOL,
    max_step=DEFAULT_MAX_STEP,
    earth_harmonic_degree=None,
):
    initial_state = validate_state(initial_state)

    if not isinstance(initial_epoch, datetime):
        raise TypeError("initial_epoch must be a datetime object.")

    if initial_epoch.tzinfo is None:
        raise ValueError("initial_epoch must be timezone-aware.")

    duration_seconds = float(duration_seconds)

    if duration_seconds < 0.0:
        raise ValueError(
            "duration_seconds must be greater than or equal to zero."
        )

    if duration_seconds == 0.0:
        return initial_state.copy()

    initial_et = utc_to_et(initial_epoch)
    if include_srp and srp_coefficient is None:
        srp_coefficient = solar_pressure_coefficient_for_epoch(initial_epoch)

    solution = solve_ivp(
        fun=lambda t, y: equations_of_motion(
            t,
            y,
            initial_et,
            include_j2=include_j2,
            include_moon=include_moon,
            include_sun=include_sun,
            include_srp=include_srp,
            srp_coefficient=srp_coefficient,
            srp_area_m2=srp_area_m2,
            srp_mass_kg=srp_mass_kg,
            include_tesseral=include_tesseral,
            earth_harmonic_degree=earth_harmonic_degree,
        ),
        t_span=(0.0, duration_seconds),
        y0=initial_state,
        method="DOP853",
        rtol=rtol,
        atol=atol,
        max_step=max_step,
        t_eval=[duration_seconds],
    )

    if not solution.success:
        raise RuntimeError(
            "Orbit propagation failed: " + solution.message
        )

    return np.asarray(solution.y[:, -1], dtype=float)


def propagate_trajectory(
    initial_state,
    initial_epoch,
    duration_seconds,
    output_step=3600.0,
    include_j2=True,
    include_moon=True,
    include_sun=False,
    include_srp=False,
    srp_coefficient=None,
    srp_area_m2=None,
    srp_mass_kg=None,
    include_tesseral=None,
    rtol=DEFAULT_RTOL,
    atol=DEFAULT_ATOL,
    max_step=DEFAULT_MAX_STEP,
    cancel_check=None,
    progress_callback=None,
    earth_harmonic_degree=None,
):
    initial_state = validate_state(initial_state)

    if not isinstance(initial_epoch, datetime):
        raise TypeError("initial_epoch must be a datetime object.")

    if initial_epoch.tzinfo is None:
        raise ValueError("initial_epoch must be timezone-aware.")

    duration_seconds = float(duration_seconds)
    output_step = float(output_step)

    if duration_seconds == 0.0:
        raise ValueError("duration_seconds must be non-zero.")

    if output_step <= 0.0:
        raise ValueError("output_step must be greater than zero.")

    initial_et = utc_to_et(initial_epoch)
    if include_srp and srp_coefficient is None:
        srp_coefficient = solar_pressure_coefficient_for_epoch(initial_epoch)

    last_progress = -1

    def trajectory_equations(t, state):
        nonlocal last_progress

        if (
            cancel_check is not None
            and cancel_check()
        ):
            raise PropagationCancelled(
                "Propagation cancelled by user."
            )

        if progress_callback is not None:
            progress = int(
                min(
                    99.0,
                    abs(float(t) / duration_seconds) * 100.0,
                )
            )
            if progress > last_progress:
                last_progress = progress
                progress_callback(
                    progress
                )

        return equations_of_motion(
            t,
            state,
            initial_et,
            include_j2=include_j2,
            include_moon=include_moon,
            include_sun=include_sun,
            include_srp=include_srp,
            srp_coefficient=srp_coefficient,
            srp_area_m2=srp_area_m2,
            srp_mass_kg=srp_mass_kg,
            include_tesseral=include_tesseral,
            earth_harmonic_degree=earth_harmonic_degree,
        )

    direction = (
        1.0
        if duration_seconds > 0.0
        else -1.0
    )

    output_times = np.arange(
        0.0,
        duration_seconds,
        direction * output_step,
        dtype=float,
    )

    if (
        len(output_times) == 0
        or not np.isclose(
            output_times[-1],
            duration_seconds,
        )
    ):
        output_times = np.append(output_times, duration_seconds)

    solution = solve_ivp(
        fun=trajectory_equations,
        t_span=(0.0, duration_seconds),
        y0=initial_state,
        method="DOP853",
        t_eval=output_times,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
    )

    if not solution.success:
        raise RuntimeError(
            "Orbit propagation failed: " + solution.message
        )

    if progress_callback is not None:
        progress_callback(
            100
        )

    return (
        np.asarray(solution.t, dtype=float),
        np.asarray(solution.y.T, dtype=float),
    )


def propagate_position(
    initial_state,
    initial_epoch,
    duration_seconds,
    include_j2=True,
    include_moon=True,
    include_sun=False,
    include_srp=False,
    srp_coefficient=None,
    srp_area_m2=None,
    srp_mass_kg=None,
    include_tesseral=None,
    earth_harmonic_degree=None,
):
    final_state = propagate_state(
        initial_state=initial_state,
        initial_epoch=initial_epoch,
        duration_seconds=duration_seconds,
        include_j2=include_j2,
        include_moon=include_moon,
        include_sun=include_sun,
        include_srp=include_srp,
        srp_coefficient=srp_coefficient,
        srp_area_m2=srp_area_m2,
        srp_mass_kg=srp_mass_kg,
        include_tesseral=include_tesseral,
        earth_harmonic_degree=earth_harmonic_degree,
    )

    return final_state[:3]


def propagate_velocity(
    initial_state,
    initial_epoch,
    duration_seconds,
    include_j2=True,
    include_moon=True,
    include_sun=False,
    include_srp=False,
    srp_coefficient=None,
    srp_area_m2=None,
    srp_mass_kg=None,
    include_tesseral=None,
    earth_harmonic_degree=None,
):
    final_state = propagate_state(
        initial_state=initial_state,
        initial_epoch=initial_epoch,
        duration_seconds=duration_seconds,
        include_j2=include_j2,
        include_moon=include_moon,
        include_sun=include_sun,
        include_srp=include_srp,
        srp_coefficient=srp_coefficient,
        srp_area_m2=srp_area_m2,
        srp_mass_kg=srp_mass_kg,
        include_tesseral=include_tesseral,
        earth_harmonic_degree=earth_harmonic_degree,
    )

    return final_state[3:]
