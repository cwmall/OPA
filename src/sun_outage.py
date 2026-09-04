"""GSO Earth-station Sun-transit prediction.

The geometry follows the simplified operational method in ITU-R S.1525-1,
Annex 2.  DE440 supplies the apparent Sun direction while the Earth station is
placed on WGS-84 and the selected spacecraft is represented by its nominal
Earth-fixed GSO slot.  The reported interval is the intersection of the solar
disc and the antenna 3 dB beam; it is a geometric interference-risk window,
not a carrier-specific link-budget outage guarantee.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta, timezone
import math
from pathlib import Path
from typing import Callable

import numpy as np
import spiceypy as spice
from scipy.optimize import brentq, minimize_scalar

from constants import R_EARTH, SUN_MEAN_RADIUS_KM, WGS84_FLATTENING
from earth_orientation import j2000_to_itrs_rotation_from_datetime
from spice_loader import load_kernels
from time_utils import format_csv_utc, utc_to_et


SPEED_OF_LIGHT_M_S = 299_792_458.0
NOMINAL_GSO_RADIUS_KM = 42_164.0
ITU_R_S_1525_URL = (
    "https://www.itu.int/rec/R-REC-S.1525/en"
)


class SunOutageError(ValueError):
    """Raised when a Sun-outage request is physically invalid."""


class SunOutageCancelled(RuntimeError):
    """Raised when the background year search is cancelled."""


@dataclass(frozen=True)
class SunOutageStation:
    station_id: str
    name: str
    latitude_deg: float
    longitude_deg: float
    height_km: float = 0.0


@dataclass(frozen=True)
class SunOutageEvent:
    start_utc: datetime
    peak_utc: datetime
    end_utc: datetime
    minimum_separation_deg: float
    threshold_deg: float
    sun_angular_diameter_deg: float
    beamwidth_3db_deg: float

    @property
    def duration_seconds(self) -> float:
        return (self.end_utc - self.start_utc).total_seconds()


@dataclass(frozen=True)
class SunOutagePrediction:
    year: int
    station: SunOutageStation
    satellite_longitude_deg: float
    frequency_ghz: float
    antenna_diameter_m: float
    beamwidth_3db_deg: float
    events: tuple[SunOutageEvent, ...]
    method: str = "ITU-R S.1525-1 Annex 2 geometry + JPL DE440 Sun"


def half_power_beamwidth_deg(frequency_ghz: float, antenna_diameter_m: float) -> float:
    """Return the ITU-R S.1525-1 estimate ``70 λ / d`` in degrees."""

    frequency = _positive(frequency_ghz, "Frequency")
    diameter = _positive(antenna_diameter_m, "Antenna diameter")
    wavelength_m = SPEED_OF_LIGHT_M_S / (frequency * 1.0e9)
    return 70.0 * wavelength_m / diameter


def _positive(value, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise SunOutageError(f"{label} must be numeric.") from error
    if not math.isfinite(result) or result <= 0.0:
        raise SunOutageError(f"{label} must be finite and greater than zero.")
    return result


def _validated_station(station: SunOutageStation) -> SunOutageStation:
    if not isinstance(station, SunOutageStation):
        raise SunOutageError("A valid ground station is required.")
    latitude = float(station.latitude_deg)
    longitude = float(station.longitude_deg)
    height = float(station.height_km)
    if not all(math.isfinite(value) for value in (latitude, longitude, height)):
        raise SunOutageError("Ground-station coordinates must be finite.")
    if not -90.0 <= latitude <= 90.0:
        raise SunOutageError("Ground-station latitude must be within ±90 degrees.")
    if not -180.0 <= longitude <= 180.0:
        raise SunOutageError("Ground-station longitude must be within ±180 degrees.")
    if height < -1.0 or height > 20.0:
        raise SunOutageError("Ground-station height is outside the supported range.")
    return station


def _geodetic_to_ecef(station: SunOutageStation) -> np.ndarray:
    latitude = math.radians(station.latitude_deg)
    longitude = math.radians(station.longitude_deg)
    eccentricity_squared = WGS84_FLATTENING * (2.0 - WGS84_FLATTENING)
    prime_vertical = R_EARTH / math.sqrt(
        1.0 - eccentricity_squared * math.sin(latitude) ** 2
    )
    radius = prime_vertical + station.height_km
    return np.asarray(
        [
            radius * math.cos(latitude) * math.cos(longitude),
            radius * math.cos(latitude) * math.sin(longitude),
            (prime_vertical * (1.0 - eccentricity_squared) + station.height_km)
            * math.sin(latitude),
        ],
        dtype=float,
    )


def _gso_ecef(longitude_deg: float) -> np.ndarray:
    longitude = math.radians(longitude_deg)
    return np.asarray(
        [
            NOMINAL_GSO_RADIUS_KM * math.cos(longitude),
            NOMINAL_GSO_RADIUS_KM * math.sin(longitude),
            0.0,
        ],
        dtype=float,
    )


def _apparent_sun_j2000(epoch: datetime) -> np.ndarray:
    load_kernels()
    state, _light_time = spice.spkezr(
        "SUN",
        utc_to_et(epoch),
        "J2000",
        "LT+S",
        "EARTH",
    )
    return np.asarray(state[:3], dtype=float)


def sun_satellite_separation_deg(
    epoch: datetime,
    station: SunOutageStation,
    satellite_longitude_deg: float,
    *,
    eop_enabled: bool | None = None,
) -> tuple[float, float]:
    """Return topocentric Sun/GSO separation and apparent solar diameter."""

    if not isinstance(epoch, datetime) or epoch.tzinfo is None:
        raise SunOutageError("Epoch must be timezone-aware.")
    station = _validated_station(station)
    longitude = float(satellite_longitude_deg)
    if not math.isfinite(longitude) or not -180.0 <= longitude <= 180.0:
        raise SunOutageError("Satellite longitude must be within ±180 degrees.")
    epoch = epoch.astimezone(timezone.utc)
    station_ecef = _geodetic_to_ecef(station)
    satellite_line = _gso_ecef(longitude) - station_ecef
    satellite_distance = float(np.linalg.norm(satellite_line))
    if satellite_distance <= 0.0:
        raise SunOutageError("Invalid station-to-satellite geometry.")

    sun_j2000 = _apparent_sun_j2000(epoch)
    rotation = j2000_to_itrs_rotation_from_datetime(
        epoch,
        eop_enabled=eop_enabled,
    )
    sun_ecef = np.asarray(rotation @ sun_j2000, dtype=float)
    sun_line = sun_ecef - station_ecef
    sun_distance = float(np.linalg.norm(sun_line))
    if sun_distance <= SUN_MEAN_RADIUS_KM:
        raise SunOutageError("Invalid Earth-to-Sun geometry.")

    cosine = float(
        np.dot(satellite_line, sun_line)
        / (satellite_distance * sun_distance)
    )
    separation = math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))
    solar_diameter = 2.0 * math.degrees(
        math.asin(SUN_MEAN_RADIUS_KM / sun_distance)
    )
    return separation, solar_diameter


def _candidate_dates(year: int) -> tuple[date, ...]:
    dates: list[date] = []
    for centre in (date(year, 3, 20), date(year, 9, 22)):
        dates.extend(centre + timedelta(days=offset) for offset in range(-30, 31))
    return tuple(dict.fromkeys(dates))


def predict_sun_outages(
    *,
    year: int,
    station: SunOutageStation,
    satellite_longitude_deg: float,
    frequency_ghz: float,
    antenna_diameter_m: float,
    eop_enabled: bool | None = None,
    candidate_dates: tuple[date, ...] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[int], None] | None = None,
) -> SunOutagePrediction:
    """Predict daily GSO Sun-transit risk intervals for one calendar year."""

    selected_year = int(year)
    if not 1900 <= selected_year <= 2199:
        raise SunOutageError("Year must be between 1900 and 2199.")
    station = _validated_station(station)
    beamwidth = half_power_beamwidth_deg(frequency_ghz, antenna_diameter_m)
    if beamwidth > 30.0:
        raise SunOutageError(
            "The estimated 3 dB beamwidth exceeds 30 degrees; check frequency and diameter."
        )
    dates = tuple(candidate_dates or _candidate_dates(selected_year))
    if not dates:
        raise SunOutageError("At least one candidate date is required.")
    if any(item.year != selected_year for item in dates):
        raise SunOutageError("Candidate dates must belong to the selected year.")

    events: list[SunOutageEvent] = []
    total = len(dates)
    for index, day in enumerate(dates):
        if cancel_check is not None and cancel_check():
            raise SunOutageCancelled("Sun-outage search cancelled.")
        midnight = datetime.combine(day, datetime_time(), tzinfo=timezone.utc)

        def geometry_at(seconds: float) -> tuple[float, float]:
            if cancel_check is not None and cancel_check():
                raise SunOutageCancelled("Sun-outage search cancelled.")
            return sun_satellite_separation_deg(
                midnight + timedelta(seconds=float(seconds)),
                station,
                satellite_longitude_deg,
                eop_enabled=eop_enabled,
            )

        optimum = minimize_scalar(
            lambda seconds: geometry_at(seconds)[0],
            bounds=(0.0, 86400.0),
            method="bounded",
            options={"xatol": 0.05, "maxiter": 80},
        )
        if not optimum.success:
            raise SunOutageError(f"Could not refine the Sun transit on {day.isoformat()}.")
        peak_seconds = float(optimum.x)
        minimum_separation, solar_diameter = geometry_at(peak_seconds)
        threshold = 0.5 * (solar_diameter + beamwidth)
        if minimum_separation <= threshold:
            def boundary(seconds: float) -> float:
                separation, diameter = geometry_at(seconds)
                return separation - 0.5 * (diameter + beamwidth)

            try:
                start_seconds = brentq(
                    boundary,
                    0.0,
                    peak_seconds,
                    xtol=0.05,
                    rtol=1.0e-12,
                )
                end_seconds = brentq(
                    boundary,
                    peak_seconds,
                    86400.0,
                    xtol=0.05,
                    rtol=1.0e-12,
                )
            except ValueError as error:
                raise SunOutageError(
                    f"Could not bracket the Sun-transit contacts on {day.isoformat()}."
                ) from error
            events.append(
                SunOutageEvent(
                    start_utc=midnight + timedelta(seconds=start_seconds),
                    peak_utc=midnight + timedelta(seconds=peak_seconds),
                    end_utc=midnight + timedelta(seconds=end_seconds),
                    minimum_separation_deg=float(minimum_separation),
                    threshold_deg=float(threshold),
                    sun_angular_diameter_deg=float(solar_diameter),
                    beamwidth_3db_deg=float(beamwidth),
                )
            )
        if progress_callback is not None:
            progress_callback(int(100 * (index + 1) / total))

    return SunOutagePrediction(
        year=selected_year,
        station=station,
        satellite_longitude_deg=float(satellite_longitude_deg),
        frequency_ghz=float(frequency_ghz),
        antenna_diameter_m=float(antenna_diameter_m),
        beamwidth_3db_deg=float(beamwidth),
        events=tuple(events),
    )


def save_sun_outage_csv(prediction: SunOutagePrediction, file_path) -> Path:
    """Export one auditable row per predicted interference-risk interval."""

    if not isinstance(prediction, SunOutagePrediction):
        raise SunOutageError("Calculate Sun-outage events before export.")
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            (
                "Station ID",
                "Station name",
                "Satellite longitude [deg E]",
                "Frequency [GHz]",
                "Antenna diameter [m]",
                "3 dB beamwidth [deg]",
                "Start UTC",
                "Peak UTC",
                "End UTC",
                "Duration [s]",
                "Minimum separation [deg]",
                "Threshold [deg]",
                "Solar angular diameter [deg]",
                "Method",
            )
        )
        for event in prediction.events:
            writer.writerow(
                (
                    prediction.station.station_id,
                    prediction.station.name,
                    f"{prediction.satellite_longitude_deg:.8f}",
                    f"{prediction.frequency_ghz:.6f}",
                    f"{prediction.antenna_diameter_m:.6f}",
                    f"{event.beamwidth_3db_deg:.9f}",
                    format_csv_utc(event.start_utc),
                    format_csv_utc(event.peak_utc),
                    format_csv_utc(event.end_utc),
                    f"{event.duration_seconds:.3f}",
                    f"{event.minimum_separation_deg:.9f}",
                    f"{event.threshold_deg:.9f}",
                    f"{event.sun_angular_diameter_deg:.9f}",
                    prediction.method,
                )
            )
    return path
