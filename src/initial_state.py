"""
Generic initial-state utilities for public TLE and Cartesian workflows.

IMPORTANT
---------
TLE / Skyfield is used here only to obtain a temporary
initial Cartesian state for testing the numerical propagator.

Once an authoritative state vector is provided by the
reference / flight-dynamics system, that state should replace
the temporary TLE-derived initialization.

Propagation itself is NOT performed by SGP4 in this module.
"""

from datetime import datetime, timedelta

import numpy as np
from skyfield.api import wgs84

from constants import MU_EARTH, R_EARTH
from earth_orientation import (
    skyfield_time_from_datetime,
    skyfield_time_from_datetimes,
)
from satellite import TARGET_SATELLITE_NAME, load_satellite


# ============================================================
# DEFAULT SATELLITE
# ============================================================

DEFAULT_SATELLITE_NAME = TARGET_SATELLITE_NAME

EARTH_SIDEREAL_ROTATION_RATE_RAD_S = 7.2921150e-5
NOMINAL_GEO_RADIUS_KM = (
    MU_EARTH / EARTH_SIDEREAL_ROTATION_RATE_RAD_S**2
) ** (1.0 / 3.0)

# ============================================================
# LOAD TLE SATELLITE
# ============================================================

def load_satellite_from_tle(
    satellite_name=DEFAULT_SATELLITE_NAME,
):
    """
    Load a satellite from the current CelesTrak active TLE list.

    Parameters
    ----------
    satellite_name : str
        Satellite name.

    Returns
    -------
    EarthSatellite
        Skyfield satellite object.
    """

    return load_satellite(
        satellite_name
    )


# ============================================================
# TEMPORARY INITIAL STATE FROM TLE
# ============================================================

def get_tle_initial_state(
    epoch,
    satellite_name=DEFAULT_SATELLITE_NAME,
):
    """
    Generate a temporary initial state using a TLE.

    Parameters
    ----------
    epoch : datetime
        Timezone-aware UTC epoch.

    satellite_name : str
        Satellite name.

    Returns
    -------
    numpy.ndarray
        Cartesian state:

        [x, y, z, vx, vy, vz]

        Position : km
        Velocity : km/s

    Notes
    -----
    This state is intended only to bootstrap and test
    the numerical propagator.

    For high-accuracy validation against the flight-dynamics
    reference system, replace this with an authoritative state
    vector at an explicitly defined epoch and reference frame.
    """

    if not isinstance(
        epoch,
        datetime,
    ):
        raise TypeError(
            "epoch must be a datetime object."
        )

    if epoch.tzinfo is None:
        raise ValueError(
            "epoch must be timezone-aware."
        )

    satellite = load_satellite_from_tle(
        satellite_name
    )

    skyfield_time = skyfield_time_from_datetime(epoch)

    geocentric = satellite.at(
        skyfield_time
    )

    position = np.asarray(
        geocentric.position.km,
        dtype=float,
    )

    velocity = np.asarray(
        geocentric.velocity.km_per_s,
        dtype=float,
    )

    state = np.concatenate(
        (
            position,
            velocity,
        )
    )

    if state.shape != (6,):
        raise RuntimeError(
            "Invalid state returned from Skyfield."
        )

    return state


# ============================================================
# MANUAL / REFERENCE STATE
# ============================================================

def create_initial_state(
    x,
    y,
    z,
    vx,
    vy,
    vz,
):
    """
    Create a Cartesian state vector manually.

    Position
    --------
    x, y, z : km

    Velocity
    --------
    vx, vy, vz : km/s

    Returns
    -------
    numpy.ndarray
        [x, y, z, vx, vy, vz]
    """

    state = np.array(
        [
            x,
            y,
            z,
            vx,
            vy,
            vz,
        ],
        dtype=float,
    )

    if not np.all(
        np.isfinite(state)
    ):
        raise ValueError(
            "Initial state contains invalid values."
        )

    return state


def get_nominal_geostationary_state(epoch, longitude_deg=12.0):
    """Return a fixed Earth-relative circular GEO state in GCRS/J2000.

    This supports apples-to-apples validation of nominal-slot Eclipse
    schedules. It is intentionally separate from free physical propagation
    of an authoritative state or a temporary TLE-derived state.
    """

    if not isinstance(epoch, datetime):
        raise TypeError("epoch must be a datetime object.")
    if epoch.tzinfo is None:
        raise ValueError("epoch must be timezone-aware.")
    longitude_deg = float(longitude_deg)
    if not np.isfinite(longitude_deg):
        raise ValueError("longitude_deg must be finite.")

    nominal_location = wgs84.latlon(
        latitude_degrees=0.0,
        longitude_degrees=longitude_deg,
        elevation_m=(NOMINAL_GEO_RADIUS_KM - R_EARTH) * 1000.0,
    )
    geocentric = nominal_location.at(skyfield_time_from_datetime(epoch))
    return np.concatenate(
        (
            np.asarray(geocentric.position.km, dtype=float),
            np.asarray(geocentric.velocity.km_per_s, dtype=float),
        )
    )


def nominal_geostationary_trajectory(
    initial_epoch,
    duration_seconds,
    output_step=3600.0,
    *,
    longitude_deg=12.0,
    cancel_check=None,
    progress_callback=None,
):
    """Sample a fixed-longitude nominal GEO orbit in GCRS/J2000."""

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
    if cancel_check is not None and cancel_check():
        from propagator import PropagationCancelled
        raise PropagationCancelled("Propagation cancelled by user.")

    direction = 1.0 if duration_seconds > 0.0 else -1.0
    output_times = np.arange(
        0.0,
        duration_seconds,
        direction * output_step,
        dtype=float,
    )
    if len(output_times) == 0 or not np.isclose(
        output_times[-1], duration_seconds
    ):
        output_times = np.append(output_times, duration_seconds)

    if progress_callback is not None:
        progress_callback(5)
    epochs = [
        initial_epoch + timedelta(seconds=float(seconds))
        for seconds in output_times
    ]
    nominal_location = wgs84.latlon(
        latitude_degrees=0.0,
        longitude_degrees=float(longitude_deg),
        elevation_m=(NOMINAL_GEO_RADIUS_KM - R_EARTH) * 1000.0,
    )
    geocentric = nominal_location.at(skyfield_time_from_datetimes(epochs))
    states = np.column_stack(
        (
            np.asarray(geocentric.position.km, dtype=float).T,
            np.asarray(geocentric.velocity.km_per_s, dtype=float).T,
        )
    )
    if cancel_check is not None and cancel_check():
        from propagator import PropagationCancelled
        raise PropagationCancelled("Propagation cancelled by user.")
    if progress_callback is not None:
        progress_callback(100)
    return output_times, states
