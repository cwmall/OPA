"""Background-safe preparation of the Perturbation prediction overlay.

The numerical model and output sampling intentionally match the original GUI
implementation.  This module only separates the expensive work from Qt's main
event loop so the desktop remains responsive while it runs.
"""

from datetime import timedelta

import numpy as np

from moon import get_moon_position, get_sun_position
from moon_perturbation import moon_perturbation
from perturbation_analysis import PERTURBATION_PARAMETERS, acceleration_components
from propagator import PropagationCancelled, propagate_trajectory
from solar_radiation_pressure import solar_radiation_pressure
from sun_perturbation import sun_perturbation
from time_utils import utc_to_et


def _scaled_progress(callback, start, end):
    if callback is None:
        return None
    span = int(end) - int(start)
    return lambda value: callback(int(start) + int(span * int(value) / 100))


def compute_perturbation_prediction(
    *,
    initial_state,
    epoch,
    duration_seconds,
    output_step,
    requested_sources,
    propagate_moon,
    propagate_sun,
    propagate_srp,
    srp_coefficient,
    numerical_settings,
    srp_area_m2=None,
    srp_mass_kg=None,
    cancel_check=None,
    progress_callback=None,
):
    """Return the exact past/future overlay data formerly built in the UI."""

    def cancelled():
        return bool(cancel_check and cancel_check())

    def check_cancelled():
        if cancelled():
            raise PropagationCancelled("Perturbation prediction cancelled by user.")

    common = {
        "include_j2": True,
        "include_moon": bool(propagate_moon),
        "include_sun": bool(propagate_sun),
        "include_srp": bool(propagate_srp),
        "srp_coefficient": srp_coefficient,
    }
    if srp_area_m2 is not None or srp_mass_kg is not None:
        common.update(
            {
                "srp_area_m2": srp_area_m2,
                "srp_mass_kg": srp_mass_kg,
            }
        )
    srp_force_kwargs = {}
    if srp_area_m2 is not None or srp_mass_kg is not None:
        srp_force_kwargs = {
            "area_m2": srp_area_m2,
            "mass_kg": srp_mass_kg,
        }
    settings = dict(numerical_settings)

    past_times, past_states = propagate_trajectory(
        initial_state=initial_state,
        initial_epoch=epoch,
        duration_seconds=-float(duration_seconds),
        output_step=float(output_step),
        cancel_check=cancel_check,
        progress_callback=_scaled_progress(progress_callback, 0, 20),
        **common,
        **settings,
    )
    future_times, future_states = propagate_trajectory(
        initial_state=initial_state,
        initial_epoch=epoch,
        duration_seconds=float(duration_seconds),
        output_step=float(output_step),
        cancel_check=cancel_check,
        progress_callback=_scaled_progress(progress_callback, 20, 40),
        **common,
        **settings,
    )

    relaxed_settings = {
        "rtol": settings["rtol"] * 100.0,
        "atol": settings["atol"] * 100.0,
        "max_step": min(settings["max_step"] * 2.0, 3600.0),
    }
    _, relaxed_past_states = propagate_trajectory(
        initial_state=initial_state,
        initial_epoch=epoch,
        duration_seconds=-float(duration_seconds),
        output_step=float(output_step),
        cancel_check=cancel_check,
        progress_callback=_scaled_progress(progress_callback, 40, 60),
        **common,
        **relaxed_settings,
    )
    _, relaxed_future_states = propagate_trajectory(
        initial_state=initial_state,
        initial_epoch=epoch,
        duration_seconds=float(duration_seconds),
        output_step=float(output_step),
        cancel_check=cancel_check,
        progress_callback=_scaled_progress(progress_callback, 60, 80),
        **common,
        **relaxed_settings,
    )

    elapsed_times = np.concatenate((past_times[::-1][:-1], future_times))
    states = np.vstack((past_states[::-1][:-1], future_states))
    relaxed_states = np.vstack(
        (relaxed_past_states[::-1][:-1], relaxed_future_states)
    )
    prediction_times = [
        epoch + timedelta(seconds=float(elapsed)) for elapsed in elapsed_times
    ]

    accelerations = {name: [] for name in ("Moon", "Sun β", "SRP", "Combined")}
    relaxed_accelerations = {
        name: [] for name in ("Moon", "Sun β", "SRP", "Combined")
    }
    total_points = max(1, len(prediction_times))
    for index, (prediction_time, state, relaxed_state) in enumerate(
        zip(prediction_times, states, relaxed_states)
    ):
        check_cancelled()
        et = utc_to_et(prediction_time)
        r_moon = get_moon_position(et)
        r_sun = get_sun_position(et)
        moon_acceleration = moon_perturbation(state[:3], r_moon)
        sun_acceleration = sun_perturbation(state[:3], r_sun)
        relaxed_moon = moon_perturbation(relaxed_state[:3], r_moon)
        relaxed_sun = sun_perturbation(relaxed_state[:3], r_sun)
        srp_acceleration = (
            solar_radiation_pressure(
                state[:3], r_sun, srp_coefficient, **srp_force_kwargs
            )
            if propagate_srp
            else np.zeros(3, dtype=float)
        )
        relaxed_srp = (
            solar_radiation_pressure(
                relaxed_state[:3],
                r_sun,
                srp_coefficient,
                **srp_force_kwargs,
            )
            if propagate_srp
            else np.zeros(3, dtype=float)
        )
        accelerations["Moon"].append(moon_acceleration)
        accelerations["Sun β"].append(sun_acceleration)
        accelerations["SRP"].append(srp_acceleration)
        accelerations["Combined"].append(
            moon_acceleration + sun_acceleration + srp_acceleration
        )
        relaxed_accelerations["Moon"].append(relaxed_moon)
        relaxed_accelerations["Sun β"].append(relaxed_sun)
        relaxed_accelerations["SRP"].append(relaxed_srp)
        relaxed_accelerations["Combined"].append(
            relaxed_moon + relaxed_sun + relaxed_srp
        )
        if progress_callback is not None and index % 8 == 0:
            progress_callback(80 + int(15 * (index + 1) / total_points))

    accelerations = {
        source: np.asarray(values, dtype=float)
        for source, values in accelerations.items()
    }
    relaxed_accelerations = {
        source: np.asarray(values, dtype=float)
        for source, values in relaxed_accelerations.items()
    }

    prediction_values = {}
    prediction_uncertainty = {}
    selected_sources = tuple(requested_sources)
    for source_index, source in enumerate(selected_sources):
        check_cancelled()
        if source == "SRP" and not propagate_srp:
            continue
        source_values = {name: [] for name in PERTURBATION_PARAMETERS}
        relaxed_values = {name: [] for name in PERTURBATION_PARAMETERS}
        for state, acceleration in zip(states, accelerations[source]):
            values = acceleration_components(acceleration, state)
            for name in PERTURBATION_PARAMETERS:
                source_values[name].append(values[name])
        for state, acceleration in zip(
            relaxed_states, relaxed_accelerations[source]
        ):
            values = acceleration_components(acceleration, state)
            for name in PERTURBATION_PARAMETERS:
                relaxed_values[name].append(values[name])
        source_values = {
            name: np.asarray(values, dtype=float)
            for name, values in source_values.items()
        }
        relaxed_values = {
            name: np.asarray(values, dtype=float)
            for name, values in relaxed_values.items()
        }
        prediction_values[source] = source_values
        prediction_uncertainty[source] = {
            name: np.abs(relaxed_values[name] - values)
            for name, values in source_values.items()
        }
        if progress_callback is not None:
            progress_callback(
                95 + int(5 * (source_index + 1) / max(1, len(selected_sources)))
            )

    if progress_callback is not None:
        progress_callback(100)
    return {
        "epoch": epoch,
        "times": prediction_times,
        "values": prediction_values,
        "uncertainty": prediction_uncertainty,
        "point_count": len(prediction_times),
    }
