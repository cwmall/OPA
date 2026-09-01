"""Reusable differential third-body gravity model.

All vectors are Earth-centred J2000 positions in kilometres.  The returned
acceleration is expressed in km/s^2.
"""

import numpy as np


def third_body_perturbation(
    r_sat,
    r_body,
    mu_body,
    body_name="Third body",
):
    """Return the body's differential acceleration on an Earth orbiter."""

    r_sat = np.asarray(r_sat, dtype=float)
    r_body = np.asarray(r_body, dtype=float)

    if r_sat.shape != (3,):
        raise ValueError("r_sat must be a 3-element position vector.")
    if r_body.shape != (3,):
        raise ValueError("r_body must be a 3-element position vector.")
    if not np.all(np.isfinite(r_sat)):
        raise ValueError("r_sat contains non-finite values.")
    if not np.all(np.isfinite(r_body)):
        raise ValueError("r_body contains non-finite values.")

    mu_body = float(mu_body)
    if not np.isfinite(mu_body) or mu_body <= 0.0:
        raise ValueError("mu_body must be finite and positive.")

    r_sat_to_body = r_body - r_sat
    distance_sat_to_body = float(np.linalg.norm(r_sat_to_body))
    distance_earth_to_body = float(np.linalg.norm(r_body))

    if distance_sat_to_body <= 0.0:
        raise ValueError(f"Satellite-{body_name} distance cannot be zero.")
    if distance_earth_to_body <= 0.0:
        raise ValueError(f"Earth-{body_name} distance cannot be zero.")

    return np.asarray(
        mu_body
        * (
            r_sat_to_body / distance_sat_to_body**3
            - r_body / distance_earth_to_body**3
        ),
        dtype=float,
    )
