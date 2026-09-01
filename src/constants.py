"""
Physical and astrodynamic constants used throughout
the Orbital Perturbation Analyzer project.

Unit system
-----------
Distance     : km
Time         : s
Velocity     : km/s
Acceleration : km/s^2
GM           : km^3/s^2
"""


# ============================================================
# EARTH
# ============================================================

# Earth gravitational parameter.
#
# EGM96 / WGS84(G873) value. The spherical-harmonic coefficients and
# their reference GM must be used as one consistent gravity model.
# Source: the official NGA EGM96 distribution, f477.f.
MU_EARTH = 398600.4418


# Earth equatorial reference radius.
#
# EGM96 / WGS84(G873) reference equatorial radius.
# Source: the official NGA EGM96 distribution, f477.f.
R_EARTH = 6378.137


# Earth polar (semi-minor) reference radius.
#
# WGS-84 value. The Earth is 21.4 km smaller through the poles than at the
# equator, so its shadow silhouette is an ellipse rather than a circle. That
# difference is negligible when a satellite crosses the middle of the shadow
# and dominant when it grazes the northern or southern limb, which is exactly
# what happens at the first and last eclipse of a season.
EARTH_POLAR_RADIUS_KM = 6356.752314245


# WGS-84 flattening, kept as the single source for both the shadow silhouette
# and the 3-D Earth rendering.
WGS84_FLATTENING = 1.0 / 298.257223563


# Earth's second zonal harmonic.
#
# This represents Earth's oblateness and is the dominant
# non-spherical gravity perturbation.
J2_EARTH = 1.08262668e-3


# Earth's unnormalized degree-2, order-2 spherical-harmonic
# coefficients (EGM96 convention). These tesseral terms model
# the equatorial ellipticity that drives longitude drift at GEO.
C22_EARTH = 1.5744570e-6
S22_EARTH = -0.9038060e-6

# Production spherical-harmonic truncation. The 30-day GEO regression shows
# degree/order 4 is both more accurate for the supplied reference and roughly
# twice as fast as degree/order 8.
EARTH_GRAVITY_DEGREE = 4


# Approximate TT - UT1 [s] used to recover Earth rotation from
# SPICE ET for the C22/S22 model. A sub-second error here has a
# negligible effect at degree 2, but this approximation should be
# replaced by Earth-orientation data for precision operational work.
DELTA_T_TT_UT1 = 69.2


# ============================================================
# MOON
# ============================================================

# Lunar gravitational parameter.
#
# JPL DE440 value.
MU_MOON = 4902.800118

# IAU mean lunar radius used for apparent-disc occultation geometry [km].
R_MOON = 1737.4


# ============================================================
# SUN
# ============================================================

# Solar gravitational parameter.
#
# JPL DE440-compatible solar GM. Optional solar third-body gravity uses this
# value; solar radiation pressure is implemented separately by the physical
# box-wing module.
MU_SUN = 132712440041.279419

# Fully synthetic public demonstration spacecraft. These values were created
# for this repository and do not describe a real spacecraft or operator.
DEMO_SPACECRAFT_MASS_KG = 1000.0
DEMO_SPACECRAFT_SOLAR_ARRAY_TRACKING_MODE = "TrueSun"
DEMO_SPACECRAFT_SOLAR_ARRAY_COUNT = 2
DEMO_SPACECRAFT_SOLAR_ARRAY_WIDTH_M = 1.5
DEMO_SPACECRAFT_SOLAR_ARRAY_HEIGHT_M = 6.0
DEMO_SPACECRAFT_TOTAL_SOLAR_ARRAY_AREA_M2 = 18.0
DEMO_SPACECRAFT_SOLAR_ARRAY_SPECULAR = 0.10
DEMO_SPACECRAFT_SOLAR_ARRAY_DIFFUSE = 0.10
DEMO_SPACECRAFT_SOLAR_ARRAY_ABSORPTION = 0.80
DEMO_SPACECRAFT_BODY_X_M = 2.0
DEMO_SPACECRAFT_BODY_Y_M = 1.8
DEMO_SPACECRAFT_BODY_Z_M = 3.0
DEMO_SPACECRAFT_BODY_SPECULAR = 0.15
DEMO_SPACECRAFT_BODY_DIFFUSE = 0.15
DEMO_SPACECRAFT_BODY_ABSORPTION = 0.70
SOLAR_PRESSURE_1_AU_N_M2 = 4.56e-6
ASTRONOMICAL_UNIT_KM = 149597870.7
SUN_MEAN_RADIUS_KM = 695700.0


# ============================================================
# TIME
# ============================================================

SECONDS_PER_MINUTE = 60.0

SECONDS_PER_HOUR = 3600.0

SECONDS_PER_DAY = 86400.0


# ============================================================
# PROPAGATION DEFAULTS
# ============================================================

# Maximum integration step.
#
# DOP853 is adaptive, so this is only the maximum allowed step.
DEFAULT_MAX_STEP = 300.0


# Relative integration tolerance.
DEFAULT_RTOL = 1.0e-11


# Absolute integration tolerance.
DEFAULT_ATOL = 1.0e-12
