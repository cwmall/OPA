import numpy as np

from earth_gravity import earth_gravity
from moon_perturbation import moon_perturbation
from sun_perturbation import sun_perturbation


def total_acceleration(r_sat, r_moon, r_sun=None):
    """
    Compute total acceleration acting on the satellite.

    Parameters
    ----------
    r_sat : ndarray
        Satellite position [km]

    r_moon : ndarray
        Moon position [km]

    Returns
    -------
    ndarray
        Total acceleration [km/s²]
    """

    a_earth = earth_gravity(r_sat)

    a_moon = moon_perturbation(r_sat, r_moon)

    acceleration = a_earth + a_moon
    if r_sun is not None:
        acceleration = acceleration + sun_perturbation(r_sat, r_sun)
    return acceleration
