"""Generic box-wing and effective-area solar-radiation-pressure models."""

from datetime import datetime
import math

import numpy as np

from constants import (
    EARTH_POLAR_RADIUS_KM,
    ASTRONOMICAL_UNIT_KM,
    DEMO_SPACECRAFT_BODY_ABSORPTION,
    DEMO_SPACECRAFT_BODY_DIFFUSE,
    DEMO_SPACECRAFT_BODY_SPECULAR,
    DEMO_SPACECRAFT_BODY_X_M,
    DEMO_SPACECRAFT_BODY_Y_M,
    DEMO_SPACECRAFT_BODY_Z_M,
    DEMO_SPACECRAFT_MASS_KG,
    DEMO_SPACECRAFT_SOLAR_ARRAY_ABSORPTION,
    DEMO_SPACECRAFT_SOLAR_ARRAY_DIFFUSE,
    DEMO_SPACECRAFT_SOLAR_ARRAY_SPECULAR,
    DEMO_SPACECRAFT_TOTAL_SOLAR_ARRAY_AREA_M2,
    R_EARTH,
    SOLAR_PRESSURE_1_AU_N_M2,
    SUN_MEAN_RADIUS_KM,
)


def _validate_optical_fractions(absorption, specular, diffuse, label):
    """Səthin enerji paylarının fiziki olaraq vahidə bərabərliyini yoxla."""

    values = np.asarray([absorption, specular, diffuse], dtype=float)
    if np.any(values < 0.0) or not np.all(np.isfinite(values)):
        raise ValueError(f"{label} optical fractions are invalid.")
    if not np.isclose(float(np.sum(values)), 1.0, atol=1.0e-12):
        raise ValueError(f"{label} optical fractions must sum to one.")


def _flat_surface_force_per_pressure(
    photon_direction,
    sun_facing_normal,
    area_m2,
    specular,
    diffuse,
):
    """Bir səthin P-yə bölünmüş radiasiya qüvvəsini [m²] qaytar.

    ``photon_direction`` Günəşdən peykə, ``sun_facing_normal`` isə səthdən
    Günəşə yönəlir. Nəticədə udulma, güzgü və Lambert diffuz əksolunması
    ayrıca nəzərə alınır.
    """

    photon_direction = np.asarray(photon_direction, dtype=float)
    normal = np.asarray(sun_facing_normal, dtype=float)
    incidence = float(np.dot(-photon_direction, normal))
    if incidence <= 0.0:
        return np.zeros(3, dtype=float)
    return area_m2 * incidence * (
        (1.0 - specular) * photon_direction
        - 2.0 * specular * incidence * normal
        - (2.0 / 3.0) * diffuse * normal
    )


def _earth_pointing_body_axes(r_sat):
    """Earth-pointing GEO gövdəsi üçün sağəlli SCBx/SCBy/SCBz oxları qur."""

    nadir = -np.asarray(r_sat, dtype=float)
    nadir /= np.linalg.norm(nadir)
    earth_north = np.array([0.0, 0.0, 1.0], dtype=float)
    body_y = earth_north - np.dot(earth_north, nadir) * nadir
    body_y_norm = float(np.linalg.norm(body_y))
    if body_y_norm <= 1.0e-12:
        body_y = np.array([0.0, 1.0, 0.0], dtype=float)
    else:
        body_y /= body_y_norm
    body_z = nadir
    body_x = np.cross(body_y, body_z)
    body_x /= np.linalg.norm(body_x)
    return body_x, body_y, body_z


def _box_wing_force_per_pressure(r_sat, photon_direction):
    """Şəkildə verilmiş panel və prizma gövdənin P-siz SRP qüvvəsini qaytar."""

    _validate_optical_fractions(
        DEMO_SPACECRAFT_SOLAR_ARRAY_ABSORPTION,
        DEMO_SPACECRAFT_SOLAR_ARRAY_SPECULAR,
        DEMO_SPACECRAFT_SOLAR_ARRAY_DIFFUSE,
        "Solar-array",
    )
    _validate_optical_fractions(
        DEMO_SPACECRAFT_BODY_ABSORPTION,
        DEMO_SPACECRAFT_BODY_SPECULAR,
        DEMO_SPACECRAFT_BODY_DIFFUSE,
        "Spacecraft-body",
    )

    # TrueSun: hər iki panelin işıqlanan normalı dəqiq Günəşə baxır.
    force = _flat_surface_force_per_pressure(
        photon_direction,
        -photon_direction,
        DEMO_SPACECRAFT_TOTAL_SOLAR_ARRAY_AREA_M2,
        DEMO_SPACECRAFT_SOLAR_ARRAY_SPECULAR,
        DEMO_SPACECRAFT_SOLAR_ARRAY_DIFFUSE,
    )

    body_x, body_y, body_z = _earth_pointing_body_axes(r_sat)
    body_faces = (
        (body_x, DEMO_SPACECRAFT_BODY_Y_M * DEMO_SPACECRAFT_BODY_Z_M),
        (-body_x, DEMO_SPACECRAFT_BODY_Y_M * DEMO_SPACECRAFT_BODY_Z_M),
        (body_y, DEMO_SPACECRAFT_BODY_X_M * DEMO_SPACECRAFT_BODY_Z_M),
        (-body_y, DEMO_SPACECRAFT_BODY_X_M * DEMO_SPACECRAFT_BODY_Z_M),
        (body_z, DEMO_SPACECRAFT_BODY_X_M * DEMO_SPACECRAFT_BODY_Y_M),
        (-body_z, DEMO_SPACECRAFT_BODY_X_M * DEMO_SPACECRAFT_BODY_Y_M),
    )
    for normal, area_m2 in body_faces:
        force += _flat_surface_force_per_pressure(
            photon_direction,
            normal,
            area_m2,
            DEMO_SPACECRAFT_BODY_SPECULAR,
            DEMO_SPACECRAFT_BODY_DIFFUSE,
        )
    return np.asarray(force, dtype=float)


def solar_pressure_coefficient_for_epoch(epoch):
    """Return the transparent public-mode SRP coefficient.

    Public mode deliberately carries no spacecraft calibration table.  The
    neutral coefficient keeps the physical model available for synthetic and
    user-created profiles without embedding mission-specific values.
    """

    if not isinstance(epoch, datetime):
        raise TypeError("epoch must be a datetime object.")
    return 1.0


def resolved_solar_pressure_coefficient(epoch):
    """Return the neutral coefficient and an explicit public-mode label."""

    return solar_pressure_coefficient_for_epoch(epoch), "NOMINAL / PUBLIC DEMO"


def _disc_overlap_area(radius_1, radius_2, separation):
    """Bucaq radiuslu iki dairənin üst-üstə düşən sahəsini hesabla."""

    if separation >= radius_1 + radius_2:
        return 0.0
    if separation <= abs(radius_1 - radius_2):
        return math.pi * min(radius_1, radius_2) ** 2

    cosine_1 = np.clip(
        (separation**2 + radius_1**2 - radius_2**2)
        / (2.0 * separation * radius_1),
        -1.0,
        1.0,
    )
    cosine_2 = np.clip(
        (separation**2 + radius_2**2 - radius_1**2)
        / (2.0 * separation * radius_2),
        -1.0,
        1.0,
    )
    triangle_term = max(
        0.0,
        (-separation + radius_1 + radius_2)
        * (separation + radius_1 - radius_2)
        * (separation - radius_1 + radius_2)
        * (separation + radius_1 + radius_2),
    )
    return (
        radius_1**2 * math.acos(float(cosine_1))
        + radius_2**2 * math.acos(float(cosine_2))
        - 0.5 * math.sqrt(triangle_term)
    )


def _oblate_silhouette_radius_km(
    line_of_sight,
    sun_direction,
    equatorial_radius_km,
    polar_radius_km,
):
    """Return the occulting body's limb radius toward the Sun's sky offset.

    An oblate body projects an ellipse, not a circle. Contact timing depends on
    where the limb sits along the direction the Sun is offset from the body
    centre, so that is the radius returned here. The illumination fraction
    still treats the silhouette as a circle of this radius, which is exact at
    the contacts and a close approximation in between.
    """

    equatorial_radius_km = float(equatorial_radius_km)
    polar_radius_km = float(polar_radius_km)
    if polar_radius_km <= 0.0 or polar_radius_km == equatorial_radius_km:
        return equatorial_radius_km

    pole = np.array([0.0, 0.0, 1.0])
    cosine_tilt = float(np.clip(abs(np.dot(line_of_sight, pole)), 0.0, 1.0))
    sine_tilt_squared = max(0.0, 1.0 - cosine_tilt**2)

    # Semi-axis along the projected polar direction; the perpendicular
    # semi-axis is always the equatorial radius.
    polar_semi_axis = math.sqrt(
        equatorial_radius_km**2 * cosine_tilt**2
        + polar_radius_km**2 * sine_tilt_squared
    )

    pole_in_sky = pole - np.dot(pole, line_of_sight) * line_of_sight
    pole_in_sky_norm = float(np.linalg.norm(pole_in_sky))
    if pole_in_sky_norm <= 1.0e-12:
        # Viewed along the pole the silhouette is a circle.
        return equatorial_radius_km
    polar_axis_direction = pole_in_sky / pole_in_sky_norm
    equatorial_axis_direction = np.cross(line_of_sight, polar_axis_direction)

    sun_in_sky = (
        sun_direction - np.dot(sun_direction, line_of_sight) * line_of_sight
    )
    sun_in_sky_norm = float(np.linalg.norm(sun_in_sky))
    if sun_in_sky_norm <= 1.0e-12:
        # Sun exactly behind the body centre; the disc is fully covered and the
        # limb direction is undefined.
        return equatorial_radius_km
    sun_in_sky = sun_in_sky / sun_in_sky_norm

    cosine_offset = float(np.dot(sun_in_sky, equatorial_axis_direction))
    sine_offset = float(np.dot(sun_in_sky, polar_axis_direction))

    return float(
        equatorial_radius_km
        * polar_semi_axis
        / math.hypot(
            polar_semi_axis * cosine_offset,
            equatorial_radius_km * sine_offset,
        )
    )


def solar_occultation_geometry(r_sat, r_sun, *, oblate_earth=False):
    """Günəş/Yer görünən disklərinin bucaq geometriyasını [rad] qaytar.

    Nəticə ``(sun_radius, earth_radius, separation)`` şəklindədir. ``separation``
    peykdən baxdıqda Günəş və Yer disk mərkəzləri arasındakı bucaqdır.
    """

    return occulting_body_geometry(
        r_sat,
        r_sun,
        np.zeros(3, dtype=float),
        R_EARTH,
        body_polar_radius_km=(
            EARTH_POLAR_RADIUS_KM if oblate_earth else None
        ),
    )


def occulting_body_geometry(
    r_sat,
    r_sun,
    r_body,
    body_radius_km,
    body_polar_radius_km=None,
):
    """Return apparent Sun/body radii and separation as seen by a satellite.

    ``body_polar_radius_km`` makes the occulting body an oblate spheroid. It is
    supplied for the Earth and left out for the Moon, whose flattening is
    negligible at these distances.
    """

    r_sat = np.asarray(r_sat, dtype=float)
    r_sun = np.asarray(r_sun, dtype=float)
    r_body = np.asarray(r_body, dtype=float)
    body_radius_km = float(body_radius_km)
    sat_to_sun = r_sun - r_sat
    sat_to_body = r_body - r_sat
    sun_distance = float(np.linalg.norm(sat_to_sun))
    body_distance = float(np.linalg.norm(sat_to_body))
    if sun_distance <= SUN_MEAN_RADIUS_KM:
        raise ValueError("Satellite-Sun distance is invalid for SRP.")
    if not np.isfinite(body_radius_km) or body_radius_km <= 0.0:
        raise ValueError("Occulting-body radius must be finite and positive.")
    if body_distance <= body_radius_km:
        raise ValueError("Satellite is at or below the occulting-body surface.")

    sun_radius = math.asin(SUN_MEAN_RADIUS_KM / sun_distance)
    if body_polar_radius_km is None:
        effective_body_radius_km = body_radius_km
    else:
        effective_body_radius_km = _oblate_silhouette_radius_km(
            sat_to_body / body_distance,
            sat_to_sun / sun_distance,
            body_radius_km,
            body_polar_radius_km,
        )
    body_radius = math.asin(effective_body_radius_km / body_distance)
    # atan2(|a x b|, a · b) keeps small apparent separations accurate.  The
    # former acos(cosine) form loses significant digits when the Sun and the
    # occulting body are nearly aligned, exactly where eclipse contacts occur.
    cross_norm = float(np.linalg.norm(np.cross(sat_to_sun, sat_to_body)))
    dot_product = float(np.dot(sat_to_sun, sat_to_body))
    separation = math.atan2(cross_norm, dot_product)
    return float(sun_radius), float(body_radius), float(separation)


def sunlight_fraction(r_sat, r_sun, *, oblate_earth=False):
    """Yer diskinin Günəş diskini örtməsinə görə 0..1 işıqlanmanı qaytar."""

    sun_radius, earth_radius, separation = solar_occultation_geometry(
        r_sat,
        r_sun,
        oblate_earth=oblate_earth,
    )
    overlap = _disc_overlap_area(sun_radius, earth_radius, separation)
    fraction = 1.0 - overlap / (math.pi * sun_radius**2)
    return float(np.clip(fraction, 0.0, 1.0))


def occulting_body_sunlight_fraction(
    r_sat,
    r_sun,
    r_body,
    body_radius_km,
):
    """Return visible Sun fraction after occultation by an arbitrary body."""

    sun_radius, body_radius, separation = occulting_body_geometry(
        r_sat,
        r_sun,
        r_body,
        body_radius_km,
    )
    overlap = _disc_overlap_area(sun_radius, body_radius, separation)
    fraction = 1.0 - overlap / (math.pi * sun_radius**2)
    return float(np.clip(fraction, 0.0, 1.0))


def resolve_effective_area_srp_inputs(
    *,
    mode,
    mass_kg,
    total_area_m2=None,
    coefficient=None,
    panel_area_m2=None,
    panel_coefficient=None,
    body_area_m2=None,
    body_coefficient=None,
):
    """Validate manual SRP inputs and return one equivalent cannonball model.

    The panel/body form is mathematically identical to summing two illuminated
    effective-area forces because both contributions share the same photon
    direction and shadow fraction.  Keeping this reduction here ensures every
    UI module uses the same area-weighted coefficient.
    """

    def finite(value, label, *, positive=False, nonnegative=False):
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} must be numeric.") from error
        if not math.isfinite(number):
            raise ValueError(f"{label} must be finite.")
        if positive and number <= 0.0:
            raise ValueError(f"{label} must be greater than zero.")
        if nonnegative and number < 0.0:
            raise ValueError(f"{label} cannot be negative.")
        return number

    resolved_mass_kg = finite(mass_kg, "SRP mass", positive=True)
    selected_mode = str(mode or "combined").strip().lower()
    if selected_mode == "combined":
        resolved_area_m2 = finite(
            total_area_m2,
            "SRP effective area",
            positive=True,
        )
        resolved_coefficient = finite(
            coefficient,
            "SRP coefficient",
            positive=True,
        )
        return {
            "mode": "combined",
            "mode_label": "MANUAL / COMBINED",
            "mass_kg": resolved_mass_kg,
            "area_m2": resolved_area_m2,
            "coefficient": resolved_coefficient,
            "components": (),
        }

    if selected_mode != "panel_body":
        raise ValueError("Unknown manual SRP input mode.")
    resolved_panel_area_m2 = finite(
        panel_area_m2,
        "SRP panel area",
        nonnegative=True,
    )
    if total_area_m2 is None:
        # Retain compatibility with older project payloads while new UI paths
        # always supply total area and derive the body contribution from it.
        resolved_body_area_m2 = finite(
            body_area_m2,
            "SRP body area",
            nonnegative=True,
        )
        resolved_area_m2 = resolved_panel_area_m2 + resolved_body_area_m2
    else:
        resolved_area_m2 = finite(
            total_area_m2,
            "SRP total area",
            positive=True,
        )
        if resolved_panel_area_m2 > resolved_area_m2:
            raise ValueError("SRP panel area cannot exceed total area.")
        resolved_body_area_m2 = resolved_area_m2 - resolved_panel_area_m2
    if resolved_area_m2 <= 0.0:
        raise ValueError("SRP panel and body areas cannot both be zero.")
    resolved_panel_coefficient = finite(
        panel_coefficient,
        "SRP panel coefficient",
        positive=True,
    )
    resolved_body_coefficient = finite(
        body_coefficient,
        "SRP body coefficient",
        positive=True,
    )
    resolved_coefficient = (
        resolved_panel_area_m2 * resolved_panel_coefficient
        + resolved_body_area_m2 * resolved_body_coefficient
    ) / resolved_area_m2
    return {
        "mode": "panel_body",
        "mode_label": "MANUAL / PANEL + BODY",
        "mass_kg": resolved_mass_kg,
        "area_m2": resolved_area_m2,
        "coefficient": resolved_coefficient,
        "components": (
            {
                "name": "panel",
                "area_m2": resolved_panel_area_m2,
                "coefficient": resolved_panel_coefficient,
            },
            {
                "name": "body",
                "area_m2": resolved_body_area_m2,
                "coefficient": resolved_body_coefficient,
            },
        ),
    }


def solar_radiation_pressure(
    r_sat,
    r_sun,
    coefficient,
    *,
    area_m2=None,
    mass_kg=None,
):
    """Seçilmiş kosmik aparatın SRP təcilini J2000 oxlarında [km/s²] qaytar.

    A TrueSun panel follows the Sun, so an additional orbital incidence cosine
    is not applied to its effective area. Shadowing is applied separately by
    ``sunlight_fraction``.
    """

    r_sat = np.asarray(r_sat, dtype=float)
    r_sun = np.asarray(r_sun, dtype=float)
    # area_m2/mass_kg selects a Sun-tracking effective-area spacecraft model;
    # omitting both selects the built-in synthetic demonstration box-wing.
    coefficient = float(coefficient)
    if r_sat.shape != (3,) or r_sun.shape != (3,):
        raise ValueError("r_sat and r_sun must be 3-element vectors.")
    if not np.isfinite(coefficient) or coefficient <= 0.0:
        raise ValueError("SRP coefficient must be finite and positive.")

    sun_to_sat = r_sat - r_sun
    distance = float(np.linalg.norm(sun_to_sat))
    if distance <= 0.0:
        raise ValueError("Satellite-Sun distance cannot be zero.")
    illumination = sunlight_fraction(r_sat, r_sun)
    photon_direction = sun_to_sat / distance
    if (area_m2 is None) != (mass_kg is None):
        raise ValueError("area_m2 and mass_kg must be supplied together.")
    if area_m2 is None:
        force_per_pressure_m2 = _box_wing_force_per_pressure(
            r_sat,
            photon_direction,
        )
        resolved_mass_kg = DEMO_SPACECRAFT_MASS_KG
    else:
        area_m2 = float(area_m2)
        resolved_mass_kg = float(mass_kg)
        if not np.isfinite(area_m2) or area_m2 <= 0.0:
            raise ValueError("area_m2 must be finite and positive.")
        if not np.isfinite(resolved_mass_kg) or resolved_mass_kg <= 0.0:
            raise ValueError("mass_kg must be finite and positive.")
        # Effective Sun-tracking area model used for spacecraft whose full
        # box-wing optical geometry is not available.  The caller supplies an
        # explicit physical coefficient; no hidden fit is applied.
        force_per_pressure_m2 = area_m2 * photon_direction
    pressure_n_m2 = (
        illumination
        * SOLAR_PRESSURE_1_AU_N_M2
        * coefficient
        * (ASTRONOMICAL_UNIT_KM / distance) ** 2
    )
    # N / kg = m/s²; son bölmə m/s²-dən km/s²-yə çevirir.
    return np.asarray(
        pressure_n_m2
        * force_per_pressure_m2
        / resolved_mass_kg
        / 1000.0,
        dtype=float,
    )
