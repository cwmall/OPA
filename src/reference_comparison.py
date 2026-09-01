"""Repeatable validation against the supplied 30-day reference series."""

import csv
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter

import numpy as np
from skyfield.api import load as skyfield_load
from skyfield.framelib import itrs, true_equator_and_equinox_of_date
from skyfield.functions import mxv

from constants import DEFAULT_ATOL, DEFAULT_MAX_STEP, DEFAULT_RTOL
from application_config import default_application_config_path
from earth_orientation import get_eop_status, skyfield_time_from_datetimes
from propagator import propagate_trajectory
from time_utils import format_csv_date, format_csv_time


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEMO_REFERENCE_DIR = PROJECT_DIR / "demo_data" / "reference"
REFERENCE_DIR = default_application_config_path().parent / "references"
REFERENCE_EPOCH = datetime(2030, 1, 1, tzinfo=timezone.utc)
REFERENCE_STEP_SECONDS = 3600.0
REFERENCE_ROWS = 25

DEFAULT_REFERENCE_DATASET_ID = "synthetic-demo-earth-moon"
SECOND_REFERENCE_DATASET_ID = DEFAULT_REFERENCE_DATASET_ID
EARTH_SUN_REFERENCE_DATASET_ID = "synthetic-demo-earth-sun"
EARTH_MOON_SUN_REFERENCE_DATASET_ID = "synthetic-demo-earth-moon-sun"
SUN_MOON_COMPARISON_DATASET_ID = "synthetic-demo-sun-moon-comparison"
DEMO_EARTH_MOON_SUN_SRP_DATASET_ID = "synthetic-demo-full-srp"

_DEMO_SRP_PARAMETERS = {
    "area_m2": 18.0,
    "mass_kg": 1000.0,
    "coefficient": 1.2,
    "mode": "SYNTHETIC/DEMO",
}


def _demo_scenario(name, filename, sha256):
    return {
        "name": name,
        "path": DEMO_REFERENCE_DIR / filename,
        "sha256": sha256,
        "format": "csv_j2000",
    }


REFERENCE_DATASETS = {
    DEFAULT_REFERENCE_DATASET_ID: {
        "id": DEFAULT_REFERENCE_DATASET_ID,
        "label": "SYNTHETIC/DEMO — Earth and Moon",
        "short_label": "SYNTHETIC Earth/Moon",
        "source": "Generated fictional trajectory; see demo-data notice",
        "epoch": REFERENCE_EPOCH,
        "step_seconds": REFERENCE_STEP_SECONDS,
        "rows": REFERENCE_ROWS,
        "source_frame": "ECI J2000/ICRF",
        "model_frame": "ECI J2000/ICRF",
        "scenarios": {
            False: _demo_scenario("SYNTHETIC EARTH", "demo_earth.csv", "80f1c48f6e44ee9b6aedb97331272f8f357e798ef438c19f3328fc2f06dc911a"),
            True: _demo_scenario("SYNTHETIC EARTH + MOON", "demo_earth_moon.csv", "99d36e30c5ffefbdfebe59279d9d283f49e32a1acb3eaa647e46607ab5a73a8e"),
        },
        "srp_scenarios": {
            False: _demo_scenario("SYNTHETIC EARTH + SRP", "demo_earth_srp.csv", "fb0d90915b429e9ea1a125ba36774eacfc59918d83519f0db1dd0bf1cf62ff68"),
            True: _demo_scenario("SYNTHETIC EARTH + MOON + SRP", "demo_earth_moon_srp.csv", "f4c5f8aa601afc3d539893c8a72e65e95a8fe4bb9fd5f3e9bbdab3e4687d5557"),
        },
        "srp_parameters": _DEMO_SRP_PARAMETERS,
        "satellite_name": "SYNTHETIC GEO DEMO",
    },
    EARTH_SUN_REFERENCE_DATASET_ID: {
        "id": EARTH_SUN_REFERENCE_DATASET_ID,
        "label": "SYNTHETIC/DEMO — Earth and Sun",
        "short_label": "SYNTHETIC Earth/Sun",
        "source": "Generated fictional trajectory; see demo-data notice",
        "epoch": REFERENCE_EPOCH,
        "step_seconds": REFERENCE_STEP_SECONDS,
        "rows": REFERENCE_ROWS,
        "source_frame": "ECI J2000/ICRF",
        "model_frame": "ECI J2000/ICRF",
        "required_force_model": {"include_moon": False, "include_sun": True},
        "scenarios": {False: _demo_scenario("SYNTHETIC EARTH + SUN", "demo_earth_sun.csv", "88cea68b3cec68f1d8b8f228ea4a668d0fa8a98385d3217b53f6fdb3c83bb939")},
        "srp_scenarios": {False: _demo_scenario("SYNTHETIC EARTH + SUN + SRP", "demo_earth_sun_srp.csv", "ed2f5db6ed0ef968863c76bb1f6a8f03148aadb62b5737237030cc7de7494c34")},
        "srp_parameters": _DEMO_SRP_PARAMETERS,
        "satellite_name": "SYNTHETIC GEO DEMO",
    },
    EARTH_MOON_SUN_REFERENCE_DATASET_ID: {
        "id": EARTH_MOON_SUN_REFERENCE_DATASET_ID,
        "label": "SYNTHETIC/DEMO — Earth, Moon and Sun",
        "short_label": "SYNTHETIC Earth/Moon/Sun",
        "source": "Generated fictional trajectory; see demo-data notice",
        "epoch": REFERENCE_EPOCH,
        "step_seconds": REFERENCE_STEP_SECONDS,
        "rows": REFERENCE_ROWS,
        "source_frame": "ECI J2000/ICRF",
        "model_frame": "ECI J2000/ICRF",
        "required_force_model": {"include_moon": True, "include_sun": True},
        "scenarios": {True: _demo_scenario("SYNTHETIC EARTH + MOON + SUN", "demo_earth_moon_sun.csv", "ee976989f12fb8db12ee135c8d6454cb4b8802e33010a6a9fa9a15892093898b")},
        "srp_scenarios": {True: _demo_scenario("SYNTHETIC EARTH + MOON + SUN + SRP", "demo_earth_moon_sun_srp.csv", "f19bb18bbaaa17215210da44f131f244847327864410acc8be0afbb92db1a954")},
        "srp_parameters": _DEMO_SRP_PARAMETERS,
        "satellite_name": "SYNTHETIC GEO DEMO",
    },
    SUN_MOON_COMPARISON_DATASET_ID: {
        "id": SUN_MOON_COMPARISON_DATASET_ID,
        "label": "SYNTHETIC/DEMO — Sun baseline with Moon comparison",
        "short_label": "SYNTHETIC Sun/Moon comparison",
        "source": "Generated fictional trajectory; see demo-data notice",
        "epoch": REFERENCE_EPOCH,
        "step_seconds": REFERENCE_STEP_SECONDS,
        "rows": REFERENCE_ROWS,
        "source_frame": "ECI J2000/ICRF",
        "model_frame": "ECI J2000/ICRF",
        "required_force_model": {"include_sun": True},
        "scenarios": {
            False: _demo_scenario("SYNTHETIC EARTH + SUN", "demo_earth_sun.csv", "88cea68b3cec68f1d8b8f228ea4a668d0fa8a98385d3217b53f6fdb3c83bb939"),
            True: _demo_scenario("SYNTHETIC EARTH + MOON + SUN", "demo_earth_moon_sun.csv", "ee976989f12fb8db12ee135c8d6454cb4b8802e33010a6a9fa9a15892093898b"),
        },
        "srp_scenarios": {
            False: _demo_scenario("SYNTHETIC EARTH + SUN + SRP", "demo_earth_sun_srp.csv", "ed2f5db6ed0ef968863c76bb1f6a8f03148aadb62b5737237030cc7de7494c34"),
            True: _demo_scenario("SYNTHETIC EARTH + MOON + SUN + SRP", "demo_earth_moon_sun_srp.csv", "f19bb18bbaaa17215210da44f131f244847327864410acc8be0afbb92db1a954"),
        },
        "srp_parameters": _DEMO_SRP_PARAMETERS,
        "satellite_name": "SYNTHETIC GEO DEMO",
    },
    DEMO_EARTH_MOON_SUN_SRP_DATASET_ID: {
        "id": DEMO_EARTH_MOON_SUN_SRP_DATASET_ID,
        "label": "SYNTHETIC/DEMO — Full public force model",
        "short_label": "SYNTHETIC full-force model",
        "source": "Generated fictional trajectory; see demo-data notice",
        "epoch": REFERENCE_EPOCH,
        "step_seconds": REFERENCE_STEP_SECONDS,
        "rows": REFERENCE_ROWS,
        "source_frame": "ECI J2000/ICRF",
        "model_frame": "ECI J2000/ICRF",
        "required_force_model": {"include_moon": True, "include_sun": True, "include_srp": True},
        "scenarios": {},
        "srp_scenarios": {True: _demo_scenario("SYNTHETIC FULL FORCE MODEL", "demo_earth_moon_sun_srp.csv", "f19bb18bbaaa17215210da44f131f244847327864410acc8be0afbb92db1a954")},
        "srp_parameters": _DEMO_SRP_PARAMETERS,
        "satellite_name": "SYNTHETIC GEO DEMO",
    },
}

BUILTIN_REFERENCE_DATASET_IDS = frozenset(REFERENCE_DATASETS)
_SESSION_REFERENCE_DATASET_IDS = set()
USER_REFERENCE_MANIFEST_PATTERN = "*.opa-reference.json"
USER_REFERENCE_SCHEMA = "opa-reference/v1"
_USER_REFERENCE_DATASET_IDS = set()

_SKYFIELD_TIMESCALE = skyfield_load.timescale(builtin=True)
_LEGACY_REPORT_ROW_PATTERN = re.compile(
    r"^(\d{4}/\d{2}/\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2})\s+(.+)$"
)
_ECI_TEXT_ROW_PATTERN = re.compile(
    r"^(\d{4}/\d{2}/\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(.+)$"
)


class ReferenceDataError(RuntimeError):
    """Raised when bundled reference data is missing or inconsistent."""


def clear_session_reference_datasets():
    """Remove all decrypted in-memory admin references immediately."""

    for dataset_id in tuple(_SESSION_REFERENCE_DATASET_IDS):
        REFERENCE_DATASETS.pop(dataset_id, None)
    _SESSION_REFERENCE_DATASET_IDS.clear()
    _load_reference_scenario_cached.cache_clear()


def register_session_reference_datasets(datasets):
    """Register validated, data-only J2000 series for the current session."""

    clear_session_reference_datasets()
    for source in datasets:
        dataset_id = str(source["id"])
        if dataset_id in BUILTIN_REFERENCE_DATASET_IDS:
            raise ReferenceDataError(
                "Admin reference identifiers cannot replace public datasets."
            )
        epoch = _parse_utc(source["epoch_utc"])
        step_seconds = float(source["step_seconds"])
        rows = int(source["rows"])
        scenarios = {}
        srp_scenarios = {}
        for item in source["scenarios"]:
            states = np.asarray(item["states"], dtype=float).copy()
            states.setflags(write=False)
            scenario = {
                "name": str(item["name"]),
                "format": "memory_j2000",
                "states": states,
            }
            group = srp_scenarios if item["include_srp"] else scenarios
            group[bool(item["include_moon"])] = scenario
        REFERENCE_DATASETS[dataset_id] = {
            "id": dataset_id,
            "label": str(source["label"]),
            "short_label": str(source["label"]),
            "source": "Unlocked signed admin package (memory only)",
            "epoch": epoch,
            "step_seconds": step_seconds,
            "rows": rows,
            "source_frame": str(source["source_frame"]),
            "model_frame": "ECI J2000/ICRF",
            "required_force_model": dict(source["required_force_model"]),
            "scenarios": scenarios,
            "srp_scenarios": srp_scenarios,
            "srp_parameters": source.get("srp_parameters"),
            "admin_session": True,
            "satellite_name": "ADMIN SESSION SPACECRAFT",
        }
        _SESSION_REFERENCE_DATASET_IDS.add(dataset_id)
    _load_reference_scenario_cached.cache_clear()


def earth_fixed_longitude_degrees(states, epoch, elapsed_seconds):
    """Return continuous ITRS longitude for J2000 state positions [deg]."""

    states = np.asarray(states, dtype=float)
    elapsed_seconds = np.asarray(elapsed_seconds, dtype=float)
    if states.ndim != 2 or states.shape[1] < 3:
        raise ValueError("states must have shape (N, 3) or wider.")
    if elapsed_seconds.shape != (states.shape[0],):
        raise ValueError("elapsed_seconds must contain one value per state.")
    if not np.all(np.isfinite(states[:, :3])):
        raise ValueError("states contain non-finite positions.")
    if not np.all(np.isfinite(elapsed_seconds)):
        raise ValueError("elapsed_seconds contains non-finite values.")

    # A Greenwich-only z rotation is insufficient for vectors whose axes are
    # J2000/ICRF: it omits the date-dependent pole/equinox orientation and
    # displaced the October 2024 longitude by about 0.317 degrees.  ITRS
    # supplies the complete celestial-to-terrestrial rotation (precession,
    # nutation and Earth rotation; polar motion is zero without an EOP table).
    epochs = tuple(
        epoch + timedelta(seconds=float(seconds))
        for seconds in elapsed_seconds
    )
    times = skyfield_time_from_datetimes(epochs)
    j2000_to_itrs = itrs.rotation_at(times)
    fixed_positions = mxv(j2000_to_itrs, states[:, :3].T).T
    return np.degrees(
        np.unwrap(
            np.arctan2(fixed_positions[:, 1], fixed_positions[:, 0])
        )
    )


def _parse_utc(value):
    value = str(value).strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    epoch = datetime.fromisoformat(value)
    if epoch.tzinfo is None:
        raise ReferenceDataError("Reference epochs must be timezone-aware.")
    return epoch.astimezone(timezone.utc)


def get_reference_dataset(dataset_id=DEFAULT_REFERENCE_DATASET_ID):
    """Return one configured reference dataset or raise a clear error."""

    dataset_id = str(dataset_id)
    try:
        return REFERENCE_DATASETS[dataset_id]
    except KeyError as error:
        raise ReferenceDataError(
            f"Unknown reference dataset: {dataset_id}"
        ) from error


def list_reference_datasets():
    """Return dataset metadata in the order shown by the GUI."""

    return tuple(
        {
            key: value
            for key, value in dataset.items()
            if key not in {"scenarios", "srp_scenarios"}
        }
        | {
            "available_scenarios": tuple(dataset["scenarios"]),
            "available_srp_scenarios": tuple(
                dataset.get("srp_scenarios", {})
            ),
        }
        for dataset in REFERENCE_DATASETS.values()
    )


def reference_dataset_has_scenario(
    dataset_id,
    include_moon,
    include_srp=False,
):
    dataset = get_reference_dataset(dataset_id)
    scenario_group = (
        dataset.get("srp_scenarios", {})
        if include_srp
        else dataset["scenarios"]
    )
    return bool(include_moon) in scenario_group


def _read_csv_scenario(path):
    epochs = []
    states = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        expected_columns = {
            "epoch_utc",
            "x_km",
            "y_km",
            "z_km",
            "vx_km_s",
            "vy_km_s",
            "vz_km_s",
        }
        if set(reader.fieldnames or ()) != expected_columns:
            raise ReferenceDataError(
                f"Unexpected columns in {path.name}: {reader.fieldnames}"
            )
        for row in reader:
            epochs.append(_parse_utc(row["epoch_utc"]))
            states.append(
                [
                    float(row["x_km"]),
                    float(row["y_km"]),
                    float(row["z_km"]),
                    float(row["vx_km_s"]),
                    float(row["vy_km_s"]),
                    float(row["vz_km_s"]),
                ]
            )
    return epochs, np.asarray(states, dtype=float), 0


def _manifest_text(payload, key, manifest_path, *, default=None):
    value = payload.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ReferenceDataError(
            f"{manifest_path.name}: '{key}' must be non-empty text."
        )
    return value.strip()


def _manifest_bool(payload, key, manifest_path):
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ReferenceDataError(
            f"{manifest_path.name}: '{key}' must be true or false."
        )
    return value


def _positive_manifest_number(payload, key, manifest_path):
    try:
        value = float(payload[key])
    except (KeyError, TypeError, ValueError) as error:
        raise ReferenceDataError(
            f"{manifest_path.name}: '{key}' must be numeric."
        ) from error
    if not np.isfinite(value) or value <= 0.0:
        raise ReferenceDataError(
            f"{manifest_path.name}: '{key}' must be greater than zero."
        )
    return value


def _inspect_user_reference_csv(path, manifest_path):
    epochs, states, ignored_rows = _read_csv_scenario(path)
    if ignored_rows or len(epochs) < 2:
        raise ReferenceDataError(
            f"{manifest_path.name}: {path.name} must contain at least two rows."
        )
    if not np.all(np.isfinite(states)):
        raise ReferenceDataError(
            f"{manifest_path.name}: {path.name} contains non-finite values."
        )
    elapsed = np.asarray(
        [(epoch - epochs[0]).total_seconds() for epoch in epochs],
        dtype=float,
    )
    steps = np.diff(elapsed)
    if not np.all(steps > 0.0) or not np.all(steps == steps[0]):
        raise ReferenceDataError(
            f"{manifest_path.name}: {path.name} must use one exact cadence."
        )
    return {
        "epoch": epochs[0],
        "rows": len(epochs),
        "step_seconds": float(steps[0]),
    }


def _load_user_reference_manifest(manifest_path):
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReferenceDataError(
            f"Could not read {manifest_path.name}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise ReferenceDataError(
            f"{manifest_path.name}: manifest root must be a JSON object."
        )
    if payload.get("schema") != USER_REFERENCE_SCHEMA:
        raise ReferenceDataError(
            f"{manifest_path.name}: schema must be '{USER_REFERENCE_SCHEMA}'."
        )

    public_id = _manifest_text(payload, "id", manifest_path).lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,63}", public_id) is None:
        raise ReferenceDataError(
            f"{manifest_path.name}: id must contain 3–64 lowercase letters, "
            "digits, dots, underscores or hyphens."
        )
    dataset_id = f"user:{public_id}"
    label = _manifest_text(payload, "label", manifest_path)
    source_frame = _manifest_text(payload, "source_frame", manifest_path)
    if source_frame not in {"J2000/ICRF", "ECI J2000/ICRF"}:
        raise ReferenceDataError(
            f"{manifest_path.name}: source_frame must be J2000/ICRF or "
            "ECI J2000/ICRF."
        )

    satellite = payload.get("satellite")
    if not isinstance(satellite, dict):
        raise ReferenceDataError(
            f"{manifest_path.name}: 'satellite' must be a JSON object."
        )
    satellite_name = _manifest_text(
        satellite,
        "name",
        manifest_path,
    )
    norad_id = satellite.get("norad_id")
    if norad_id is not None:
        if isinstance(norad_id, bool):
            raise ReferenceDataError(
                f"{manifest_path.name}: norad_id must be a positive integer."
            )
        try:
            norad_id = int(norad_id)
        except (TypeError, ValueError) as error:
            raise ReferenceDataError(
                f"{manifest_path.name}: norad_id must be a positive integer."
            ) from error
        if norad_id <= 0:
            raise ReferenceDataError(
                f"{manifest_path.name}: norad_id must be a positive integer."
            )

    force_model = payload.get("force_model")
    if not isinstance(force_model, dict):
        raise ReferenceDataError(
            f"{manifest_path.name}: 'force_model' must be a JSON object."
        )
    include_sun = _manifest_bool(
        force_model,
        "include_sun",
        manifest_path,
    )

    scenario_entries = payload.get("scenarios")
    if not isinstance(scenario_entries, list) or not scenario_entries:
        raise ReferenceDataError(
            f"{manifest_path.name}: 'scenarios' must be a non-empty array."
        )

    scenarios = {}
    srp_scenarios = {}
    grid = None
    root = manifest_path.parent.resolve()
    scenario_modes = []
    for index, scenario_payload in enumerate(scenario_entries, start=1):
        if not isinstance(scenario_payload, dict):
            raise ReferenceDataError(
                f"{manifest_path.name}: scenario {index} must be an object."
            )
        scenario_name = _manifest_text(
            scenario_payload,
            "name",
            manifest_path,
        )
        include_moon = _manifest_bool(
            scenario_payload,
            "include_moon",
            manifest_path,
        )
        include_srp = _manifest_bool(
            scenario_payload,
            "include_srp",
            manifest_path,
        )
        relative_file = _manifest_text(
            scenario_payload,
            "file",
            manifest_path,
        )
        data_path = (root / relative_file).resolve()
        try:
            data_path.relative_to(root)
        except ValueError as error:
            raise ReferenceDataError(
                f"{manifest_path.name}: scenario files must stay beside or "
                "below the manifest."
            ) from error
        if data_path.suffix.lower() != ".csv" or not data_path.is_file():
            raise ReferenceDataError(
                f"{manifest_path.name}: CSV file not found: {relative_file}"
            )

        actual_hash = hashlib.sha256(data_path.read_bytes()).hexdigest()
        declared_hash = scenario_payload.get("sha256")
        if declared_hash is not None:
            declared_hash = str(declared_hash).strip().lower()
            if re.fullmatch(r"[0-9a-f]{64}", declared_hash) is None:
                raise ReferenceDataError(
                    f"{manifest_path.name}: scenario {index} has an invalid "
                    "sha256 value."
                )
            if declared_hash != actual_hash:
                raise ReferenceDataError(
                    f"{manifest_path.name}: SHA-256 mismatch for "
                    f"{data_path.name}."
                )

        inspected = _inspect_user_reference_csv(data_path, manifest_path)
        current_grid = (
            inspected["epoch"],
            inspected["rows"],
            inspected["step_seconds"],
        )
        if grid is None:
            grid = current_grid
        elif current_grid != grid:
            raise ReferenceDataError(
                f"{manifest_path.name}: every scenario must use the same "
                "epoch, row count and cadence."
            )

        group = srp_scenarios if include_srp else scenarios
        if include_moon in group:
            raise ReferenceDataError(
                f"{manifest_path.name}: duplicate Moon/SRP scenario mode."
            )
        group[include_moon] = {
            "name": scenario_name,
            "path": data_path,
            "sha256": actual_hash,
            "format": "csv_j2000",
            "user_supplied": True,
        }
        scenario_modes.append((include_moon, include_srp))

    srp_parameters = None
    if any(include_srp for _, include_srp in scenario_modes):
        srp_payload = payload.get("srp_parameters")
        if not isinstance(srp_payload, dict):
            raise ReferenceDataError(
                f"{manifest_path.name}: SRP scenarios require "
                "'srp_parameters'."
            )
        srp_parameters = {
            "area_m2": _positive_manifest_number(
                srp_payload, "area_m2", manifest_path
            ),
            "mass_kg": _positive_manifest_number(
                srp_payload, "mass_kg", manifest_path
            ),
            "coefficient": _positive_manifest_number(
                srp_payload, "coefficient", manifest_path
            ),
            "mode": "USER-SUPPLIED",
        }

    required_force_model = {"include_sun": include_sun}
    moon_modes = {include_moon for include_moon, _ in scenario_modes}
    srp_modes = {include_srp for _, include_srp in scenario_modes}
    if len(moon_modes) == 1:
        required_force_model["include_moon"] = next(iter(moon_modes))
    if len(srp_modes) == 1:
        required_force_model["include_srp"] = next(iter(srp_modes))

    epoch, rows, step_seconds = grid
    return {
        "id": dataset_id,
        "public_id": public_id,
        "label": label,
        "short_label": str(payload.get("short_label") or label).strip(),
        "source": str(
            payload.get("source") or f"User manifest — {manifest_path.name}"
        ).strip(),
        "satellite_name": satellite_name,
        "norad_id": norad_id,
        "epoch": epoch,
        "step_seconds": step_seconds,
        "rows": rows,
        "source_frame": source_frame,
        "model_frame": "ECI J2000/ICRF",
        "required_force_model": required_force_model,
        "srp_parameters": srp_parameters,
        "scenarios": scenarios,
        "srp_scenarios": srp_scenarios,
        "user_supplied": True,
        "manifest_path": manifest_path,
    }


def discover_user_reference_datasets(reference_dir=REFERENCE_DIR):
    """Read valid drop-in manifests without mutating the active registry."""

    reference_dir = Path(reference_dir)
    reference_dir.mkdir(parents=True, exist_ok=True)
    datasets = []
    errors = []
    seen_ids = set()
    for manifest_path in sorted(
        reference_dir.rglob(USER_REFERENCE_MANIFEST_PATTERN)
    ):
        try:
            dataset = _load_user_reference_manifest(manifest_path)
            if dataset["id"] in REFERENCE_DATASETS or dataset["id"] in seen_ids:
                raise ReferenceDataError(
                    f"{manifest_path.name}: duplicate reference id "
                    f"'{dataset['public_id']}'."
                )
            datasets.append(dataset)
            seen_ids.add(dataset["id"])
        except ReferenceDataError as error:
            errors.append(
                {
                    "manifest": manifest_path,
                    "error": str(error),
                }
            )
    return tuple(datasets), tuple(errors)


def reload_user_reference_datasets(reference_dir=REFERENCE_DIR):
    """Replace only drop-in datasets and clear cached reference states."""

    for dataset_id in tuple(_USER_REFERENCE_DATASET_IDS):
        REFERENCE_DATASETS.pop(dataset_id, None)
    _USER_REFERENCE_DATASET_IDS.clear()

    datasets, errors = discover_user_reference_datasets(reference_dir)
    for dataset in datasets:
        REFERENCE_DATASETS[dataset["id"]] = dataset
        _USER_REFERENCE_DATASET_IDS.add(dataset["id"])

    loader = globals().get("load_reference_scenario")
    cache_clear = getattr(loader, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    return {
        "reference_dir": Path(reference_dir),
        "datasets": datasets,
        "errors": errors,
        "loaded_count": len(datasets),
        "error_count": len(errors),
    }


def _rotate_tod_fk5_states_to_j2000(epochs, states):
    """Rotate external reference True-of-Date ECI vectors into J2000/ICRF axes.

    The report labels both position and velocity as ECI vectors, so the same
    orthogonal true-equator/equinox-of-date axis rotation is applied to both.
    No Earth-fixed rotation or empirical correction is introduced.
    """

    transformed = np.empty_like(states, dtype=float)
    for index, (epoch, state) in enumerate(zip(epochs, states)):
        skyfield_time = _SKYFIELD_TIMESCALE.from_datetime(epoch)
        rotation = true_equator_and_equinox_of_date.rotation_at(
            skyfield_time
        )
        transformed[index, :3] = rotation.T @ state[:3]
        transformed[index, 3:] = rotation.T @ state[3:]
    return transformed


def rotate_j2000_states_to_tod_fk5(epochs, states):
    """J2000/ICRF vəziyyətlərini external reference True-of-Date FK5 oxlarına çevir.

    Bu, referans yüklənərkən tətbiq edilən TOD→J2000 çevrilməsinin dəqiq
    tərsidir. external reference ECI sürətini vektor kimi verdiyi üçün mövqe və sürətə
    eyni ortoqonal fırlanma matrisi tətbiq olunur; empirik düzəliş yoxdur.
    """

    states = np.asarray(states, dtype=float)
    epochs = tuple(epochs)
    if states.ndim != 2 or states.shape[1] != 6:
        raise ValueError("states must have shape (N, 6).")
    if len(epochs) != states.shape[0]:
        raise ValueError("epochs must contain one value per state.")

    transformed = np.empty_like(states, dtype=float)
    for index, (epoch, state) in enumerate(zip(epochs, states)):
        skyfield_time = _SKYFIELD_TIMESCALE.from_datetime(epoch)
        rotation = true_equator_and_equinox_of_date.rotation_at(
            skyfield_time
        )
        transformed[index, :3] = rotation @ state[:3]
        transformed[index, 3:] = rotation @ state[3:]
    return transformed


def _read_legacy_report_scenario(path, dataset):
    text = path.read_text(encoding="utf-8", errors="replace")
    if "Equinox: True of Date FK5" not in text:
        raise ReferenceDataError(
            f"{path.name} is not marked as True of Date FK5."
        )
    parsed_rows = []
    for line in text.splitlines():
        match = _LEGACY_REPORT_ROW_PATTERN.match(line.strip())
        if match is None:
            continue
        values = match.group(3).split()
        if len(values) != 6:
            continue
        epoch = datetime.strptime(
            f"{match.group(1)} {match.group(2)}",
            "%Y/%m/%d %H:%M:%S",
        ).replace(tzinfo=timezone.utc)
        parsed_rows.append((epoch, [float(value) for value in values]))

    expected_epoch = dataset["epoch"]
    step_seconds = float(dataset["step_seconds"])
    expected_rows = int(dataset["rows"])
    grid_rows = {}
    # external reference faylın sonuna bəzən tələb edilən 900 saniyəlik şəbəkəyə düşməyən
    # dəqiq son-zaman sətri əlavə edir. Model və referansın hər sətri eyni epoxada
    # müqayisə olunsun deyə yalnız 0..2879 indeksləri saxlanılır; artıq sətir isə
    # gizlədilmədən hesabatda göstərilir.
    for epoch, state in parsed_rows:
        elapsed = (epoch - expected_epoch).total_seconds()
        sample_index = int(round(elapsed / step_seconds))
        if (
            0 <= sample_index < expected_rows
            and elapsed == sample_index * step_seconds
        ):
            if sample_index in grid_rows:
                raise ReferenceDataError(
                    f"Duplicate sample {sample_index} in {path.name}."
                )
            grid_rows[sample_index] = (epoch, state)
    if set(grid_rows) != set(range(expected_rows)):
        raise ReferenceDataError(
            f"{path.name} does not contain a complete 15-minute grid."
        )

    ordered_rows = [grid_rows[index] for index in range(expected_rows)]
    epochs = [row[0] for row in ordered_rows]
    source_states = np.asarray(
        [row[1] for row in ordered_rows],
        dtype=float,
    )
    states = _rotate_tod_fk5_states_to_j2000(epochs, source_states)
    return epochs, states, len(parsed_rows) - expected_rows


def _read_eci_j2000_text_scenario(path, dataset):
    """Read the user-supplied tab/space-separated ECI J2000 ephemeris."""

    parsed_rows = []
    text = path.read_text(encoding="utf-8", errors="strict")
    for line in text.splitlines():
        match = _ECI_TEXT_ROW_PATTERN.match(line.strip())
        if match is None:
            continue
        values = match.group(3).split()
        if len(values) != 6:
            continue
        epoch = datetime.strptime(
            f"{match.group(1)} {match.group(2)}",
            "%Y/%m/%d %H:%M:%S.%f",
        ).replace(tzinfo=timezone.utc)
        parsed_rows.append((epoch, [float(value) for value in values]))

    expected_epoch = dataset["epoch"]
    step_seconds = float(dataset["step_seconds"])
    expected_rows = int(dataset["rows"])
    if len(parsed_rows) != expected_rows:
        raise ReferenceDataError(
            f"{path.name} must contain {expected_rows} ECI rows; "
            f"found {len(parsed_rows)}."
        )
    epochs = [row[0] for row in parsed_rows]
    if epochs[0] != expected_epoch:
        raise ReferenceDataError(
            f"Unexpected first epoch in {path.name}: {epochs[0].isoformat()}"
        )
    expected_epochs = [
        expected_epoch + index * timedelta(seconds=step_seconds)
        for index in range(expected_rows)
    ]
    if epochs != expected_epochs:
        raise ReferenceDataError(
            f"{path.name} does not contain a complete "
            f"{step_seconds:.0f}-second grid."
        )
    return (
        epochs,
        np.asarray([row[1] for row in parsed_rows], dtype=float),
        0,
    )


@lru_cache(maxsize=64)
def _load_reference_scenario_cached(
    include_moon,
    dataset_id=DEFAULT_REFERENCE_DATASET_ID,
    include_srp=False,
    _file_fingerprint=None,
):
    """Load and validate one immutable reference scenario."""

    include_moon = bool(include_moon)
    include_srp = bool(include_srp)
    dataset = get_reference_dataset(dataset_id)
    scenario_group = (
        dataset.get("srp_scenarios", {})
        if include_srp
        else dataset["scenarios"]
    )
    try:
        scenario = scenario_group[include_moon]
    except KeyError as error:
        scenario_name = "WITH MOON" if include_moon else "WITHOUT MOON"
        raise ReferenceDataError(
            f"{dataset['label']} does not provide {scenario_name} "
            f"{'SRP/CP ' if include_srp else ''}data."
        ) from error

    path = scenario.get("path")
    if scenario["format"] != "memory_j2000":
        if path is None or not path.exists():
            raise ReferenceDataError("Reference file is unavailable.")
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_hash != scenario["sha256"]:
            raise ReferenceDataError("Reference integrity check failed.")

    try:
        if scenario["format"] == "memory_j2000":
            states = np.asarray(scenario["states"], dtype=float).copy()
            epochs = [
                dataset["epoch"] + index * timedelta(seconds=dataset["step_seconds"])
                for index in range(len(states))
            ]
            ignored_rows = 0
        elif scenario["format"] in {"csv", "csv_j2000", "csv_tod_fk5"}:
            epochs, states, ignored_rows = _read_csv_scenario(path)
            if scenario["format"] == "csv_tod_fk5":
                # İş kitabından ixrac edilən vektorlar eyni epoxadakı external reference TOD
                # vektorlarına uyğundur; J2000 propaqatoruna eyni fırlanma
                # çevrilməsi vasitəsilə daxil edilməlidir.
                states = _rotate_tod_fk5_states_to_j2000(epochs, states)
        elif scenario["format"] == "legacy_report_tod_fk5":
            epochs, states, ignored_rows = _read_legacy_report_scenario(
                path,
                dataset,
            )
        elif scenario["format"] == "eci_j2000_text":
            epochs, states, ignored_rows = _read_eci_j2000_text_scenario(
                path,
                dataset,
            )
        else:
            raise ReferenceDataError(
                f"Unsupported reference format: {scenario['format']}"
            )
    except ReferenceDataError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise ReferenceDataError(
            f"Could not read {path.name}: {error}"
        ) from error

    expected_rows = int(dataset["rows"])
    states = np.asarray(states, dtype=float)
    if states.shape != (expected_rows, 6):
        raise ReferenceDataError(
            f"{path.name} must contain {expected_rows} states; "
            f"found {states.shape}."
        )
    if not np.all(np.isfinite(states)):
        raise ReferenceDataError(f"{path.name} contains non-finite values.")
    if epochs[0] != dataset["epoch"]:
        raise ReferenceDataError(
            f"Unexpected first epoch in {path.name}: {epochs[0].isoformat()}"
        )

    elapsed = np.asarray(
        [(epoch - epochs[0]).total_seconds() for epoch in epochs],
        dtype=float,
    )
    expected_elapsed = np.arange(expected_rows, dtype=float) * float(
        dataset["step_seconds"]
    )
    if not np.array_equal(elapsed, expected_elapsed):
        raise ReferenceDataError(
            f"{path.name} must use an exact "
            f"{dataset['step_seconds']:.0f}-second cadence."
        )

    elapsed.setflags(write=False)
    states.setflags(write=False)
    return {
        "name": scenario["name"],
        "path": path,
        "epoch": epochs[0],
        "elapsed_seconds": elapsed,
        "states": states,
        "include_moon": include_moon,
        "include_srp": include_srp,
        "dataset_id": dataset["id"],
        "dataset_label": dataset["label"],
        "step_seconds": float(dataset["step_seconds"]),
        "rows": expected_rows,
        "source_frame": dataset["source_frame"],
        "model_frame": dataset["model_frame"],
        "ignored_terminal_rows": int(ignored_rows),
        "satellite_name": dataset.get("satellite_name", "SYNTHETIC GEO DEMO"),
        "srp_parameters": dataset.get("srp_parameters"),
    }


def load_reference_scenario(
    include_moon,
    dataset_id=DEFAULT_REFERENCE_DATASET_ID,
    include_srp=False,
):
    """Load a scenario, invalidating user CSV cache entries on file change."""

    dataset = get_reference_dataset(dataset_id)
    fingerprint = None
    if dataset.get("user_supplied"):
        scenario_group = (
            dataset.get("srp_scenarios", {})
            if include_srp
            else dataset.get("scenarios", {})
        )
        scenario = scenario_group.get(bool(include_moon))
        if scenario is not None:
            try:
                file_status = scenario["path"].stat()
                fingerprint = (
                    int(file_status.st_mtime_ns),
                    int(file_status.st_size),
                )
            except OSError:
                fingerprint = (None, None)
    return _load_reference_scenario_cached(
        bool(include_moon),
        str(dataset_id),
        bool(include_srp),
        fingerprint,
    )


load_reference_scenario.cache_clear = (
    _load_reference_scenario_cached.cache_clear
)
load_reference_scenario.cache_info = _load_reference_scenario_cached.cache_info


def _rtn_components(reference_state, delta_position):
    position = reference_state[:3]
    velocity = reference_state[3:]
    radial_hat = position / np.linalg.norm(position)
    normal_hat = np.cross(position, velocity)
    normal_hat = normal_hat / np.linalg.norm(normal_hat)
    along_hat = np.cross(normal_hat, radial_hat)
    return {
        "radial_km": float(np.dot(delta_position, radial_hat)),
        "along_track_km": float(np.dot(delta_position, along_hat)),
        "cross_track_km": float(np.dot(delta_position, normal_hat)),
    }


def _compare_one_scenario(
    include_moon,
    include_sun,
    include_srp,
    calibration_enabled,
    dataset_id,
    rtol,
    atol,
    max_step,
    cancel_check,
    progress_callback,
    manual_srp_overrides=None,
):
    reference = load_reference_scenario(
        include_moon,
        dataset_id,
        include_srp=include_srp,
    )
    elapsed = reference["elapsed_seconds"]
    reference_states = reference["states"]
    duration = float(elapsed[-1])
    srp_parameters = reference.get("srp_parameters") or {}
    srp_overrides = {}
    if include_srp and manual_srp_overrides:
        srp_overrides = {
            "srp_coefficient": float(
                manual_srp_overrides["srp_coefficient"]
            ),
            "srp_area_m2": float(manual_srp_overrides["srp_area_m2"]),
            "srp_mass_kg": float(manual_srp_overrides["srp_mass_kg"]),
        }
    elif include_srp and srp_parameters:
        srp_overrides = {
            "srp_coefficient": float(srp_parameters["coefficient"]),
            "srp_area_m2": float(srp_parameters["area_m2"]),
            "srp_mass_kg": float(srp_parameters["mass_kg"]),
        }

    times, model_states = propagate_trajectory(
        initial_state=reference_states[0],
        initial_epoch=reference["epoch"],
        duration_seconds=duration,
        output_step=reference["step_seconds"],
        include_j2=True,
        include_moon=include_moon,
        include_sun=include_sun,
        include_srp=include_srp,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
        cancel_check=cancel_check,
        progress_callback=progress_callback,
        **srp_overrides,
    )
    if not np.array_equal(times, elapsed):
        raise RuntimeError(
            f"{reference['name']} output epochs do not match the reference."
        )

    delta = np.asarray(model_states, dtype=float) - reference_states
    position_error = np.linalg.norm(delta[:, :3], axis=1)
    velocity_error = np.linalg.norm(delta[:, 3:], axis=1)
    metrics = {
        "final_position_error_km": float(position_error[-1]),
        "maximum_position_error_km": float(np.max(position_error)),
        "rms_position_error_km": float(
            np.sqrt(np.mean(position_error * position_error))
        ),
        "final_velocity_error_km_s": float(velocity_error[-1]),
        "maximum_velocity_error_km_s": float(np.max(velocity_error)),
        **_rtn_components(reference_states[-1], delta[-1, :3]),
    }
    return {
        **reference,
        "model_states": np.asarray(model_states, dtype=float),
        "delta": delta,
        "position_error_km": position_error,
        "velocity_error_km_s": velocity_error,
        "metrics": metrics,
        # Bu açıq sahələr ixrac və hesabat kodunda nəticənin yalnız fiziki
        # modeldən gəldiyini təsdiqləyir; uyğunlaşdırılmış miqyas DE440 nəticəsi
        # kimi səhv başa düşülə bilməz.
        "calibration_enabled": False,
        "moon_acceleration_scale": None,
        "include_sun": bool(include_sun),
        "include_srp": bool(include_srp),
        "srp_parameters_used": dict(srp_overrides),
        "eop_status": get_eop_status(),
    }


def _attach_longitude_series(scenario):
    scenario["reference_longitude_deg"] = earth_fixed_longitude_degrees(
        scenario["states"],
        scenario["epoch"],
        scenario["elapsed_seconds"],
    )
    scenario["model_longitude_deg"] = earth_fixed_longitude_degrees(
        scenario["model_states"],
        scenario["epoch"],
        scenario["elapsed_seconds"],
    )
    return scenario


def run_reference_scenario(
    include_moon,
    include_sun=False,
    include_srp=False,
    calibration_enabled=False,
    dataset_id=DEFAULT_REFERENCE_DATASET_ID,
    rtol=DEFAULT_RTOL,
    atol=DEFAULT_ATOL,
    max_step=DEFAULT_MAX_STEP,
    cancel_check=None,
    progress_callback=None,
    srp_overrides=None,
):
    """Run and validate one independently selectable reference scenario."""

    if calibration_enabled:
        # Köhnə çağırışlarda aydın xəta vermək üçün legacy arqument saxlanılır.
        # Onu səssiz qəbul etmək empirik hesablamanı fiziki nəticə kimi göstərə
        # bilərdi.
        raise ValueError(
            "Empirical calibration is disabled; reference validation is "
            "physical-only."
        )

    started = perf_counter()

    def map_progress(start, span):
        if progress_callback is None:
            return None

        def callback(value):
            progress_callback(
                min(100, int(start + span * float(value) / 100.0))
            )

        return callback

    scenario = _compare_one_scenario(
        bool(include_moon),
        bool(include_sun),
        bool(include_srp),
        bool(calibration_enabled),
        dataset_id,
        rtol,
        atol,
        max_step,
        cancel_check,
        map_progress(0, 50) if include_moon else progress_callback,
        srp_overrides,
    )

    # The bundled WITH/WITHOUT reference files start from slightly different
    # Cartesian states. To report a common-state lunar sensitivity for the
    # selected mode, also start the Moon run from the WITHOUT MOON state.
    if include_moon and reference_dataset_has_scenario(
        dataset_id,
        False,
        include_srp=include_srp,
    ):
        common_reference = load_reference_scenario(
            False,
            dataset_id,
            include_srp=include_srp,
        )
        common_times, common_states = propagate_trajectory(
            initial_state=common_reference["states"][0],
            initial_epoch=common_reference["epoch"],
            duration_seconds=float(
                common_reference["elapsed_seconds"][-1]
            ),
            output_step=common_reference["step_seconds"],
            include_j2=True,
            include_moon=True,
            include_sun=bool(include_sun),
            include_srp=bool(include_srp),
            rtol=rtol,
            atol=atol,
            max_step=max_step,
            cancel_check=cancel_check,
            progress_callback=map_progress(50, 50),
            **(
                dict(srp_overrides)
                if include_srp and srp_overrides
                else {
                    "srp_coefficient": float(
                        (common_reference.get("srp_parameters") or {})[
                            "coefficient"
                        ]
                    ),
                    "srp_area_m2": float(
                        (common_reference.get("srp_parameters") or {})[
                            "area_m2"
                        ]
                    ),
                    "srp_mass_kg": float(
                        (common_reference.get("srp_parameters") or {})[
                            "mass_kg"
                        ]
                    ),
                }
                if common_reference.get("srp_parameters")
                else {}
            ),
        )
        if not np.array_equal(
            common_times,
            common_reference["elapsed_seconds"],
        ):
            raise RuntimeError(
                "Common-state Moon output epochs do not match reference."
            )
        scenario["common_initial_model_states"] = np.asarray(
            common_states,
            dtype=float,
        )

    _attach_longitude_series(scenario)
    scenario["runtime_seconds"] = float(perf_counter() - started)
    return scenario


def combine_reference_scenarios(
    with_moon,
    without_moon,
    runtime_seconds=None,
):
    """Combine two completed scenario runs into Moon-effect metrics."""

    if not with_moon.get("include_moon", False):
        raise ValueError("with_moon must be a WITH MOON scenario result.")
    if without_moon.get("include_moon", True):
        raise ValueError(
            "without_moon must be a WITHOUT MOON scenario result."
        )
    if with_moon.get("dataset_id") != without_moon.get("dataset_id"):
        raise ValueError("Scenario reference datasets do not match.")
    include_sun = bool(with_moon.get("include_sun", False))
    if include_sun != bool(without_moon.get("include_sun", False)):
        raise ValueError("Scenario Sun force selections do not match.")
    include_srp = bool(with_moon.get("include_srp", False))
    if include_srp != bool(without_moon.get("include_srp", False)):
        raise ValueError("Scenario SRP force selections do not match.")
    with_srp_parameters = dict(with_moon.get("srp_parameters_used") or {})
    without_srp_parameters = dict(
        without_moon.get("srp_parameters_used") or {}
    )
    if with_srp_parameters != without_srp_parameters:
        raise ValueError("Scenario SRP parameters do not match.")
    calibration_enabled = bool(
        with_moon.get("calibration_enabled", False)
    )
    if calibration_enabled != bool(
        without_moon.get("calibration_enabled", False)
    ):
        raise ValueError("Scenario calibration modes do not match.")
    if with_moon["epoch"] != without_moon["epoch"]:
        raise ValueError("Scenario epochs do not match.")
    if not np.array_equal(
        with_moon["elapsed_seconds"],
        without_moon["elapsed_seconds"],
    ):
        raise ValueError("Scenario output epochs do not match.")

    reference_separation = np.linalg.norm(
        with_moon["states"][:, :3] - without_moon["states"][:, :3],
        axis=1,
    )
    model_separation = np.linalg.norm(
        with_moon["model_states"][:, :3]
        - without_moon["model_states"][:, :3],
        axis=1,
    )
    separation_difference = model_separation - reference_separation
    initial_position_separation = float(
        np.linalg.norm(
            with_moon["states"][0, :3]
            - without_moon["states"][0, :3]
        )
    )
    initial_velocity_separation = float(
        np.linalg.norm(
            with_moon["states"][0, 3:]
            - without_moon["states"][0, 3:]
        )
    )

    pure_moon_separation = None
    if "common_initial_model_states" in with_moon:
        pure_moon_separation = np.linalg.norm(
            with_moon["common_initial_model_states"][:, :3]
            - without_moon["model_states"][:, :3],
            axis=1,
        )
    if runtime_seconds is None:
        runtime_seconds = (
            float(with_moon.get("runtime_seconds", 0.0))
            + float(without_moon.get("runtime_seconds", 0.0))
        )

    result = {
        "epoch": with_moon["epoch"],
        "dataset_id": with_moon["dataset_id"],
        "dataset_label": with_moon["dataset_label"],
        "step_seconds": with_moon["step_seconds"],
        "elapsed_seconds": with_moon["elapsed_seconds"],
        "with_moon": with_moon,
        "without_moon": without_moon,
        "reference_separation_km": reference_separation,
        "model_separation_km": model_separation,
        "separation_difference_km": separation_difference,
        "final_reference_separation_km": float(reference_separation[-1]),
        "final_model_separation_km": float(model_separation[-1]),
        "final_separation_difference_km": float(separation_difference[-1]),
        "initial_position_separation_km": initial_position_separation,
        "initial_velocity_separation_km_s": initial_velocity_separation,
        "runtime_seconds": float(runtime_seconds),
        "calibration_enabled": False,
        "include_sun": include_sun,
        "include_srp": include_srp,
        "srp_parameters_used": with_srp_parameters,
        "moon_acceleration_scale": None,
        "eop_status": with_moon.get("eop_status", get_eop_status()),
    }
    if pure_moon_separation is not None:
        result.update(
            {
                "pure_moon_separation_km": pure_moon_separation,
                "final_pure_moon_separation_km": float(
                    pure_moon_separation[-1]
                ),
                "maximum_pure_moon_separation_km": float(
                    np.max(pure_moon_separation)
                ),
                "rms_pure_moon_separation_km": float(
                    np.sqrt(np.mean(pure_moon_separation**2))
                ),
            }
        )
    return result


def run_reference_comparison(
    calibration_enabled=False,
    dataset_id=DEFAULT_REFERENCE_DATASET_ID,
    rtol=DEFAULT_RTOL,
    atol=DEFAULT_ATOL,
    max_step=DEFAULT_MAX_STEP,
    cancel_check=None,
    progress_callback=None,
    srp_overrides=None,
):
    """Propagate WITH MOON and WITHOUT MOON and compare every row."""

    if calibration_enabled:
        raise ValueError(
            "Empirical calibration is disabled; reference validation is "
            "physical-only."
        )

    for include_moon in (True, False):
        if not reference_dataset_has_scenario(dataset_id, include_moon):
            scenario_name = "WITH MOON" if include_moon else "WITHOUT MOON"
            dataset = get_reference_dataset(dataset_id)
            raise ReferenceDataError(
                f"{dataset['label']} does not provide {scenario_name} data."
            )

    started = perf_counter()

    def map_progress(offset):
        if progress_callback is None:
            return None

        def callback(value):
            progress_callback(min(100, offset + int(value) // 2))

        return callback

    with_moon = run_reference_scenario(
        include_moon=True,
        calibration_enabled=calibration_enabled,
        dataset_id=dataset_id,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
        cancel_check=cancel_check,
        progress_callback=map_progress(0),
        srp_overrides=srp_overrides,
    )
    without_moon = run_reference_scenario(
        include_moon=False,
        calibration_enabled=calibration_enabled,
        dataset_id=dataset_id,
        rtol=rtol,
        atol=atol,
        max_step=max_step,
        cancel_check=cancel_check,
        progress_callback=map_progress(50),
        srp_overrides=srp_overrides,
    )

    if progress_callback is not None:
        progress_callback(100)

    return combine_reference_scenarios(
        with_moon,
        without_moon,
        runtime_seconds=perf_counter() - started,
    )


def _write_model_scenario_csv(scenario, file_path):
    """Model nəticəsini external reference-la müqayisə edilən başlıqsız CSV kimi yaz."""

    path = Path(file_path)

    elapsed_seconds = np.asarray(scenario["elapsed_seconds"], dtype=float)
    epochs = tuple(
        datetime.fromtimestamp(
            scenario["epoch"].timestamp() + float(elapsed),
            timezone.utc,
        )
        for elapsed in elapsed_seconds
    )
    # Propaqator J2000-da işləyir, lakin xarici ixrac external reference referansı ilə eyni
    # True-of-Date FK5 oxlarında olmalıdır. Beləliklə ilk sətir də daxil olmaqla
    # hər sətri Excel/Python-da birbaşa referansla müqayisə etmək mümkündür.
    # Export in the immutable reference dataset's own axes. external reference TOD/FK5
    # references require a J2000->TOD rotation, while the SYNTHETIC GEO DEMO source
    # is already J2000/ICRF and must not be rotated a second time.
    if scenario.get("source_frame") == scenario.get("model_frame"):
        export_states = np.asarray(scenario["model_states"], dtype=float)
    else:
        export_states = rotate_j2000_states_to_tod_fk5(
            epochs,
            scenario["model_states"],
        )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(
            file,
            delimiter=",",
            lineterminator="\n",
        )
        for state_epoch, state in zip(epochs, export_states):
            x, y, z, vx, vy, vz = state
            writer.writerow(
                [
                    # Xarici proqramlar üçün standart CSV: vergül sütun ayırıcısı,
                    # nöqtə onluq ayırıcıdır və metadata/başlıq sətri yoxdur.
                    format_csv_date(state_epoch),
                    format_csv_time(state_epoch),
                    f"{x:.9f}",
                    f"{y:.9f}",
                    f"{z:.9f}",
                    f"{vx:.12f}",
                    f"{vy:.12f}",
                    f"{vz:.12f}",
                ]
            )
    return path


def save_scenario_csv(scenario, file_path):
    """Save one completed physical reference-model trajectory as CSV."""

    required = {"epoch", "elapsed_seconds", "model_states"}
    # Hesablama nəticəsi natamamdırsa və ya səhvən xam referans lüğəti verilibsə,
    # yanıltıcı natamam fayl yaranmamışdan əvvəl xəta qaytarılır.
    missing = required.difference(scenario)
    if missing:
        raise ValueError(
            "Scenario is missing CSV fields: " + ", ".join(sorted(missing))
        )
    return _write_model_scenario_csv(scenario, file_path)


def save_comparison_csv(result, file_path):
    """Save WITH MOON and WITHOUT MOON model series as separate CSV files.

    Format manual propaqasiya ixracı ilə eynidir:
    Date,Time,X,Y,Z,Vx,Vy,Vz. Fayllar yalnız TOD/FK5 məlumat sətirlərini,
    vergüllə ayrılmış sütunları və nöqtəli onluq qiymətləri saxlayır.
    """

    base_path = Path(file_path)
    base_name = (
        base_path.stem
        if base_path.suffix.lower() == ".csv"
        else base_path.name
    )
    sun_suffix = "_sun" if result.get("include_sun", False) else ""
    srp_suffix = "_srp_cp" if result.get("include_srp", False) else ""
    # Cüt ixrac faylları bir-birinin üzərinə yazılmır: qüvvə/ssenari məlumatı
    # fayl adına daxil edilir, sətir formatı isə tam eyni saxlanılır.
    with_path = base_path.with_name(
        f"{base_name}_with_moon{sun_suffix}{srp_suffix}.csv"
    )
    without_path = base_path.with_name(
        f"{base_name}_without_moon{sun_suffix}{srp_suffix}.csv"
    )

    _write_model_scenario_csv(result["with_moon"], with_path)
    _write_model_scenario_csv(result["without_moon"], without_path)
    return with_path, without_path
