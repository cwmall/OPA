"""Optional offline IERS Earth-orientation support.

The application remains reproducible with EOP disabled.  When enabled, the
bundled IERS ``finals2000A.all`` series supplies UT1-UTC and polar motion to a
dedicated Skyfield timescale used by every terrestrial-frame transformation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
from threading import RLock

import numpy as np
from skyfield.api import load as skyfield_load
from skyfield.data import iers
from skyfield.framelib import itrs
from skyfield.timelib import Timescale


PROJECT_DIR = Path(__file__).resolve().parent.parent
EOP_FILE = PROJECT_DIR / "data" / "eop" / "finals2000A.all"
EOP_SOURCE_URL = (
    "https://datacenter.iers.org/products/eop/rapid/standard/"
    "finals2000A.all"
)

_MJD_EPOCH = datetime(1858, 11, 17, tzinfo=timezone.utc)
_DEFAULT_TIMESCALE = skyfield_load.timescale(builtin=True)
_LOCK = RLock()
_EOP_ENABLED = False
_EOP_BUNDLE = None


class EarthOrientationError(RuntimeError):
    """Raised when requested EOP data is unavailable or out of coverage."""


@dataclass(frozen=True)
class _EOPBundle:
    timescale: Timescale
    coverage_start_utc: datetime
    coverage_end_utc: datetime
    first_tt_jd: float
    last_tt_jd: float
    rows: int
    sha256: str


def _load_eop_bundle():
    global _EOP_BUNDLE

    with _LOCK:
        if _EOP_BUNDLE is not None:
            return _EOP_BUNDLE
        if not EOP_FILE.is_file():
            raise EarthOrientationError(
                f"Bundled IERS EOP file is missing: {EOP_FILE}"
            )

        try:
            with EOP_FILE.open("rb") as handle:
                finals_data = iers.parse_x_y_dut1_from_finals_all(handle)
        except (OSError, TypeError, ValueError) as error:
            raise EarthOrientationError(
                f"Could not parse IERS EOP file: {error}"
            ) from error
        if len(finals_data) < 2:
            raise EarthOrientationError("IERS EOP file contains too few rows.")

        utc_mjd = np.asarray(finals_data["utc_mjd"], dtype=float)
        dut1 = np.asarray(finals_data["dut1"], dtype=float)
        xp = np.asarray(finals_data["x_arcseconds"], dtype=float)
        yp = np.asarray(finals_data["y_arcseconds"], dtype=float)
        if not all(np.all(np.isfinite(values)) for values in (utc_mjd, dut1, xp, yp)):
            raise EarthOrientationError("IERS EOP file contains invalid values.")
        if np.any(np.diff(utc_mjd) <= 0.0):
            raise EarthOrientationError("IERS EOP epochs are not strictly ordered.")

        daily_tt, daily_delta_t, leap_dates, leap_offsets = (
            iers.build_timescale_arrays(utc_mjd, dut1)
        )
        timescale = Timescale(
            (daily_tt, daily_delta_t),
            leap_dates,
            leap_offsets,
        )
        iers.install_polar_motion_table(timescale, finals_data)

        payload_hash = hashlib.sha256(EOP_FILE.read_bytes()).hexdigest()
        _EOP_BUNDLE = _EOPBundle(
            timescale=timescale,
            coverage_start_utc=_MJD_EPOCH + timedelta(days=float(utc_mjd[0])),
            coverage_end_utc=_MJD_EPOCH + timedelta(days=float(utc_mjd[-1])),
            first_tt_jd=float(daily_tt[0]),
            last_tt_jd=float(daily_tt[-1]),
            rows=int(len(finals_data)),
            sha256=payload_hash,
        )
        return _EOP_BUNDLE


def set_eop_enabled(enabled):
    """Enable or disable application-wide IERS Earth orientation."""

    global _EOP_ENABLED
    enabled = bool(enabled)
    if enabled:
        _load_eop_bundle()
    with _LOCK:
        _EOP_ENABLED = enabled
    return get_eop_status()


def is_eop_enabled():
    with _LOCK:
        return bool(_EOP_ENABLED)


def _use_eop(enabled):
    return is_eop_enabled() if enabled is None else bool(enabled)


def get_eop_status():
    """Return serialisable provenance and coverage for the Settings UI."""

    try:
        bundle = _load_eop_bundle()
    except EarthOrientationError as error:
        return {
            "enabled": is_eop_enabled(),
            "available": False,
            "file": str(EOP_FILE),
            "source": EOP_SOURCE_URL,
            "error": str(error),
        }
    return {
        "enabled": is_eop_enabled(),
        "available": True,
        "file": str(EOP_FILE),
        "source": EOP_SOURCE_URL,
        "coverage_start_utc": bundle.coverage_start_utc.isoformat(),
        "coverage_end_utc": bundle.coverage_end_utc.isoformat(),
        "rows": bundle.rows,
        "sha256": bundle.sha256,
        "components": "UT1-UTC (DUT1) + polar motion xp/yp",
    }


def _validate_utc_epoch(epoch, bundle):
    if not isinstance(epoch, datetime):
        raise TypeError("EOP epoch must be a datetime object.")
    if epoch.tzinfo is None:
        raise ValueError("EOP epoch must be timezone-aware.")
    epoch = epoch.astimezone(timezone.utc)
    if not bundle.coverage_start_utc <= epoch <= bundle.coverage_end_utc:
        raise EarthOrientationError(
            "EOP epoch is outside bundled coverage: "
            f"{epoch.isoformat()} is not within "
            f"{bundle.coverage_start_utc.isoformat()} .. "
            f"{bundle.coverage_end_utc.isoformat()}"
        )
    return epoch


def skyfield_time_from_datetime(epoch, *, eop_enabled=None):
    if not _use_eop(eop_enabled):
        return _DEFAULT_TIMESCALE.from_datetime(epoch)
    bundle = _load_eop_bundle()
    return bundle.timescale.from_datetime(_validate_utc_epoch(epoch, bundle))


def skyfield_time_from_datetimes(epochs, *, eop_enabled=None):
    epochs = tuple(epochs)
    if not epochs:
        raise ValueError("At least one epoch is required.")
    if not _use_eop(eop_enabled):
        return _DEFAULT_TIMESCALE.from_datetimes(epochs)
    bundle = _load_eop_bundle()
    checked = tuple(_validate_utc_epoch(epoch, bundle) for epoch in epochs)
    return bundle.timescale.from_datetimes(checked)


def skyfield_time_from_tt_jd(tt_jd, *, eop_enabled=None):
    values = np.asarray(tt_jd, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("TT Julian date must be finite.")
    if not _use_eop(eop_enabled):
        return _DEFAULT_TIMESCALE.tt_jd(tt_jd)
    bundle = _load_eop_bundle()
    if np.any(values < bundle.first_tt_jd) or np.any(values > bundle.last_tt_jd):
        raise EarthOrientationError(
            "TT epoch is outside bundled IERS EOP coverage."
        )
    return bundle.timescale.tt_jd(tt_jd)


def j2000_to_itrs_rotation_from_datetime(epoch, *, eop_enabled=None):
    return np.asarray(
        itrs.rotation_at(
            skyfield_time_from_datetime(epoch, eop_enabled=eop_enabled)
        ),
        dtype=float,
    )


def j2000_to_itrs_rotation_from_tt_jd(tt_jd, *, eop_enabled=None):
    return np.asarray(
        itrs.rotation_at(
            skyfield_time_from_tt_jd(tt_jd, eop_enabled=eop_enabled)
        ),
        dtype=float,
    )


def eop_values_at(epoch):
    """Return interpolated DUT1 and polar-motion values at one UTC epoch."""

    time = skyfield_time_from_datetime(epoch, eop_enabled=True)
    _sprime, xp_arcseconds, yp_arcseconds = time.polar_motion_angles()
    return {
        "dut1_seconds": float(time.dut1),
        "xp_arcseconds": float(xp_arcseconds),
        "yp_arcseconds": float(yp_arcseconds),
    }
