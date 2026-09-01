from math import factorial

import numpy as np

from constants import (
    C22_EARTH,
    DELTA_T_TT_UT1,
    MU_EARTH,
    R_EARTH,
    J2_EARTH,
    S22_EARTH,
)
from earth_orientation import (
    is_eop_enabled,
    j2000_to_itrs_rotation_from_tt_jd,
    skyfield_time_from_tt_jd,
)
from egm96_coefficients import (
    EGM96_MAX_DEGREE,
    EGM96_NORMALIZED_COEFFICIENTS,
)


def _coefficient_normalization(degree, order):
    """Return the geodetic full-normalization factor for P_nm."""

    order_factor = 1.0 if order == 0 else 2.0
    return np.sqrt(
        (2.0 * degree + 1.0)
        * order_factor
        * factorial(degree - order)
        / factorial(degree + order)
    )


EGM96_UNNORMALIZED_C = np.zeros(
    (EGM96_MAX_DEGREE + 1, EGM96_MAX_DEGREE + 1),
    dtype=float,
)
EGM96_UNNORMALIZED_S = np.zeros_like(EGM96_UNNORMALIZED_C)
for (_degree, _order), (_c_bar, _s_bar) in (
    EGM96_NORMALIZED_COEFFICIENTS.items()
):
    _normalization = _coefficient_normalization(_degree, _order)
    EGM96_UNNORMALIZED_C[_degree, _order] = _c_bar * _normalization
    EGM96_UNNORMALIZED_S[_degree, _order] = _s_bar * _normalization


_J2000_TT_JULIAN_DATE = 2451545.0


# ============================================================
# POSITION VALIDATION
# ============================================================

def _validate_position(r_sat):
    """
    Validate a satellite position vector.

    Parameters
    ----------
    r_sat : array_like
        Earth-centered satellite position [km].

    Returns
    -------
    numpy.ndarray
        Three-element position vector.
    """

    r_sat = np.asarray(
        r_sat,
        dtype=float,
    )

    if r_sat.shape != (3,):
        raise ValueError(
            "r_sat must be a 3-element position vector."
        )

    if not np.all(
        np.isfinite(r_sat)
    ):
        raise ValueError(
            "r_sat contains non-finite values."
        )

    r = float(
        np.linalg.norm(
            r_sat
        )
    )

    if r <= 0.0:
        raise ValueError(
            "Satellite position magnitude must be greater than zero."
        )

    return r_sat


# ============================================================
# CENTRAL EARTH GRAVITY
# ============================================================

def earth_point_mass(r_sat):
    """
    Compute Earth's central point-mass gravity.

    Parameters
    ----------
    r_sat : array_like
        Earth-centered satellite position [km].

    Returns
    -------
    numpy.ndarray
        Acceleration [km/s^2].
    """

    r_sat = _validate_position(
        r_sat
    )

    r = float(
        np.linalg.norm(
            r_sat
        )
    )

    return (
        -MU_EARTH
        * r_sat
        / r**3
    )


# ============================================================
# J2 PERTURBATION
# ============================================================

def earth_j2(r_sat):
    """
    Compute Earth's J2 perturbing acceleration.

    Parameters
    ----------
    r_sat : array_like
        Earth-centered satellite position [km].

    Returns
    -------
    numpy.ndarray
        J2 acceleration [km/s^2].

    Notes
    -----
    This is the J2-only perturbation.

    For the current baseline propagator, the inertial z-axis
    is treated as aligned with Earth's reference symmetry axis.

    A future high-fidelity version can transform the state
    through an Earth-fixed frame before evaluating a complete
    spherical-harmonic gravity model.
    """

    r_sat = _validate_position(
        r_sat
    )

    x = float(r_sat[0])
    y = float(r_sat[1])
    z = float(r_sat[2])

    r2 = (
        x * x
        + y * y
        + z * z
    )

    r = np.sqrt(
        r2
    )

    z2 = (
        z * z
    )

    common = (
        1.5
        * J2_EARTH
        * MU_EARTH
        * R_EARTH**2
        / r**5
    )

    ratio = (
        z2
        / r2
    )

    ax = (
        common
        * x
        * (
            5.0 * ratio
            - 1.0
        )
    )

    ay = (
        common
        * y
        * (
            5.0 * ratio
            - 1.0
        )
    )

    az = (
        common
        * z
        * (
            5.0 * ratio
            - 3.0
        )
    )

    return np.array(
        [
            ax,
            ay,
            az,
        ],
        dtype=float,
    )


# ============================================================
# EARTH ROTATION AND C22/S22 TESSELLAR GRAVITY
# ============================================================

def earth_rotation_angle(et):
    """Return approximate Greenwich sidereal angle [rad] for SPICE ET."""

    et = float(et)
    if not np.isfinite(et):
        raise ValueError("et must be finite.")

    if is_eop_enabled():
        skyfield_time = skyfield_time_from_tt_jd(
            _J2000_TT_JULIAN_DATE + et / 86400.0
        )
        return float(np.radians((float(skyfield_time.gmst) * 15.0) % 360.0))

    # GMST is referenced to J2000 UT1, while SPICE ET is effectively
    # TDB seconds past J2000. TT-TDB is millisecond-scale; TT-UT1 is
    # the material correction for this degree-2 model.
    days_ut1_from_j2000 = (
        et - DELTA_T_TT_UT1
    ) / 86400.0
    degrees = (
        280.46061837
        + 360.98564736629 * days_ut1_from_j2000
    )
    return float(np.radians(degrees % 360.0))


def _validate_harmonic_degree(max_degree):
    max_degree = int(max_degree)
    if max_degree < 2 or max_degree > EGM96_MAX_DEGREE:
        raise ValueError(
            f"max_degree must be between 2 and {EGM96_MAX_DEGREE}."
        )
    return max_degree


def _legendre_and_latitude_derivative(
    sin_latitude,
    cos_latitude,
    max_degree,
):
    """Return unnormalized P_nm and dP_nm/d(latitude), without phase."""

    p = np.zeros((max_degree + 1, max_degree + 1), dtype=float)
    dp = np.zeros_like(p)
    p[0, 0] = 1.0

    for order in range(1, max_degree + 1):
        factor = 2.0 * order - 1.0
        p[order, order] = (
            factor * cos_latitude * p[order - 1, order - 1]
        )
        dp[order, order] = factor * (
            -sin_latitude * p[order - 1, order - 1]
            + cos_latitude * dp[order - 1, order - 1]
        )

    for order in range(0, max_degree):
        degree = order + 1
        factor = 2.0 * order + 1.0
        p[degree, order] = factor * sin_latitude * p[order, order]
        dp[degree, order] = factor * (
            cos_latitude * p[order, order]
            + sin_latitude * dp[order, order]
        )

    for order in range(0, max_degree + 1):
        for degree in range(order + 2, max_degree + 1):
            denominator = float(degree - order)
            previous_factor = degree + order - 1.0
            p[degree, order] = (
                (2.0 * degree - 1.0)
                * sin_latitude
                * p[degree - 1, order]
                - previous_factor * p[degree - 2, order]
            ) / denominator
            dp[degree, order] = (
                (2.0 * degree - 1.0)
                * (
                    cos_latitude * p[degree - 1, order]
                    + sin_latitude * dp[degree - 1, order]
                )
                - previous_factor * dp[degree - 2, order]
            ) / denominator

    return p, dp


def earth_harmonic_potential_fixed(r_fixed, max_degree=4):
    """Return the EGM96 degree 2..N perturbing potential [km^2/s^2]."""

    r_fixed = _validate_position(r_fixed)
    max_degree = _validate_harmonic_degree(max_degree)
    x, y, z = r_fixed
    radius = float(np.linalg.norm(r_fixed))
    horizontal = float(np.hypot(x, y))
    sin_latitude = float(z / radius)
    cos_latitude = float(horizontal / radius)
    longitude = float(np.arctan2(y, x)) if horizontal > 0.0 else 0.0
    p, _ = _legendre_and_latitude_derivative(
        sin_latitude,
        cos_latitude,
        max_degree,
    )

    total = 0.0
    radius_ratio = R_EARTH / radius
    for degree in range(2, max_degree + 1):
        degree_sum = 0.0
        for order in range(0, degree + 1):
            angle = order * longitude
            harmonic = (
                EGM96_UNNORMALIZED_C[degree, order] * np.cos(angle)
                + EGM96_UNNORMALIZED_S[degree, order] * np.sin(angle)
            )
            degree_sum += p[degree, order] * harmonic
        total += radius_ratio**degree * degree_sum

    return float(MU_EARTH / radius * total)


def earth_harmonic_acceleration_fixed(r_fixed, max_degree=4):
    """Return EGM96 degree 2..N acceleration in Earth-fixed axes."""

    r_fixed = _validate_position(r_fixed)
    max_degree = _validate_harmonic_degree(max_degree)
    x, y, z = r_fixed
    radius = float(np.linalg.norm(r_fixed))
    horizontal = float(np.hypot(x, y))

    # The production orbit is near-equatorial. This fallback keeps the
    # general function finite at the coordinate singularity on the poles.
    if horizontal <= radius * 1.0e-12:
        step = max(1.0e-3, radius * 1.0e-7)
        acceleration = np.empty(3, dtype=float)
        for axis in range(3):
            offset = np.zeros(3, dtype=float)
            offset[axis] = step
            acceleration[axis] = (
                earth_harmonic_potential_fixed(
                    r_fixed + offset,
                    max_degree,
                )
                - earth_harmonic_potential_fixed(
                    r_fixed - offset,
                    max_degree,
                )
            ) / (2.0 * step)
        return acceleration

    sin_latitude = float(z / radius)
    cos_latitude = float(horizontal / radius)
    longitude = float(np.arctan2(y, x))
    p, dp = _legendre_and_latitude_derivative(
        sin_latitude,
        cos_latitude,
        max_degree,
    )

    radial_sum = 0.0
    latitude_sum = 0.0
    longitude_sum = 0.0
    radius_ratio = R_EARTH / radius
    for degree in range(2, max_degree + 1):
        degree_radial = 0.0
        degree_latitude = 0.0
        degree_longitude = 0.0
        for order in range(0, degree + 1):
            angle = order * longitude
            cos_angle = np.cos(angle)
            sin_angle = np.sin(angle)
            c_nm = EGM96_UNNORMALIZED_C[degree, order]
            s_nm = EGM96_UNNORMALIZED_S[degree, order]
            harmonic = c_nm * cos_angle + s_nm * sin_angle
            degree_radial += p[degree, order] * harmonic
            degree_latitude += dp[degree, order] * harmonic
            degree_longitude += (
                p[degree, order]
                * order
                * (-c_nm * sin_angle + s_nm * cos_angle)
            )

        scale = radius_ratio**degree
        radial_sum += (degree + 1.0) * scale * degree_radial
        latitude_sum += scale * degree_latitude
        longitude_sum += scale * degree_longitude

    common = MU_EARTH / radius**2
    acceleration_radial = -common * radial_sum
    acceleration_latitude = common * latitude_sum
    acceleration_longitude = (
        common * longitude_sum / cos_latitude
    )

    cos_longitude = np.cos(longitude)
    sin_longitude = np.sin(longitude)
    radial_hat = np.array(
        [
            cos_latitude * cos_longitude,
            cos_latitude * sin_longitude,
            sin_latitude,
        ]
    )
    latitude_hat = np.array(
        [
            -sin_latitude * cos_longitude,
            -sin_latitude * sin_longitude,
            cos_latitude,
        ]
    )
    longitude_hat = np.array(
        [-sin_longitude, cos_longitude, 0.0]
    )
    return (
        acceleration_radial * radial_hat
        + acceleration_latitude * latitude_hat
        + acceleration_longitude * longitude_hat
    )


def earth_harmonics_egm96(r_sat, et, max_degree=4):
    """Return EGM96 degree 2..N acceleration in inertial J2000 axes."""

    r_sat = _validate_position(r_sat)
    max_degree = _validate_harmonic_degree(max_degree)
    et = float(et)
    if not np.isfinite(et):
        raise ValueError("et must be finite.")

    # EGM96 coefficients are defined in Earth-fixed axes.  A Greenwich-only
    # z rotation incorrectly assumes that the terrestrial pole is identical
    # to J2000's z axis.  ITRS supplies the full precession/nutation and Earth
    # rotation orientation.  Polar motion remains zero unless an explicit
    # Earth-orientation table is loaded, which keeps offline runs repeatable.
    j2000_to_itrs = j2000_to_itrs_rotation_from_tt_jd(
        _J2000_TT_JULIAN_DATE + et / 86400.0
    )
    r_fixed = j2000_to_itrs @ r_sat
    acceleration_fixed = earth_harmonic_acceleration_fixed(
        r_fixed,
        max_degree=max_degree,
    )
    return np.asarray(j2000_to_itrs.T @ acceleration_fixed, dtype=float)


def earth_tesseral_22(r_sat, et):
    """Return Earth's unnormalized C22/S22 acceleration in J2000.

    The inertial position is rotated into an Earth-fixed frame, the
    gradient of the degree-2/order-2 potential is evaluated there, and
    the acceleration is rotated back to J2000. Units are km/s^2.
    """

    r_sat = _validate_position(r_sat)
    if is_eop_enabled():
        j2000_to_itrs = j2000_to_itrs_rotation_from_tt_jd(
            _J2000_TT_JULIAN_DATE + float(et) / 86400.0
        )
        x, y, z = j2000_to_itrs @ r_sat
        cos_theta = sin_theta = None
    else:
        theta = earth_rotation_angle(et)
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)

        # J2000 -> rotating Earth-fixed axes.
        x = r_sat[0] * cos_theta + r_sat[1] * sin_theta
        y = -r_sat[0] * sin_theta + r_sat[1] * cos_theta
        z = float(r_sat[2])

    r2 = x * x + y * y + z * z
    r = np.sqrt(r2)
    r5 = r2 * r2 * r
    r7 = r5 * r2
    common = 3.0 * MU_EARTH * R_EARTH**2
    harmonic = (
        C22_EARTH * (x * x - y * y)
        + 2.0 * S22_EARTH * x * y
    )

    ax_fixed = common * (
        (2.0 * C22_EARTH * x + 2.0 * S22_EARTH * y) / r5
        - 5.0 * harmonic * x / r7
    )
    ay_fixed = common * (
        (-2.0 * C22_EARTH * y + 2.0 * S22_EARTH * x) / r5
        - 5.0 * harmonic * y / r7
    )
    az_fixed = common * (-5.0 * harmonic * z / r7)

    if is_eop_enabled():
        return np.asarray(
            j2000_to_itrs.T
            @ np.array([ax_fixed, ay_fixed, az_fixed], dtype=float),
            dtype=float,
        )

    # Earth-fixed -> J2000 (legacy Greenwich-only OFF mode).
    return np.array(
        [
            ax_fixed * cos_theta - ay_fixed * sin_theta,
            ax_fixed * sin_theta + ay_fixed * cos_theta,
            az_fixed,
        ],
        dtype=float,
    )


# ============================================================
# TOTAL EARTH GRAVITY
# ============================================================

def earth_gravity(
    r_sat,
    include_j2=True,
    et=None,
    include_tesseral=False,
    harmonic_degree=None,
):
    """
    Compute Earth gravitational acceleration.

    Parameters
    ----------
    r_sat : array_like
        Earth-centered satellite position [km].

    include_j2 : bool
        Include J2 perturbation when True.

    et : float or None
        SPICE Ephemeris Time. Required when ``include_tesseral`` is True.

    include_tesseral : bool
        Include Earth's C22/S22 equatorial ellipticity terms.

    harmonic_degree : int or None
        When set, use the complete EGM96 field from degree 2 through this
        degree. This replaces the separate J2 and C22/S22 additions.

    Returns
    -------
    numpy.ndarray
        Earth acceleration [km/s^2].
    """

    acceleration = earth_point_mass(
        r_sat
    )

    if harmonic_degree is not None:
        if et is None:
            raise ValueError(
                "et is required when harmonic_degree is set."
            )
        acceleration = acceleration + earth_harmonics_egm96(
            r_sat,
            et,
            max_degree=harmonic_degree,
        )
        return np.asarray(acceleration, dtype=float)

    if include_j2:
        acceleration = (
            acceleration
            + earth_j2(
                r_sat
            )
        )

    if include_tesseral:
        if et is None:
            raise ValueError(
                "et is required when include_tesseral is True."
            )
        acceleration = acceleration + earth_tesseral_22(
            r_sat,
            et,
        )

    return np.asarray(
        acceleration,
        dtype=float,
    )


# ============================================================
# MAGNITUDE
# ============================================================

def earth_gravity_magnitude(
    r_sat,
    include_j2=True,
):
    """
    Return Earth gravity acceleration magnitude [km/s^2].
    """

    acceleration = earth_gravity(
        r_sat,
        include_j2=include_j2,
    )

    return float(
        np.linalg.norm(
            acceleration
        )
    )
