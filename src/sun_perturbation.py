"""Solar third-body gravity for Earth-centred orbit propagation."""

import numpy as np

from constants import MU_SUN
from third_body import third_body_perturbation


def sun_perturbation(r_sat, r_sun):
    """Return the Sun's differential acceleration in J2000 [km/s^2]."""

    return third_body_perturbation(
        r_sat,
        r_sun,
        MU_SUN,
        body_name="Sun",
    )


def sun_perturbation_magnitude(r_sat, r_sun):
    """Return the solar third-body acceleration magnitude [km/s^2]."""

    return float(np.linalg.norm(sun_perturbation(r_sat, r_sun)))
