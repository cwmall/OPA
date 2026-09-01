from datetime import datetime, timezone

import spiceypy as spice

from spice_loader import load_kernels


CSV_UTC_FORMAT = "%d/%m/%Y %H:%M:%S.%f"


def format_csv_utc(utc_time):
    """Return the application-wide UTC CSV timestamp with millisecond precision."""

    if utc_time is None:
        return ""
    if not isinstance(utc_time, datetime):
        raise TypeError("CSV UTC value must be a datetime object.")
    if utc_time.tzinfo is None:
        raise ValueError("CSV UTC value must be timezone-aware.")
    value = utc_time.astimezone(timezone.utc).strftime(CSV_UTC_FORMAT)
    return value[:-3]


def format_csv_date(utc_time):
    """Return the date portion used by legacy split Date/Time CSV layouts."""

    if not isinstance(utc_time, datetime) or utc_time.tzinfo is None:
        raise ValueError("CSV date value must be a timezone-aware datetime.")
    return utc_time.astimezone(timezone.utc).strftime("%d/%m/%Y")


def format_csv_time(utc_time):
    """Return the time portion used by legacy split Date/Time CSV layouts."""

    if not isinstance(utc_time, datetime) or utc_time.tzinfo is None:
        raise ValueError("CSV time value must be a timezone-aware datetime.")
    return utc_time.astimezone(timezone.utc).strftime("%H:%M:%S.%f")[:-3]


# ============================================================
# CURRENT UTC
# ============================================================

def get_current_utc():
    """
    Return the current UTC time as a timezone-aware datetime.

    Returns
    -------
    datetime
        Current UTC datetime with timezone information.
    """

    return datetime.now(timezone.utc)


# ============================================================
# DATETIME -> UTC STRING
# ============================================================

def datetime_to_utc_string(utc_time):
    """
    Convert a timezone-aware datetime object to a SPICE-compatible
    UTC string while preserving microsecond precision.

    Parameters
    ----------
    utc_time : datetime
        Timezone-aware datetime object.

    Returns
    -------
    str
        UTC string in format:

        YYYY-MM-DDTHH:MM:SS.ffffff
    """

    if not isinstance(utc_time, datetime):
        raise TypeError(
            "utc_time must be a datetime object."
        )

    if utc_time.tzinfo is None:
        raise ValueError(
            "utc_time must be timezone-aware."
        )

    # Convert any timezone to UTC
    utc_time = utc_time.astimezone(
        timezone.utc
    )

    return utc_time.strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )


# ============================================================
# UTC -> SPICE ET
# ============================================================

def utc_to_et(utc_time):
    """
    Convert a timezone-aware UTC datetime to
    SPICE Ephemeris Time (ET).

    Parameters
    ----------
    utc_time : datetime
        Timezone-aware datetime object.

    Returns
    -------
    float
        SPICE Ephemeris Time in seconds past J2000.
    """

    # Make sure leap-second kernel is available
    load_kernels()

    utc_string = datetime_to_utc_string(
        utc_time
    )

    et = spice.utc2et(
        utc_string
    )

    return float(et)


# ============================================================
# SPICE ET -> UTC
# ============================================================

def et_to_utc(et):
    """
    Convert SPICE Ephemeris Time (ET) back to
    a timezone-aware UTC datetime.

    Parameters
    ----------
    et : float
        SPICE Ephemeris Time.

    Returns
    -------
    datetime
        UTC datetime.
    """

    load_kernels()

    utc_string = spice.et2utc(
        float(et),
        "ISOC",
        6
    )

    utc_time = datetime.fromisoformat(
        utc_string
    )

    return utc_time.replace(
        tzinfo=timezone.utc
    )


# ============================================================
# ADD SECONDS USING ET
# ============================================================

def add_seconds_et(utc_time, seconds):
    """
    Advance a UTC datetime by a number of SI seconds
    using SPICE Ephemeris Time.

    This is useful for orbital propagation because
    SPICE handles the underlying astronomical time scales.

    Parameters
    ----------
    utc_time : datetime
        Initial timezone-aware UTC datetime.

    seconds : float
        Number of seconds to advance.

    Returns
    -------
    datetime
        Resulting UTC datetime.
    """

    et = utc_to_et(
        utc_time
    )

    new_et = et + float(
        seconds
    )

    return et_to_utc(
        new_et
    )
