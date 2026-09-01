"""J2000 Cartesian states and classical osculating Keplerian elements.

The conversion uses the Earth-centred inertial position/velocity state and the
same EGM96 gravitational parameter used by the force model.  Returned angles
are normalized to [0, 360) degrees.  Circular/equatorial singularities are
reported explicitly instead of manufacturing an arbitrary angle.
"""

import numpy as np

from constants import MU_EARTH


_ANGLE_EPS = 1.0e-12


def _clamped_acos(value):
    return float(np.arccos(np.clip(float(value), -1.0, 1.0)))


def _angle_degrees(y, x):
    return float(np.degrees(np.arctan2(float(y), float(x))) % 360.0)


def cartesian_to_keplerian(state, mu=MU_EARTH):
    """Convert one inertial Cartesian state to osculating classical elements.

    Parameters
    ----------
    state : array-like, shape (6,)
        X, Y, Z [km] and Vx, Vy, Vz [km/s] in one Earth-centred inertial frame.
    mu : float
        Central-body GM [km^3/s^2]. Defaults to EGM96/WGS84 Earth GM.

    Returns
    -------
    dict
        ``a_km``, ``e``, ``i_deg``, ``raan_deg``, ``argp_deg``, ``nu_deg``
        plus singularity metadata. Undefined classical angles are ``None``.
    """

    values = np.asarray(state, dtype=np.float64)
    if values.shape != (6,) or not np.all(np.isfinite(values)):
        raise ValueError("state must contain six finite Cartesian values.")
    mu = float(mu)
    if not np.isfinite(mu) or mu <= 0.0:
        raise ValueError("mu must be a positive finite value.")

    r_vec = values[:3]
    v_vec = values[3:]
    radius = float(np.linalg.norm(r_vec))
    speed_squared = float(np.dot(v_vec, v_vec))
    if radius <= 0.0:
        raise ValueError("position magnitude must be greater than zero.")

    h_vec = np.cross(r_vec, v_vec)
    h = float(np.linalg.norm(h_vec))
    if h <= np.finfo(np.float64).eps * radius:
        raise ValueError("radial state has no well-defined orbital plane.")

    k_hat = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    n_vec = np.cross(k_hat, h_vec)
    n = float(np.linalg.norm(n_vec))
    eccentricity_vec = (
        ((speed_squared - mu / radius) * r_vec)
        - float(np.dot(r_vec, v_vec)) * v_vec
    ) / mu
    eccentricity = float(np.linalg.norm(eccentricity_vec))
    energy = 0.5 * speed_squared - mu / radius
    energy_tolerance = np.finfo(np.float64).eps * mu / radius * 64.0
    semi_major_axis = (
        float(np.inf)
        if abs(energy) <= energy_tolerance
        else float(-mu / (2.0 * energy))
    )
    inclination = float(np.degrees(_clamped_acos(h_vec[2] / h)))

    equatorial = n / h <= _ANGLE_EPS
    circular = eccentricity <= _ANGLE_EPS
    raan = None if equatorial else _angle_degrees(n_vec[1], n_vec[0])

    if circular:
        argument_of_periapsis = None
        if equatorial:
            # In a circular equatorial orbit only true longitude is defined.
            true_anomaly = _angle_degrees(r_vec[1], r_vec[0])
            anomaly_kind = "true_longitude"
        else:
            # Circular inclined orbit: argument of latitude replaces ν.
            cos_u = np.dot(n_vec, r_vec) / (n * radius)
            sin_u = np.dot(np.cross(n_vec, r_vec), h_vec) / (n * radius * h)
            true_anomaly = _angle_degrees(sin_u, cos_u)
            anomaly_kind = "argument_of_latitude"
    else:
        if equatorial:
            # Equatorial eccentric orbit: longitude of periapsis replaces ω.
            argument_of_periapsis = _angle_degrees(
                eccentricity_vec[1],
                eccentricity_vec[0],
            )
            periapsis_kind = "longitude_of_periapsis"
        else:
            cos_argp = np.dot(n_vec, eccentricity_vec) / (n * eccentricity)
            sin_argp = (
                np.dot(np.cross(n_vec, eccentricity_vec), h_vec)
                / (n * eccentricity * h)
            )
            argument_of_periapsis = _angle_degrees(sin_argp, cos_argp)
            periapsis_kind = "argument_of_periapsis"

        cos_nu = np.dot(eccentricity_vec, r_vec) / (eccentricity * radius)
        sin_nu = (
            np.dot(np.cross(eccentricity_vec, r_vec), h_vec)
            / (eccentricity * radius * h)
        )
        true_anomaly = _angle_degrees(sin_nu, cos_nu)
        anomaly_kind = "true_anomaly"

    if circular:
        periapsis_kind = "undefined_circular"

    return {
        "a_km": semi_major_axis,
        "e": eccentricity,
        "i_deg": inclination,
        "raan_deg": raan,
        "argp_deg": argument_of_periapsis,
        "nu_deg": true_anomaly,
        "equatorial": equatorial,
        "circular": circular,
        "periapsis_kind": periapsis_kind,
        "anomaly_kind": anomaly_kind,
        "eccentricity_vector": eccentricity_vec,
        "angular_momentum_vector": h_vec,
    }


def keplerian_to_cartesian(elements, mu=MU_EARTH):
    """Convert nonsingular elliptic classical elements to Cartesian state.

    This inverse is primarily provided for independent round-trip verification
    of the forward conversion. Angles are expected in degrees.
    """

    mu = float(mu)
    a = float(elements["a_km"])
    e = float(elements["e"])
    inclination = np.radians(float(elements["i_deg"]))
    raan = np.radians(float(elements["raan_deg"]))
    argp = np.radians(float(elements["argp_deg"]))
    nu = np.radians(float(elements["nu_deg"]))
    if not (np.isfinite(a) and a > 0.0 and 0.0 <= e < 1.0):
        raise ValueError("inverse conversion requires an elliptic orbit.")

    p = a * (1.0 - e * e)
    radius_pf = p / (1.0 + e * np.cos(nu))
    r_pf = np.array(
        [radius_pf * np.cos(nu), radius_pf * np.sin(nu), 0.0],
        dtype=np.float64,
    )
    v_pf = np.sqrt(mu / p) * np.array(
        [-np.sin(nu), e + np.cos(nu), 0.0],
        dtype=np.float64,
    )

    cos_o, sin_o = np.cos(raan), np.sin(raan)
    cos_i, sin_i = np.cos(inclination), np.sin(inclination)
    cos_w, sin_w = np.cos(argp), np.sin(argp)
    rotation = np.array(
        [
            [cos_o * cos_w - sin_o * sin_w * cos_i,
             -cos_o * sin_w - sin_o * cos_w * cos_i,
             sin_o * sin_i],
            [sin_o * cos_w + cos_o * sin_w * cos_i,
             -sin_o * sin_w + cos_o * cos_w * cos_i,
             -cos_o * sin_i],
            [sin_w * sin_i, cos_w * sin_i, cos_i],
        ],
        dtype=np.float64,
    )
    return np.concatenate((rotation @ r_pf, rotation @ v_pf))
