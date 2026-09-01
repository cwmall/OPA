import numpy as np
import spiceypy as spice

from spice_loader import load_kernels


# ============================================================
# CONSTANTS
# ============================================================

MOON_TARGET = "MOON"
SUN_TARGET = "SUN"
EARTH_OBSERVER = "EARTH"
REFERENCE_FRAME = "J2000"

# For force-model calculations we want the geometric
# position, not light-time / stellar-aberration corrected data.
ABERRATION_CORRECTION = "NONE"

# Occultation geometry is a different question from gravity. A photon that
# reaches the satellite passed the Moon while the Moon was where light-time
# correction places it, not where it is "now". The offset is about 19 arcsec,
# roughly 1% of the lunar apparent radius, which is worth several seconds on a
# lunar contact time. Stellar aberration is deliberately excluded: it changes
# the apparent direction of a source but not whether a body blocks the light.
OCCULTATION_ABERRATION_CORRECTION = "LT"


# ============================================================
# MOON POSITION
# ============================================================

def get_moon_position(et):
    """
    Return the Moon position with respect to Earth's center.

    Parameters
    ----------
    et : float
        SPICE Ephemeris Time, seconds past J2000.

    Returns
    -------
    numpy.ndarray
        Moon position vector:

        [x, y, z]

        Units: km
        Frame: J2000
        Origin: Earth center
    """

    load_kernels()

    state, _ = spice.spkezr(
        MOON_TARGET,
        float(et),
        REFERENCE_FRAME,
        ABERRATION_CORRECTION,
        EARTH_OBSERVER,
    )

    position = np.asarray(
        state[:3],
        dtype=float,
    )

    return position


def get_moon_position_apparent(et):
    """Return the light-time corrected Earth-to-Moon vector in J2000 [km].

    Use this for occultation and shadow geometry. ``get_moon_position`` stays
    geometric and remains the correct choice for third-body gravity.
    """

    load_kernels()

    state, _ = spice.spkezr(
        MOON_TARGET,
        float(et),
        REFERENCE_FRAME,
        OCCULTATION_ABERRATION_CORRECTION,
        EARTH_OBSERVER,
    )

    return np.asarray(
        state[:3],
        dtype=float,
    )


def get_sun_position(et):
    """Return the geometric Earth-to-Sun vector in J2000 [km]."""

    load_kernels()
    state, _ = spice.spkezr(
        SUN_TARGET,
        float(et),
        REFERENCE_FRAME,
        ABERRATION_CORRECTION,
        EARTH_OBSERVER,
    )
    return np.asarray(
        state[:3],
        dtype=float,
    )


# ============================================================
# MOON STATE
# ============================================================

def get_moon_state(et):
    """
    Return the Moon position and velocity with respect
    to Earth's center.

    Parameters
    ----------
    et : float
        SPICE Ephemeris Time, seconds past J2000.

    Returns
    -------
    numpy.ndarray
        State vector:

        [x, y, z, vx, vy, vz]

        Position units: km
        Velocity units: km/s
        Frame: J2000
        Origin: Earth center
    """

    load_kernels()

    state, _ = spice.spkezr(
        MOON_TARGET,
        float(et),
        REFERENCE_FRAME,
        ABERRATION_CORRECTION,
        EARTH_OBSERVER,
    )

    return np.asarray(
        state,
        dtype=float,
    )


# ============================================================
# EARTH-MOON DISTANCE
# ============================================================

def get_earth_moon_distance(et):
    """
    Return the instantaneous Earth-Moon center-to-center distance.

    Parameters
    ----------
    et : float
        SPICE Ephemeris Time.

    Returns
    -------
    float
        Earth-Moon distance in km.
    """

    moon_position = get_moon_position(
        et
    )

    return float(
        np.linalg.norm(
            moon_position
        )
    )
