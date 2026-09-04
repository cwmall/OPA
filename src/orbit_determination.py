"""Weighted batch least-squares orbit determination for OPA datasets.

The supplied ``orbit_file.csv`` is the nominal ephemeris. Ground-station
measurements are modelled in WGS-84/ITRS and weighted batch least squares
estimates a six-component Cartesian correction to that file. The application's
general numerical propagator is deliberately not used by this workflow.
"""

from __future__ import annotations

import ast
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
from constants import (
    MU_EARTH,
    R_EARTH,
    WGS84_FLATTENING,
)
from earth_gravity import earth_rotation_angle
from earth_orientation import j2000_to_itrs_rotation_from_datetime
from orbital_elements import keplerian_to_cartesian
from time_utils import utc_to_et


GENERIC_TIME_FORMAT = "%Y/%m/%d-%H:%M:%S.%f"
SUPPORTED_MEASUREMENT_TYPES = ("Range", "Azimuth", "Elevation")


class OrbitDeterminationError(ValueError):
    """Raised when an OD dataset or requested estimation arc is invalid."""


class OrbitDeterminationCancelled(RuntimeError):
    """Raised when the background file-based estimator is cancelled."""


def _validate_state(state):
    state = np.asarray(state, dtype=float)
    if state.shape != (6,) or not np.all(np.isfinite(state)):
        raise OrbitDeterminationError("State must contain six finite values.")
    return state


@dataclass(frozen=True)
class GroundStation:
    station_id: str
    name: str
    latitude_deg: float
    longitude_deg: float
    height_km: float
    temperature_c: float
    pressure_mbar: float
    humidity_percent: float
    biases: dict[str, float]
    noises: dict[str, float]
    range_ambiguity_km: float


@dataclass(frozen=True)
class Measurement:
    measurement_id: int
    quality_factor: int
    station_id: str
    measurement_type: str
    epoch: datetime
    value: float


@dataclass(frozen=True)
class ReferenceOrbitRecord:
    epoch: datetime
    elements: np.ndarray
    cp_scale_factor: float
    discontinuity: bool


@dataclass(frozen=True)
class OrbitDeterminationDataset:
    dataset_id: str
    display_name: str
    frame_note: str
    spacecraft_mass_kg: float
    cp_scale_factor: float
    stations: dict[str, GroundStation]
    measurements: tuple[Measurement, ...]
    reference_orbit: tuple[ReferenceOrbitRecord, ...]
    source_directory: Path

    @property
    def measurement_start(self):
        return min(item.epoch for item in self.measurements)

    @property
    def measurement_end(self):
        return max(item.epoch for item in self.measurements)

    @property
    def reference_start(self):
        return min(item.epoch for item in self.reference_orbit)

    @property
    def reference_end(self):
        return max(item.epoch for item in self.reference_orbit)


_SESSION_ORBIT_DETERMINATION_DATASETS = {}


def clear_session_orbit_determination_datasets():
    """Remove decrypted OD measurements and references from memory."""

    _SESSION_ORBIT_DETERMINATION_DATASETS.clear()


def register_session_orbit_determination_datasets(datasets):
    """Install validated, data-only OD datasets for the current session."""

    clear_session_orbit_determination_datasets()
    for source in datasets:
        stations = {
            item["station_id"]: GroundStation(
                station_id=str(item["station_id"]),
                name=str(item["name"]),
                latitude_deg=float(item["latitude_deg"]),
                longitude_deg=float(item["longitude_deg"]),
                height_km=float(item["height_km"]),
                temperature_c=float(item["temperature_c"]),
                pressure_mbar=float(item["pressure_mbar"]),
                humidity_percent=float(item["humidity_percent"]),
                biases={key: float(value) for key, value in item["biases"].items()},
                noises={key: float(value) for key, value in item["noises"].items()},
                range_ambiguity_km=float(item["range_ambiguity_km"]),
            )
            for item in source["stations"]
        }
        measurements = tuple(
            Measurement(
                measurement_id=int(item["measurement_id"]),
                quality_factor=int(item["quality_factor"]),
                station_id=str(item["station_id"]),
                measurement_type=str(item["type"]),
                epoch=datetime.fromisoformat(item["epoch_utc"]).astimezone(timezone.utc),
                value=float(item["value"]),
            )
            for item in source["measurements"]
        )
        reference_orbit = tuple(
            ReferenceOrbitRecord(
                epoch=datetime.fromisoformat(item["epoch_utc"]).astimezone(timezone.utc),
                elements=np.asarray(item["elements"], dtype=float),
                cp_scale_factor=float(item["cp_scale_factor"]),
                discontinuity=bool(item["discontinuity"]),
            )
            for item in source["reference_orbit"]
        )
        dataset = OrbitDeterminationDataset(
            dataset_id=str(source["id"]),
            display_name=str(source["display_name"]),
            frame_note=str(source["frame_note"]),
            spacecraft_mass_kg=float(source["spacecraft_mass_kg"]),
            cp_scale_factor=float(source["cp_scale_factor"]),
            stations=stations,
            measurements=measurements,
            reference_orbit=reference_orbit,
            source_directory=Path("ADMIN_SESSION_MEMORY"),
        )
        _SESSION_ORBIT_DETERMINATION_DATASETS[dataset.dataset_id] = dataset


def available_ground_stations():
    """Return session stations, or fictional public stations while locked.

    Admin coordinates remain in memory and are removed by
    ``clear_session_orbit_determination_datasets``.  The stable dataset/station
    key lets GUI selectors distinguish equal station identifiers in different
    datasets without persisting any private location.
    """

    datasets = tuple(_SESSION_ORBIT_DETERMINATION_DATASETS.values())
    if not datasets:
        datasets = (_synthetic_dataset(),)
    return tuple(
        (dataset.dataset_id, station)
        for dataset in datasets
        for station in sorted(
            dataset.stations.values(),
            key=lambda item: (item.name.casefold(), item.station_id.casefold()),
        )
    )


@dataclass(frozen=True)
class ResidualSummary:
    station_id: str
    station_name: str
    measurement_type: str
    noise: float
    count: int
    rejected: int
    prefit_mean: float
    prefit_rms: float
    postfit_mean: float
    postfit_rms: float


@dataclass(frozen=True)
class OrbitDeterminationResult:
    dataset_id: str
    arc_start: datetime
    arc_end: datetime
    estimation_epoch: datetime
    initial_state: np.ndarray
    corrected_state: np.ndarray
    state_correction: np.ndarray
    covariance: np.ndarray
    parameter_sigmas: np.ndarray
    condition_number: float
    iterations: int
    converged: bool
    weighted_rms_prefit: float
    weighted_rms_postfit: float
    measurements: tuple[Measurement, ...]
    predicted_prefit: np.ndarray
    predicted_postfit: np.ndarray
    residuals_prefit: np.ndarray
    residuals_postfit: np.ndarray
    accepted_mask: np.ndarray
    summaries: tuple[ResidualSummary, ...]
    reference_epochs: tuple[datetime, ...]
    determination_file_states: np.ndarray
    determination_prefit_states: np.ndarray
    determination_postfit_states: np.ndarray
    reference_position_errors_prefit_km: np.ndarray
    reference_position_errors_postfit_km: np.ndarray
    reference_velocity_errors_prefit_km_s: np.ndarray
    reference_velocity_errors_postfit_km_s: np.ndarray
    state_jump_count: int
    noon_epoch: datetime | None
    noon_position_error_prefit_km: float | None
    noon_position_error_postfit_km: float | None
    noon_velocity_error_prefit_km_s: float | None
    noon_velocity_error_postfit_km_s: float | None


def _parse_dataset_epoch(value: str) -> datetime:
    try:
        return datetime.strptime(value.strip(), GENERIC_TIME_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except (TypeError, ValueError) as error:
        raise OrbitDeterminationError(
            f"Invalid dataset epoch: {value!r}."
        ) from error


def _finite(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise OrbitDeterminationError(f"{label} must be numeric.") from error
    if not np.isfinite(result):
        raise OrbitDeterminationError(f"{label} must be finite.")
    return result


def _load_station(source) -> GroundStation:
    station_id = str(source.get("station_id", "")).strip()
    if not station_id:
        raise OrbitDeterminationError("Every station requires station_id.")
    biases = {
        "Range": _finite(source.get("range_bias_km", 0.0), "Range bias"),
        "Azimuth": _finite(source.get("azimuth_bias_deg", 0.0), "Azimuth bias"),
        "Elevation": _finite(source.get("elevation_bias_deg", 0.0), "Elevation bias"),
    }
    noises = {
        "Range": _finite(source.get("range_noise_km"), "Range noise"),
        "Azimuth": _finite(source.get("azimuth_noise_deg"), "Azimuth noise"),
        "Elevation": _finite(source.get("elevation_noise_deg"), "Elevation noise"),
    }
    if any(value <= 0.0 for value in noises.values()):
        raise OrbitDeterminationError("Station measurement noises must be positive.")
    return GroundStation(
        station_id=station_id,
        name=str(source.get("name") or station_id).strip(),
        latitude_deg=_finite(source.get("latitude_deg"), "Station latitude"),
        longitude_deg=_finite(source.get("longitude_deg"), "Station longitude"),
        height_km=_finite(source.get("height_km"), "Station height"),
        temperature_c=_finite(source.get("temperature_c", 15.0), "Temperature"),
        pressure_mbar=_finite(source.get("pressure_mbar", 1013.25), "Pressure"),
        humidity_percent=_finite(source.get("humidity_percent", 0.0), "Humidity"),
        biases=biases,
        noises=noises,
        range_ambiguity_km=_finite(
            source.get("range_ambiguity_km", 0.0), "Range ambiguity"
        ),
    )


def load_dataset(directory: Path | str | None = None) -> OrbitDeterminationDataset:
    """Load a user dataset, or the in-memory public SYNTHETIC/DEMO dataset."""

    if directory is None:
        if _SESSION_ORBIT_DETERMINATION_DATASETS:
            return next(iter(_SESSION_ORBIT_DETERMINATION_DATASETS.values()))
        return _synthetic_dataset()

    directory = Path(directory).resolve()
    metadata_path = directory / "dataset.json"
    measurement_path = directory / "measurements.csv"
    orbit_path = directory / "orbit_file.csv"
    for path in (metadata_path, measurement_path, orbit_path):
        if not path.is_file():
            raise OrbitDeterminationError(f"Required OD file is missing: {path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    stations = {
        station.station_id: station
        for station in (_load_station(item) for item in metadata.get("stations", ()))
    }
    if not stations:
        raise OrbitDeterminationError("OD dataset contains no ground stations.")

    measurements = []
    with measurement_path.open(newline="", encoding="utf-8-sig") as stream:
        for row_number, row in enumerate(csv.DictReader(stream), start=2):
            station_id = str(row.get("Station ID:", "")).strip()
            measurement_type = str(row.get("Type:", "")).strip()
            if station_id not in stations:
                raise OrbitDeterminationError(
                    f"Unknown station {station_id!r} at measurements row {row_number}."
                )
            if measurement_type not in SUPPORTED_MEASUREMENT_TYPES:
                raise OrbitDeterminationError(
                    f"Unsupported measurement type {measurement_type!r} at row {row_number}."
                )
            measurements.append(Measurement(
                measurement_id=int(row["Measurement ID:"]),
                quality_factor=int(row["Quality Factor:"]),
                station_id=station_id,
                measurement_type=measurement_type,
                epoch=_parse_dataset_epoch(row["Time Tag:"]),
                value=_finite(row["Measurement Value:"], "Measurement value"),
            ))
    if not measurements:
        raise OrbitDeterminationError("OD measurement file is empty.")
    measurements.sort(key=lambda item: (item.epoch, item.measurement_id))

    reference_orbit = []
    with orbit_path.open(newline="", encoding="utf-8-sig") as stream:
        for row_number, row in enumerate(csv.DictReader(stream), start=2):
            try:
                elements = np.asarray(ast.literal_eval(row["State"]), dtype=float)
            except (SyntaxError, ValueError) as error:
                raise OrbitDeterminationError(
                    f"Invalid orbit state at row {row_number}."
                ) from error
            if elements.shape != (6,) or not np.all(np.isfinite(elements)):
                raise OrbitDeterminationError(
                    f"Orbit row {row_number} must contain six finite elements."
                )
            reference_orbit.append(ReferenceOrbitRecord(
                epoch=_parse_dataset_epoch(row["Epoch"]),
                elements=elements,
                cp_scale_factor=_finite(row["Cp Scale Factor"], "CP scale factor"),
                discontinuity=str(row["Discontinuity Flag"]).strip().lower() == "true",
            ))
    if not reference_orbit:
        raise OrbitDeterminationError("OD reference orbit file is empty.")
    reference_orbit.sort(key=lambda item: item.epoch)

    return OrbitDeterminationDataset(
        dataset_id=str(metadata.get("dataset_id") or directory.name),
        display_name=str(metadata.get("display_name") or directory.name),
        frame_note=str(metadata.get("frame_note") or ""),
        spacecraft_mass_kg=_finite(metadata.get("spacecraft_mass_kg"), "Spacecraft mass"),
        cp_scale_factor=_finite(metadata.get("cp_scale_factor"), "CP scale factor"),
        stations=stations,
        measurements=tuple(measurements),
        reference_orbit=tuple(reference_orbit),
        source_directory=directory,
    )


def _wrap_degrees(value):
    return (np.asarray(value, dtype=float) + 180.0) % 360.0 - 180.0


def _geodetic_to_ecef(station: GroundStation):
    latitude = np.radians(station.latitude_deg)
    longitude = np.radians(station.longitude_deg)
    eccentricity_squared = WGS84_FLATTENING * (2.0 - WGS84_FLATTENING)
    prime_vertical = R_EARTH / np.sqrt(
        1.0 - eccentricity_squared * np.sin(latitude) ** 2
    )
    return np.array([
        (prime_vertical + station.height_km) * np.cos(latitude) * np.cos(longitude),
        (prime_vertical + station.height_km) * np.cos(latitude) * np.sin(longitude),
        (prime_vertical * (1.0 - eccentricity_squared) + station.height_km)
        * np.sin(latitude),
    ], dtype=float)


def _atmospheric_refraction_deg(elevation_deg, station: GroundStation):
    """Return the standard near-horizon optical elevation correction."""

    elevation_deg = float(elevation_deg)
    if elevation_deg <= -1.0:
        return 0.0
    denominator_angle = elevation_deg + 10.3 / (elevation_deg + 5.11)
    correction_arcminutes = (
        1.02
        / np.tan(np.radians(denominator_angle))
        * (station.pressure_mbar / 1010.0)
        * (283.0 / (273.0 + station.temperature_c))
    )
    return float(correction_arcminutes / 60.0)


def reference_elements_to_j2000(elements, epoch):
    """Convert generic of-date orbital elements to OPA J2000 Cartesian."""

    elements = np.asarray(elements, dtype=float)
    if elements.shape != (6,) or not np.all(np.isfinite(elements)):
        raise OrbitDeterminationError("Reference state must contain six finite elements.")
    if epoch.tzinfo is None:
        raise OrbitDeterminationError("Reference epoch must be timezone-aware.")
    a_km, eccentricity, inclination, raan, argp, longitude = elements
    theta = earth_rotation_angle(utc_to_et(epoch))
    inertial_longitude = np.radians(longitude) + theta
    node = np.radians(raan)
    inclination_rad = np.radians(inclination)
    delta = inertial_longitude - node
    argument_of_latitude = np.arctan2(
        np.sin(delta) / np.cos(inclination_rad),
        np.cos(delta),
    )
    true_anomaly = np.degrees(argument_of_latitude) - argp
    of_date_state = keplerian_to_cartesian({
        "a_km": a_km,
        "e": eccentricity,
        "i_deg": inclination,
        "raan_deg": raan,
        "argp_deg": argp,
        "nu_deg": true_anomaly,
    }, mu=MU_EARTH)
    cosine = np.cos(theta)
    sine = np.sin(theta)
    of_date_to_itrs = np.array([
        [cosine, sine, 0.0],
        [-sine, cosine, 0.0],
        [0.0, 0.0, 1.0],
    ])
    j2000_to_itrs = j2000_to_itrs_rotation_from_datetime(
        epoch, eop_enabled=False
    )
    state = np.empty(6, dtype=float)
    state[:3] = j2000_to_itrs.T @ (of_date_to_itrs @ of_date_state[:3])
    state[3:] = j2000_to_itrs.T @ (of_date_to_itrs @ of_date_state[3:])
    return state


def _post_discontinuity_records(records):
    records = tuple(records)
    result = []
    for index, record in enumerate(records):
        if record.discontinuity:
            continue
        if result and record.epoch == result[-1].epoch:
            result[-1] = record
        else:
            result.append(record)
    return tuple(result)


def reference_state_at(dataset: OrbitDeterminationDataset, epoch: datetime):
    """Interpolate a continuous reference state and convert it to J2000."""

    if epoch.tzinfo is None:
        raise OrbitDeterminationError("Arc epoch must be timezone-aware.")
    records = _post_discontinuity_records(dataset.reference_orbit)
    seconds = np.array([
        (record.epoch - records[0].epoch).total_seconds() for record in records
    ])
    target = (epoch - records[0].epoch).total_seconds()
    if target < seconds[0] or target > seconds[-1]:
        raise OrbitDeterminationError("Arc epoch is outside the reference orbit.")
    values = np.array([record.elements for record in records], dtype=float)
    for column in (2, 3, 4, 5):
        values[:, column] = np.degrees(np.unwrap(np.radians(values[:, column])))
    interpolated = np.array([
        np.interp(target, seconds, values[:, column]) for column in range(6)
    ])
    return reference_elements_to_j2000(interpolated, epoch)


def reference_state_jumps(dataset, arc_start, arc_end):
    """Return fixed J2000 state jumps encoded by duplicate discontinuity rows."""

    records = dataset.reference_orbit
    jumps = []
    for index, before in enumerate(records[:-1]):
        after = records[index + 1]
        if (
            before.discontinuity
            and before.epoch == after.epoch
            and arc_start < before.epoch <= arc_end
        ):
            before_state = reference_elements_to_j2000(before.elements, before.epoch)
            after_state = reference_elements_to_j2000(after.elements, after.epoch)
            jumps.append((before.epoch, after_state - before_state))
    return tuple(jumps)


def predict_observation(state, measurement: Measurement, station: GroundStation):
    """Predict one bias-aware ground observation from a J2000 state."""

    position = np.asarray(state, dtype=float)[:3]
    rotation = j2000_to_itrs_rotation_from_datetime(
        measurement.epoch, eop_enabled=False
    )
    line_of_sight = rotation @ position - _geodetic_to_ecef(station)
    distance = float(np.linalg.norm(line_of_sight))
    latitude = np.radians(station.latitude_deg)
    longitude = np.radians(station.longitude_deg)
    east = -np.sin(longitude) * line_of_sight[0] + np.cos(longitude) * line_of_sight[1]
    north = (
        -np.sin(latitude) * np.cos(longitude) * line_of_sight[0]
        - np.sin(latitude) * np.sin(longitude) * line_of_sight[1]
        + np.cos(latitude) * line_of_sight[2]
    )
    up = (
        np.cos(latitude) * np.cos(longitude) * line_of_sight[0]
        + np.cos(latitude) * np.sin(longitude) * line_of_sight[1]
        + np.sin(latitude) * line_of_sight[2]
    )
    if measurement.measurement_type == "Range":
        computed = distance
    elif measurement.measurement_type == "Azimuth":
        computed = float(np.degrees(np.arctan2(east, north)) % 360.0)
    elif measurement.measurement_type == "Elevation":
        computed = float(np.degrees(np.arcsin(up / distance)))
        computed += _atmospheric_refraction_deg(computed, station)
    else:
        raise OrbitDeterminationError(
            f"Unsupported measurement type: {measurement.measurement_type}"
        )
    return computed + station.biases[measurement.measurement_type]


def _file_ephemeris_states(dataset, epochs, cancel_check=None):
    """Read/interpolate the supplied orbit file at the requested epochs."""

    states = []
    for epoch in epochs:
        if cancel_check is not None and cancel_check():
            raise OrbitDeterminationCancelled("Orbit determination cancelled.")
        states.append(reference_state_at(dataset, epoch))
    return np.asarray(states, dtype=float)


def _apply_linear_state_correction(
    file_states,
    epochs,
    initial_epoch,
    initial_state,
    file_initial_state,
):
    """Apply the LS six-state correction around the supplied file ephemeris."""

    correction = _validate_state(initial_state) - _validate_state(file_initial_state)
    seconds = np.asarray([
        (epoch - initial_epoch).total_seconds() for epoch in epochs
    ], dtype=float)
    corrected = np.asarray(file_states, dtype=float).copy()
    corrected[:, :3] += correction[:3] + seconds[:, None] * correction[3:]
    corrected[:, 3:] += correction[3:]
    return corrected


@lru_cache(maxsize=1)
def _synthetic_dataset() -> OrbitDeterminationDataset:
    """Create a deterministic, fictional OD dataset entirely in memory."""

    stations = {
        "DEMO-A": GroundStation(
            station_id="DEMO-A",
            name="SYNTHETIC STATION A",
            latitude_deg=10.0,
            longitude_deg=-20.0,
            height_km=0.10,
            temperature_c=15.0,
            pressure_mbar=1013.25,
            humidity_percent=40.0,
            biases={"Range": 0.0, "Azimuth": 0.0, "Elevation": 0.0},
            noises={"Range": 0.05, "Azimuth": 0.005, "Elevation": 0.005},
            range_ambiguity_km=0.0,
        ),
        "DEMO-B": GroundStation(
            station_id="DEMO-B",
            name="SYNTHETIC STATION B",
            latitude_deg=-25.0,
            longitude_deg=80.0,
            height_km=0.25,
            temperature_c=18.0,
            pressure_mbar=1000.0,
            humidity_percent=35.0,
            biases={"Range": 0.0, "Azimuth": 0.0, "Elevation": 0.0},
            noises={"Range": 0.05, "Azimuth": 0.005, "Elevation": 0.005},
            range_ambiguity_km=0.0,
        ),
    }
    epoch = datetime(2030, 1, 1, tzinfo=timezone.utc)
    records = tuple(
        ReferenceOrbitRecord(
            epoch=epoch + timedelta(hours=2 * index),
            elements=np.asarray(
                [42164.0, 0.001, 0.05, 4.0, 12.0, 12.0], dtype=float
            ),
            cp_scale_factor=1.0,
            discontinuity=False,
        )
        for index in range(13)
    )
    empty_dataset = OrbitDeterminationDataset(
        dataset_id="synthetic-od-demo-v1",
        display_name="SYNTHETIC/DEMO ORBIT DETERMINATION",
        frame_note="Fictional public J2000/WGS-84 training data",
        spacecraft_mass_kg=1000.0,
        cp_scale_factor=1.0,
        stations=stations,
        measurements=(),
        reference_orbit=records,
        source_directory=Path("SYNTHETIC_DEMO_MEMORY"),
    )
    estimation_epoch = epoch + timedelta(hours=12)
    file_initial_state = reference_state_at(empty_dataset, estimation_epoch)
    intended_state = file_initial_state + np.asarray(
        [0.8, -0.5, 0.3, 1.5e-5, -1.0e-5, 0.5e-5], dtype=float
    )
    measurements: list[Measurement] = []
    measurement_id = 1
    for record in records:
        file_state = reference_state_at(empty_dataset, record.epoch)
        corrected_state = _apply_linear_state_correction(
            np.asarray([file_state]),
            (record.epoch,),
            estimation_epoch,
            intended_state,
            file_initial_state,
        )[0]
        for station in stations.values():
            for measurement_type in SUPPORTED_MEASUREMENT_TYPES:
                placeholder = Measurement(
                    measurement_id=measurement_id,
                    quality_factor=1,
                    station_id=station.station_id,
                    measurement_type=measurement_type,
                    epoch=record.epoch,
                    value=0.0,
                )
                value = predict_observation(corrected_state, placeholder, station)
                measurements.append(
                    Measurement(
                        measurement_id=measurement_id,
                        quality_factor=1,
                        station_id=station.station_id,
                        measurement_type=measurement_type,
                        epoch=record.epoch,
                        value=float(value),
                    )
                )
                measurement_id += 1
    return OrbitDeterminationDataset(
        dataset_id=empty_dataset.dataset_id,
        display_name=empty_dataset.display_name,
        frame_note=empty_dataset.frame_note,
        spacecraft_mass_kg=empty_dataset.spacecraft_mass_kg,
        cp_scale_factor=empty_dataset.cp_scale_factor,
        stations=stations,
        measurements=tuple(measurements),
        reference_orbit=records,
        source_directory=empty_dataset.source_directory,
    )


def _arc_measurements(dataset, arc_start, arc_end):
    if arc_start.tzinfo is None or arc_end.tzinfo is None:
        raise OrbitDeterminationError("OD arc bounds must be timezone-aware.")
    if arc_end <= arc_start:
        raise OrbitDeterminationError("OD arc end must be after its start.")
    selected = tuple(
        item for item in dataset.measurements
        if arc_start <= item.epoch <= arc_end and item.quality_factor >= 0
    )
    if len(selected) < 7:
        raise OrbitDeterminationError(
            "The selected arc needs at least seven valid measurements."
        )
    return selected


def _predictions(
    initial_state,
    initial_epoch,
    measurements,
    dataset,
    file_states,
    file_initial_state,
):
    epochs = tuple(item.epoch for item in measurements)
    states = _apply_linear_state_correction(
        file_states,
        epochs,
        initial_epoch,
        initial_state,
        file_initial_state,
    )
    return np.asarray([
        predict_observation(state, measurement, dataset.stations[measurement.station_id])
        for state, measurement in zip(states, measurements)
    ], dtype=float)


def _residuals(observed, predicted, measurements):
    residuals = np.asarray(observed, dtype=float) - np.asarray(predicted, dtype=float)
    angular = np.array([
        item.measurement_type == "Azimuth" for item in measurements
    ], dtype=bool)
    residuals[angular] = _wrap_degrees(residuals[angular])
    return residuals


def _noise_vector(measurements, dataset):
    return np.asarray([
        dataset.stations[item.station_id].noises[item.measurement_type]
        for item in measurements
    ], dtype=float)


def _weighted_rms(residuals, noises, mask=None):
    if mask is None:
        mask = np.ones(len(residuals), dtype=bool)
    return float(np.sqrt(np.mean((residuals[mask] / noises[mask]) ** 2)))


def _summaries(dataset, measurements, noises, prefit, postfit, accepted):
    summaries = []
    keys = sorted({(item.station_id, item.measurement_type) for item in measurements})
    for station_id, measurement_type in keys:
        group = np.array([
            item.station_id == station_id and item.measurement_type == measurement_type
            for item in measurements
        ], dtype=bool)
        used = group & accepted
        if not np.any(used):
            used = group
        summaries.append(ResidualSummary(
            station_id=station_id,
            station_name=dataset.stations[station_id].name,
            measurement_type=measurement_type,
            noise=float(noises[group][0]),
            count=int(np.sum(group)),
            rejected=int(np.sum(group & ~accepted)),
            prefit_mean=float(np.mean(prefit[group])),
            prefit_rms=float(np.sqrt(np.mean(prefit[group] ** 2))),
            postfit_mean=float(np.mean(postfit[used])),
            postfit_rms=float(np.sqrt(np.mean(postfit[used] ** 2))),
        ))
    return tuple(summaries)


def _reference_validation(
    dataset,
    estimation_epoch,
    arc_start,
    arc_end,
    initial_state,
    corrected_state,
    cancel_check,
):
    records = tuple(
        item for item in _post_discontinuity_records(dataset.reference_orbit)
        if arc_start <= item.epoch <= arc_end
    )
    epochs = tuple(item.epoch for item in records)
    if not epochs:
        empty_states = np.empty((0, 6), dtype=float)
        empty_errors = np.empty(0, dtype=float)
        return (
            (), empty_states, empty_states.copy(), empty_states.copy(),
            empty_errors, empty_errors.copy(), empty_errors.copy(),
            empty_errors.copy(),
        )
    reference_states = _file_ephemeris_states(dataset, epochs, cancel_check)
    file_initial_state = reference_state_at(dataset, estimation_epoch)
    prefit_states = _apply_linear_state_correction(
        reference_states, epochs, estimation_epoch, initial_state, file_initial_state,
    )
    postfit_states = _apply_linear_state_correction(
        reference_states, epochs, estimation_epoch, corrected_state, file_initial_state,
    )
    return (
        epochs,
        reference_states,
        prefit_states,
        postfit_states,
        np.linalg.norm(prefit_states[:, :3] - reference_states[:, :3], axis=1),
        np.linalg.norm(postfit_states[:, :3] - reference_states[:, :3], axis=1),
        np.linalg.norm(prefit_states[:, 3:] - reference_states[:, 3:], axis=1),
        np.linalg.norm(postfit_states[:, 3:] - reference_states[:, 3:], axis=1),
    )


def fit_weighted_least_squares(
    dataset: OrbitDeterminationDataset,
    arc_start: datetime,
    arc_end: datetime,
    *,
    initial_state: np.ndarray | None = None,
    max_iterations: int = 4,
    rejection_sigma: float = 3.0,
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
):
    """Estimate the selected arc's initial J2000 state by weighted LS."""

    max_iterations = int(max_iterations)
    rejection_sigma = float(rejection_sigma)
    if max_iterations < 1 or max_iterations > 12:
        raise OrbitDeterminationError("Iterations must be between 1 and 12.")
    if not np.isfinite(rejection_sigma) or rejection_sigma < 2.0:
        raise OrbitDeterminationError("Rejection threshold must be at least 2 sigma.")
    measurements = _arc_measurements(dataset, arc_start, arc_end)
    observed = np.asarray([item.value for item in measurements], dtype=float)
    noises = _noise_vector(measurements, dataset)
    estimation_epoch = arc_start + (arc_end - arc_start) / 2
    file_initial_state = reference_state_at(dataset, estimation_epoch)
    if initial_state is None:
        initial_state = file_initial_state.copy()
    else:
        initial_state = _validate_state(initial_state).copy()
    jumps = reference_state_jumps(dataset, arc_start, arc_end)
    measurement_epochs = tuple(item.epoch for item in measurements)
    file_measurement_states = _file_ephemeris_states(
        dataset, measurement_epochs, cancel_check
    )
    perturbations = np.array([0.01, 0.01, 0.01, 1.0e-6, 1.0e-6, 1.0e-6])
    current_state = initial_state.copy()
    accepted = np.ones(len(measurements), dtype=bool)
    total_evaluations = max_iterations * 8 + 4
    evaluation_count = 0

    def report(stage):
        if progress_callback is not None:
            progress_callback(
                min(99, int(100 * evaluation_count / total_evaluations)),
                stage,
            )

    def evaluate(state, stage):
        nonlocal evaluation_count
        if cancel_check is not None and cancel_check():
            raise OrbitDeterminationCancelled("Orbit determination cancelled.")
        report(stage)
        predicted = _predictions(
            state,
            estimation_epoch,
            measurements,
            dataset,
            file_measurement_states,
            file_initial_state,
        )
        evaluation_count += 1
        residual = _residuals(observed, predicted, measurements)
        return predicted, residual

    predicted_prefit, residuals_prefit = evaluate(initial_state, "PREFIT PROPAGATION")
    previous_rms = _weighted_rms(residuals_prefit, noises, accepted)
    converged = False
    final_design = None
    completed_iterations = 0

    for iteration in range(1, max_iterations + 1):
        completed_iterations = iteration
        predicted, residual = evaluate(current_state, f"ITERATION {iteration} · NOMINAL")
        design = np.empty((len(measurements), 6), dtype=float)
        for column, step in enumerate(perturbations):
            perturbed = current_state.copy()
            perturbed[column] += step
            predicted_step, _unused = evaluate(
                perturbed, f"ITERATION {iteration} · JACOBIAN {column + 1}/6"
            )
            derivative = predicted_step - predicted
            azimuth = np.array([
                item.measurement_type == "Azimuth" for item in measurements
            ], dtype=bool)
            derivative[azimuth] = _wrap_degrees(derivative[azimuth])
            design[:, column] = derivative / step / noises
        weighted_target = residual / noises
        active_design = design[accepted]
        active_target = weighted_target[accepted]
        correction, *_ = np.linalg.lstsq(active_design, active_target, rcond=1.0e-12)
        position_norm = float(np.linalg.norm(correction[:3]))
        velocity_norm = float(np.linalg.norm(correction[3:]))
        scale = min(
            1.0,
            10.0 / position_norm if position_norm > 10.0 else 1.0,
            0.01 / velocity_norm if velocity_norm > 0.01 else 1.0,
        )
        correction *= scale

        best_state = current_state
        best_predicted = predicted
        best_residual = residual
        best_rms = _weighted_rms(residual, noises, accepted)
        step_factor = 1.0
        while step_factor >= 0.0625:
            candidate = current_state + correction * step_factor
            candidate_predicted, candidate_residual = evaluate(
                candidate, f"ITERATION {iteration} · LINE SEARCH"
            )
            candidate_rms = _weighted_rms(candidate_residual, noises, accepted)
            if candidate_rms < best_rms:
                best_state = candidate
                best_predicted = candidate_predicted
                best_residual = candidate_residual
                best_rms = candidate_rms
                break
            step_factor *= 0.5
        applied = best_state - current_state
        current_state = best_state
        final_design = design

        if iteration >= 2:
            normalized = np.abs(best_residual / noises)
            candidate_mask = normalized <= rejection_sigma
            if np.sum(candidate_mask) >= 7:
                accepted = candidate_mask
                best_rms = _weighted_rms(best_residual, noises, accepted)
        if (
            np.linalg.norm(applied[:3]) < 1.0e-4
            and np.linalg.norm(applied[3:]) < 1.0e-8
        ) or abs(previous_rms - best_rms) < 1.0e-5:
            converged = True
            break
        previous_rms = best_rms

    predicted_postfit, residuals_postfit = evaluate(
        current_state, "POSTFIT PROPAGATION"
    )
    if final_design is None:
        raise OrbitDeterminationError("Least-squares design matrix was not formed.")
    active_design = final_design[accepted]
    normal_matrix = active_design.T @ active_design
    condition_number = float(np.linalg.cond(normal_matrix))
    degrees_of_freedom = max(1, int(np.sum(accepted)) - 6)
    variance_factor = float(np.sum(
        (residuals_postfit[accepted] / noises[accepted]) ** 2
    ) / degrees_of_freedom)
    covariance = np.linalg.pinv(normal_matrix, rcond=1.0e-12) * variance_factor
    parameter_sigmas = np.sqrt(np.maximum(0.0, np.diag(covariance)))

    report("REFERENCE VALIDATION")
    (
        reference_epochs,
        determination_file_states,
        determination_prefit_states,
        determination_postfit_states,
        reference_position_prefit,
        reference_position_postfit,
        reference_velocity_prefit,
        reference_velocity_postfit,
    ) = _reference_validation(
        dataset, estimation_epoch, arc_start, arc_end,
        initial_state, current_state, cancel_check,
    )
    noon_epoch = arc_start.astimezone(timezone.utc).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    if noon_epoch < arc_start:
        noon_epoch += timedelta(days=1)
    noon_position_prefit = noon_position_postfit = None
    noon_velocity_prefit = noon_velocity_postfit = None
    if arc_start <= noon_epoch <= arc_end:
        noon_file_state = _file_ephemeris_states(
            dataset, (noon_epoch,), cancel_check
        )
        noon_prefit_state = _apply_linear_state_correction(
            noon_file_state, (noon_epoch,), estimation_epoch,
            initial_state, file_initial_state,
        )[0]
        noon_postfit_state = _apply_linear_state_correction(
            noon_file_state, (noon_epoch,), estimation_epoch,
            current_state, file_initial_state,
        )[0]
        noon_position_prefit = float(np.linalg.norm(
            noon_prefit_state[:3] - noon_file_state[0, :3]
        ))
        noon_position_postfit = float(np.linalg.norm(
            noon_postfit_state[:3] - noon_file_state[0, :3]
        ))
        noon_velocity_prefit = float(np.linalg.norm(
            noon_prefit_state[3:] - noon_file_state[0, 3:]
        ))
        noon_velocity_postfit = float(np.linalg.norm(
            noon_postfit_state[3:] - noon_file_state[0, 3:]
        ))
    if progress_callback is not None:
        progress_callback(100, "COMPLETED")
    return OrbitDeterminationResult(
        dataset_id=dataset.dataset_id,
        arc_start=arc_start,
        arc_end=arc_end,
        estimation_epoch=estimation_epoch,
        initial_state=initial_state,
        corrected_state=current_state,
        state_correction=current_state - initial_state,
        covariance=covariance,
        parameter_sigmas=parameter_sigmas,
        condition_number=condition_number,
        iterations=completed_iterations,
        converged=converged,
        weighted_rms_prefit=_weighted_rms(residuals_prefit, noises),
        weighted_rms_postfit=_weighted_rms(residuals_postfit, noises, accepted),
        measurements=measurements,
        predicted_prefit=predicted_prefit,
        predicted_postfit=predicted_postfit,
        residuals_prefit=residuals_prefit,
        residuals_postfit=residuals_postfit,
        accepted_mask=accepted,
        summaries=_summaries(
            dataset, measurements, noises, residuals_prefit,
            residuals_postfit, accepted,
        ),
        reference_epochs=reference_epochs,
        determination_file_states=determination_file_states,
        determination_prefit_states=determination_prefit_states,
        determination_postfit_states=determination_postfit_states,
        reference_position_errors_prefit_km=reference_position_prefit,
        reference_position_errors_postfit_km=reference_position_postfit,
        reference_velocity_errors_prefit_km_s=reference_velocity_prefit,
        reference_velocity_errors_postfit_km_s=reference_velocity_postfit,
        state_jump_count=len(jumps),
        noon_epoch=noon_epoch if arc_start <= noon_epoch <= arc_end else None,
        noon_position_error_prefit_km=noon_position_prefit,
        noon_position_error_postfit_km=noon_position_postfit,
        noon_velocity_error_prefit_km_s=noon_velocity_prefit,
        noon_velocity_error_postfit_km_s=noon_velocity_postfit,
    )
