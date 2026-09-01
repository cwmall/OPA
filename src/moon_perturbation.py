import numpy as np

from constants import MU_MOON
from third_body import third_body_perturbation


# ============================================================
# MOON THIRD-BODY PERTURBATION
# ============================================================

def moon_perturbation(r_sat, r_moon):
    """
    Compute the Moon's third-body perturbation acceleration
    acting on an Earth-orbiting satellite.

    Parameters
    ----------
    r_sat : array_like
        Satellite position with respect to Earth's center.

        Units: km
        Frame: J2000

    r_moon : array_like
        Moon position with respect to Earth's center.

        Units: km
        Frame: J2000

    Returns
    -------
    numpy.ndarray
        Lunar third-body perturbation acceleration:

        [ax, ay, az]

        Units: km/s^2
        Frame: J2000

    Notes
    -----
    The acceleration is computed as:

        a_moon = mu_moon * (
            (r_moon - r_sat) / |r_moon - r_sat|^3
            -
            r_moon / |r_moon|^3
        )

    The first term is the Moon's gravitational acceleration
    acting on the satellite.

    The second term subtracts the Moon's gravitational
    acceleration acting on the Earth.

    This gives the differential (third-body) acceleration
    experienced by the satellite relative to Earth's center.
    """

    return third_body_perturbation(
        r_sat,
        r_moon,
        MU_MOON,
        body_name="Moon",
    )


# ============================================================
# MOON PERTURBATION MAGNITUDE
# ============================================================

def moon_perturbation_magnitude(r_sat, r_moon):
    """
    Return the magnitude of the Moon's third-body
    perturbation acceleration.

    Parameters
    ----------
    r_sat : array_like
        Satellite position [km], Earth-centered J2000.

    r_moon : array_like
        Moon position [km], Earth-centered J2000.

    Returns
    -------
    float
        Acceleration magnitude in km/s^2.
    """

    acceleration = moon_perturbation(
        r_sat,
        r_moon,
    )

    return float(
        np.linalg.norm(
            acceleration
        )
    )
