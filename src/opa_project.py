"""Safe, versioned Orbital Perturbation Analyzer project documents."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from satellite_profiles import SatelliteProfile, validate_profile


PROJECT_SCHEMA_VERSION = 3
SUPPORTED_PROJECT_SCHEMA_VERSIONS = {1, 2, PROJECT_SCHEMA_VERSION}


class ProjectValidationError(ValueError):
    """Raised for malformed, unsafe or unsupported project content."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite(value: Any, name: str, *, positive: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ProjectValidationError(f"{name} must be numeric.") from error
    if not math.isfinite(number) or (positive and number <= 0.0):
        qualifier = "positive and " if positive else ""
        raise ProjectValidationError(f"{name} must be {qualifier}finite.")
    return number


def _integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise ProjectValidationError(f"{name} must be an integer.")
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ProjectValidationError(f"{name} must be an integer.") from error
    if number < minimum or number > maximum:
        raise ProjectValidationError(
            f"{name} must be between {minimum} and {maximum}."
        )
    return number


def _boolean(value: Any, name: str, default: bool) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise ProjectValidationError(f"{name} must be a JSON boolean.")


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ProjectValidationError(f"{name} must be a JSON object.")
    return dict(value)


def _text(value: Any, name: str, *, limit: int, fallback: str = "") -> str:
    if value is None:
        return fallback
    if not isinstance(value, str):
        raise ProjectValidationError(f"{name} must be text.")
    if len(value) > limit:
        raise ProjectValidationError(f"{name} is too long.")
    return value


def _timestamp(
    value: Any,
    name: str,
    *,
    fallback: str | None = None,
    allow_empty: bool = False,
) -> str:
    if value in {None, ""}:
        if fallback is not None:
            return fallback
        if allow_empty:
            return ""
        raise ProjectValidationError(f"{name} is required.")
    if not isinstance(value, str):
        raise ProjectValidationError(f"{name} must be an ISO-8601 timestamp.")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProjectValidationError(
            f"{name} must be a valid ISO-8601 timestamp."
        ) from error
    if parsed.tzinfo is None:
        raise ProjectValidationError(f"{name} must include a UTC offset.")
    return parsed.astimezone(timezone.utc).isoformat()


def _state(value: Any, name: str, *, optional: bool = False) -> list[float]:
    if value is None or value == () or value == []:
        if optional:
            return []
        raise ProjectValidationError(f"{name} is required.")
    if not isinstance(value, (list, tuple)):
        raise ProjectValidationError(f"{name} must be a JSON array.")
    if len(value) != 6:
        raise ProjectValidationError(f"{name} must contain six components.")
    return [_finite(component, f"{name} component") for component in value]


def _optional_positive(value: Any, name: str) -> float | None:
    if value in {None, ""}:
        return None
    return _finite(value, name, positive=True)


def _optional_nonnegative(value: Any, name: str) -> float | None:
    if value in {None, ""}:
        return None
    number = _finite(value, name)
    if number < 0.0:
        raise ProjectValidationError(f"{name} cannot be negative.")
    return number


def _provenance(value: Any) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProjectValidationError("Project provenance must be a JSON array.")
    if len(value) > 50:
        raise ProjectValidationError("Project provenance contains too many entries.")
    result = []
    for entry in value:
        if isinstance(entry, str):
            result.append(_text(entry, "Provenance entry", limit=4000))
            continue
        if not isinstance(entry, Mapping):
            raise ProjectValidationError(
                "Each provenance entry must be text or a JSON object."
            )
        clean = {}
        for key, item in entry.items():
            if not isinstance(key, str) or len(key) > 100:
                raise ProjectValidationError("Invalid provenance field name.")
            if isinstance(item, float) and not math.isfinite(item):
                raise ProjectValidationError("Provenance numbers must be finite.")
            if item is not None and not isinstance(item, (str, int, float, bool)):
                raise ProjectValidationError(
                    "Provenance values must be scalar JSON values."
                )
            if isinstance(item, str) and len(item) > 4000:
                raise ProjectValidationError("Provenance value is too long.")
            clean[key] = item
        result.append(clean)
    return result


def _default_eclipse(profile: SatelliteProfile) -> dict[str, Any]:
    return {
        "epoch_utc": "",
        "state_j2000": [],
        "duration_days": 30,
        "output_step_seconds": 600,
        "include_j2": profile.include_j2,
        "include_moon": profile.include_moon,
        "include_sun": profile.include_sun,
        "include_srp": profile.include_srp,
        "oblate_earth_shadow": False,
        "light_time_moon": False,
        "yearly_search_year": datetime.now(timezone.utc).year,
        "reference_dataset_id": "",
        "reference_tolerance_seconds": 120,
    }


def _default_view() -> dict[str, Any]:
    return {
        "active_tab": 0,
        "manual_chart": "longitude",
        "perturbation_parameter": "",
        "perturbation_time_range": "",
        "reference_chart": "",
        "reference_dataset_id": "",
        "system_projection": "XY Plane",
        "system_scale": "Auto Fit Selected",
        "system_focus": "earth",
        "system_visible_objects": ["moon", "iss"],
    }


def new_project(profile: SatelliteProfile, application_version: str) -> dict[str, Any]:
    now = _utc_now()
    epoch = profile.epoch_utc or ""
    state = list(profile.state_j2000 or ())
    project = {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "project_id": uuid4().hex,
        "application_version": str(application_version),
        "name": "Untitled Mission",
        "description": "",
        "created_utc": now,
        "modified_utc": now,
        "satellite_profile_id": profile.profile_id,
        "satellite_profile_snapshot": profile.to_dict(),
        "initial_state": {
            "source": profile.orbit_source,
            "epoch_utc": epoch,
            "reference_frame": profile.reference_frame,
            "state_j2000": state,
            "provenance": profile.source_description,
        },
        "propagation": {
            "start_utc": epoch,
            "end_utc": "",
            "epoch_utc": epoch,
            "state_j2000": state,
            "duration_days": 30.0,
            "output_step_seconds": 900,
            "earth_gravity_enabled": True,
            "include_j2": profile.include_j2,
            "egm96_degree": profile.egm96_degree,
            "egm96_order": profile.egm96_order,
            "include_moon": profile.include_moon,
            "include_sun": profile.include_sun,
            "include_srp": profile.include_srp,
            "srp_model": "active_profile",
            "manual_srp_mode": "combined",
            "manual_srp_mass_kg": 1000.0,
            "manual_srp_total_area_m2": 20.0,
            "manual_srp_coefficient": 1.0,
            "manual_srp_panel_area_m2": 15.0,
            "manual_srp_panel_coefficient": 1.0,
            "manual_srp_body_area_m2": 5.0,
            "manual_srp_body_coefficient": 1.0,
        },
        "numerical": {
            "rtol": "1e-11",
            "atol": "1e-12",
            "max_step_seconds": 300,
            "eop_enabled": profile.eop_enabled,
        },
        "eclipse": _default_eclipse(profile),
        "geo_operations": {
            "target_longitude_deg": profile.target_longitude_deg,
            "station_box_half_width_deg": profile.station_box_half_width_deg,
            "inclination_warning_deg": profile.inclination_warning_deg,
            "inclination_limit_deg": profile.inclination_limit_deg,
            "eccentricity_warning": profile.eccentricity_warning,
            "eccentricity_limit": profile.eccentricity_limit,
            "annual_delta_v_budget_m_s": profile.annual_delta_v_budget_m_s,
            "annual_delta_v_used_m_s": 0.0,
        },
        "view": _default_view(),
        "notes": "",
        "provenance": [],
    }
    return validate_project(project)


def validate_project(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ProjectValidationError("Project root must be a JSON object.")
    source = dict(payload)
    try:
        version = int(source.get("schema_version", 0))
    except (TypeError, ValueError) as error:
        raise ProjectValidationError("Invalid project schema version.") from error
    if version > PROJECT_SCHEMA_VERSION:
        raise ProjectValidationError(
            f"Project schema {version} is newer than supported schema "
            f"{PROJECT_SCHEMA_VERSION}. Update OPA before opening it."
        )
    if version not in SUPPORTED_PROJECT_SCHEMA_VERSIONS:
        raise ProjectValidationError("Project schema version is missing or unsupported.")

    snapshot = source.get("satellite_profile_snapshot")
    if not isinstance(snapshot, Mapping):
        raise ProjectValidationError(
            "Project is missing its satellite-profile snapshot."
        )
    profile = validate_profile(snapshot)
    propagation = _mapping(source.get("propagation"), "Propagation")
    initial = _mapping(source.get("initial_state"), "Initial state")
    raw_state = initial.get("state_j2000", propagation.get("state_j2000", []))
    state = _state(raw_state, "Initial J2000 state", optional=True)
    raw_epoch = initial.get("epoch_utc", propagation.get("epoch_utc", ""))
    epoch = _timestamp(
        raw_epoch,
        "Initial-state epoch",
        allow_empty=not bool(state),
    )
    if state and not epoch:
        raise ProjectValidationError("A J2000 state requires an epoch.")
    reference_frame = _text(
        initial.get("reference_frame", profile.reference_frame),
        "Initial-state reference frame",
        limit=40,
        fallback="J2000",
    ).strip().upper()
    if reference_frame not in {"J2000", "ICRF"}:
        raise ProjectValidationError(
            "Initial-state reference frame must be J2000/ICRF."
        )
    reference_frame = "J2000"
    initial_source = _text(
        initial.get("source", profile.orbit_source),
        "Initial-state source",
        limit=80,
        fallback="manual",
    ).strip() or "manual"
    initial_provenance = _text(
        initial.get("provenance", profile.source_description),
        "Initial-state provenance",
        limit=10000,
    )

    duration = _finite(
        propagation.get("duration_days", 30.0), "Duration", positive=True
    )
    step = _integer(
        propagation.get("output_step_seconds", 900),
        "Output step",
        1,
        31_536_000,
    )
    start = _timestamp(
        propagation.get("start_utc", propagation.get("epoch_utc", epoch)),
        "Propagation start",
        allow_empty=not bool(state),
    )
    end = ""
    if start:
        end = (
            datetime.fromisoformat(start) + timedelta(days=duration)
        ).astimezone(timezone.utc).isoformat()
    supplied_end = propagation.get("end_utc")
    if supplied_end:
        _timestamp(supplied_end, "Propagation end")

    egm96_degree = _integer(
        propagation.get("egm96_degree", profile.egm96_degree),
        "EGM96 degree",
        2,
        4,
    )
    egm96_order = _integer(
        propagation.get("egm96_order", egm96_degree),
        "EGM96 order",
        2,
        4,
    )
    if egm96_order != egm96_degree:
        raise ProjectValidationError(
            "Project EGM96 truncation must be coupled 2×2, 3×3 or 4×4."
        )
    if not _boolean(
        propagation.get("earth_gravity_enabled", True),
        "Earth gravity enabled",
        True,
    ):
        raise ProjectValidationError("Earth central gravity must remain enabled.")
    srp_model = _text(
        propagation.get("srp_model", "active_profile"),
        "Propagation SRP model",
        limit=80,
        fallback="active_profile",
    ).strip()
    if srp_model not in {"active_profile", "demo_equivalent", "manual"}:
        raise ProjectValidationError("Unknown propagation SRP model.")
    manual_srp_mode = _text(
        propagation.get("manual_srp_mode", "combined"),
        "Manual SRP input mode",
        limit=40,
        fallback="combined",
    ).strip()
    if manual_srp_mode not in {"combined", "panel_body"}:
        raise ProjectValidationError("Unknown manual SRP input mode.")
    manual_srp_mass_kg = _finite(
        propagation.get("manual_srp_mass_kg", 1000.0),
        "Manual SRP mass",
        positive=True,
    )
    manual_srp_total_area_m2 = _finite(
        propagation.get("manual_srp_total_area_m2", 20.0),
        "Manual SRP total area",
        positive=True,
    )
    manual_srp_coefficient = _finite(
        propagation.get("manual_srp_coefficient", 1.0),
        "Manual SRP coefficient",
        positive=True,
    )
    manual_srp_panel_area_m2 = _finite(
        propagation.get("manual_srp_panel_area_m2", 15.0),
        "Manual SRP panel area",
    )
    manual_srp_panel_coefficient = _finite(
        propagation.get("manual_srp_panel_coefficient", 1.0),
        "Manual SRP panel coefficient",
        positive=True,
    )
    manual_srp_body_area_m2 = _finite(
        propagation.get("manual_srp_body_area_m2", 5.0),
        "Manual SRP body area",
    )
    manual_srp_body_coefficient = _finite(
        propagation.get("manual_srp_body_coefficient", 1.0),
        "Manual SRP body coefficient",
        positive=True,
    )
    if manual_srp_panel_area_m2 < 0.0 or manual_srp_body_area_m2 < 0.0:
        raise ProjectValidationError("Manual SRP component areas cannot be negative.")
    if (
        manual_srp_mode == "panel_body"
        and manual_srp_panel_area_m2 + manual_srp_body_area_m2 <= 0.0
    ):
        raise ProjectValidationError(
            "Manual SRP panel and body areas cannot both be zero."
        )
    if manual_srp_mass_kg > 1_000_000_000.0:
        raise ProjectValidationError("Manual SRP mass exceeds the supported range.")
    for value, name, maximum in (
        (manual_srp_total_area_m2, "Manual SRP total area", 1_000_000_000.0),
        (manual_srp_panel_area_m2, "Manual SRP panel area", 1_000_000_000.0),
        (manual_srp_body_area_m2, "Manual SRP body area", 1_000_000_000.0),
        (manual_srp_coefficient, "Manual SRP coefficient", 100.0),
        (manual_srp_panel_coefficient, "Manual SRP panel coefficient", 100.0),
        (manual_srp_body_coefficient, "Manual SRP body coefficient", 100.0),
    ):
        if value > maximum:
            raise ProjectValidationError(f"{name} exceeds the supported range.")

    numerical = _mapping(source.get("numerical"), "Numerical settings")
    rtol = _finite(numerical.get("rtol", "1e-11"), "Relative tolerance", positive=True)
    atol = _finite(numerical.get("atol", "1e-12"), "Absolute tolerance", positive=True)
    max_step = _integer(
        numerical.get("max_step_seconds", 300),
        "Numerical maximum step",
        1,
        86_400,
    )

    eclipse_source = _mapping(source.get("eclipse"), "Eclipse settings")
    eclipse_defaults = _default_eclipse(profile)
    eclipse_state = _state(
        eclipse_source.get("state_j2000", eclipse_defaults["state_j2000"]),
        "Eclipse J2000 state",
        optional=True,
    )
    eclipse_epoch = _timestamp(
        eclipse_source.get("epoch_utc", eclipse_defaults["epoch_utc"]),
        "Eclipse epoch",
        allow_empty=not bool(eclipse_state),
    )
    if eclipse_state and not eclipse_epoch:
        raise ProjectValidationError("An eclipse J2000 state requires an epoch.")
    eclipse_step = _integer(
        eclipse_source.get(
            "output_step_seconds", eclipse_defaults["output_step_seconds"]
        ),
        "Eclipse output step",
        1,
        31_536_000,
    )
    if not any(
        eclipse_step % unit == 0 and 1 <= eclipse_step // unit <= 60
        for unit in (1, 60, 3600, 86400)
    ):
        raise ProjectValidationError(
            "Eclipse output step cannot be represented by the current "
            "seconds/minutes/hours/days controls."
        )

    geo = _mapping(source.get("geo_operations"), "GEO operations")
    target_longitude = _finite(
        geo.get("target_longitude_deg", profile.target_longitude_deg),
        "Target longitude",
    )
    if target_longitude < -180.0 or target_longitude > 180.0:
        raise ProjectValidationError("Target longitude must be between -180 and 180 degrees.")
    half_width = _finite(
        geo.get("station_box_half_width_deg", profile.station_box_half_width_deg),
        "Station-box half-width",
        positive=True,
    )
    if half_width > 180.0:
        raise ProjectValidationError("Station-box half-width cannot exceed 180 degrees.")
    inclination_warning = _finite(
        geo.get("inclination_warning_deg", profile.inclination_warning_deg),
        "Inclination warning",
    )
    inclination_limit = _finite(
        geo.get("inclination_limit_deg", profile.inclination_limit_deg),
        "Inclination limit",
    )
    eccentricity_warning = _finite(
        geo.get("eccentricity_warning", profile.eccentricity_warning),
        "Eccentricity warning",
    )
    eccentricity_limit = _finite(
        geo.get("eccentricity_limit", profile.eccentricity_limit),
        "Eccentricity limit",
    )
    if not 0.0 <= inclination_warning <= inclination_limit:
        raise ProjectValidationError(
            "Inclination warning must be non-negative and no greater than its limit."
        )
    if not 0.0 <= eccentricity_warning <= eccentricity_limit < 1.0:
        raise ProjectValidationError(
            "Eccentricity warning/limit must satisfy 0 ≤ warning ≤ limit < 1."
        )

    view_source = _mapping(source.get("view"), "View settings")
    view_defaults = _default_view()
    visible_objects = view_source.get(
        "system_visible_objects", view_defaults["system_visible_objects"]
    )
    if not isinstance(visible_objects, list) or any(
        not isinstance(item, str) or len(item) > 80 for item in visible_objects
    ):
        raise ProjectValidationError("Visible system objects must be a JSON text array.")

    created = _timestamp(
        source.get("created_utc"), "Creation timestamp", fallback=_utc_now()
    )
    modified = _timestamp(
        source.get("modified_utc"), "Modification timestamp", fallback=created
    )

    return {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "project_id": _text(
            source.get("project_id"), "Project ID", limit=200, fallback=uuid4().hex
        ) or uuid4().hex,
        "application_version": _text(
            source.get("application_version"),
            "Application version",
            limit=80,
            fallback="unknown",
        ) or "unknown",
        "name": _text(
            source.get("name"), "Project name", limit=200, fallback="Untitled Mission"
        ).strip() or "Untitled Mission",
        "description": _text(
            source.get("description"), "Project description", limit=20_000
        ),
        "created_utc": created,
        "modified_utc": modified,
        "satellite_profile_id": _text(
            source.get("satellite_profile_id"),
            "Satellite profile ID",
            limit=200,
            fallback=profile.profile_id,
        ) or profile.profile_id,
        "satellite_profile_snapshot": profile.to_dict(),
        "initial_state": {
            "source": initial_source,
            "epoch_utc": epoch,
            "reference_frame": reference_frame,
            "state_j2000": state,
            "provenance": initial_provenance,
        },
        "propagation": {
            "start_utc": start,
            "end_utc": end,
            "epoch_utc": epoch,
            "state_j2000": state,
            "duration_days": duration,
            "output_step_seconds": step,
            "earth_gravity_enabled": True,
            "include_j2": _boolean(
                propagation.get("include_j2"), "EGM96 enabled", profile.include_j2
            ),
            "egm96_degree": egm96_degree,
            "egm96_order": egm96_order,
            "include_moon": _boolean(
                propagation.get("include_moon"), "Moon gravity", profile.include_moon
            ),
            "include_sun": _boolean(
                propagation.get("include_sun"), "Sun gravity", profile.include_sun
            ),
            "include_srp": _boolean(
                propagation.get("include_srp"), "SRP", profile.include_srp
            ),
            "srp_model": srp_model,
            "manual_srp_mode": manual_srp_mode,
            "manual_srp_mass_kg": manual_srp_mass_kg,
            "manual_srp_total_area_m2": manual_srp_total_area_m2,
            "manual_srp_coefficient": manual_srp_coefficient,
            "manual_srp_panel_area_m2": manual_srp_panel_area_m2,
            "manual_srp_panel_coefficient": manual_srp_panel_coefficient,
            "manual_srp_body_area_m2": manual_srp_body_area_m2,
            "manual_srp_body_coefficient": manual_srp_body_coefficient,
        },
        "numerical": {
            "rtol": f"{rtol:.16g}",
            "atol": f"{atol:.16g}",
            "max_step_seconds": max_step,
            "eop_enabled": _boolean(
                numerical.get("eop_enabled"), "EOP enabled", profile.eop_enabled
            ),
        },
        "eclipse": {
            "epoch_utc": eclipse_epoch,
            "state_j2000": eclipse_state,
            "duration_days": _integer(
                eclipse_source.get("duration_days", eclipse_defaults["duration_days"]),
                "Eclipse duration",
                1,
                3650,
            ),
            "output_step_seconds": eclipse_step,
            "include_j2": _boolean(
                eclipse_source.get("include_j2"),
                "Eclipse EGM96",
                eclipse_defaults["include_j2"],
            ),
            "include_moon": _boolean(
                eclipse_source.get("include_moon"),
                "Eclipse Moon gravity",
                eclipse_defaults["include_moon"],
            ),
            "include_sun": _boolean(
                eclipse_source.get("include_sun"),
                "Eclipse Sun gravity",
                eclipse_defaults["include_sun"],
            ),
            "include_srp": _boolean(
                eclipse_source.get("include_srp"),
                "Eclipse SRP",
                eclipse_defaults["include_srp"],
            ),
            "oblate_earth_shadow": _boolean(
                eclipse_source.get("oblate_earth_shadow"),
                "Oblate Earth shadow",
                False,
            ),
            "light_time_moon": _boolean(
                eclipse_source.get("light_time_moon"),
                "Light-time Moon",
                False,
            ),
            "yearly_search_year": _integer(
                eclipse_source.get(
                    "yearly_search_year", eclipse_defaults["yearly_search_year"]
                ),
                "Eclipse search year",
                2000,
                2100,
            ),
            "reference_dataset_id": _text(
                eclipse_source.get("reference_dataset_id"),
                "Eclipse reference dataset ID",
                limit=200,
            ),
            "reference_tolerance_seconds": _integer(
                eclipse_source.get(
                    "reference_tolerance_seconds",
                    eclipse_defaults["reference_tolerance_seconds"],
                ),
                "Eclipse reference tolerance",
                1,
                3600,
            ),
        },
        "geo_operations": {
            "target_longitude_deg": target_longitude,
            "station_box_half_width_deg": half_width,
            "inclination_warning_deg": inclination_warning,
            "inclination_limit_deg": inclination_limit,
            "eccentricity_warning": eccentricity_warning,
            "eccentricity_limit": eccentricity_limit,
            "annual_delta_v_budget_m_s": _optional_nonnegative(
                geo.get(
                    "annual_delta_v_budget_m_s",
                    profile.annual_delta_v_budget_m_s,
                ),
                "Annual delta-v budget",
            ),
            "annual_delta_v_used_m_s": _optional_nonnegative(
                geo.get("annual_delta_v_used_m_s", 0.0),
                "Annual delta-v used",
            ) or 0.0,
        },
        "view": {
            "active_tab": _integer(
                view_source.get("active_tab", view_defaults["active_tab"]),
                "Active tab",
                0,
                100,
            ),
            "manual_chart": _text(
                view_source.get("manual_chart"), "Manual chart", limit=200,
                fallback=view_defaults["manual_chart"],
            ),
            "perturbation_parameter": _text(
                view_source.get("perturbation_parameter"),
                "Perturbation parameter",
                limit=200,
            ),
            "perturbation_time_range": _text(
                view_source.get("perturbation_time_range"),
                "Perturbation time range",
                limit=100,
            ),
            "reference_chart": _text(
                view_source.get("reference_chart"), "Reference chart", limit=200
            ),
            "reference_dataset_id": _text(
                view_source.get("reference_dataset_id"),
                "Reference dataset ID",
                limit=200,
            ),
            "system_projection": _text(
                view_source.get("system_projection"),
                "System projection",
                limit=100,
                fallback=view_defaults["system_projection"],
            ),
            "system_scale": _text(
                view_source.get("system_scale"),
                "System scale",
                limit=100,
                fallback=view_defaults["system_scale"],
            ),
            "system_focus": _text(
                view_source.get("system_focus"),
                "System focus",
                limit=80,
                fallback=view_defaults["system_focus"],
            ),
            "system_visible_objects": list(dict.fromkeys(visible_objects)),
        },
        "notes": _text(source.get("notes"), "Project notes", limit=100_000),
        "provenance": _provenance(source.get("provenance")),
    }


def load_project(path: str | os.PathLike[str]) -> dict[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProjectValidationError(f"Could not read project: {error}") from error
    return validate_project(payload)


def save_project(
    payload: Mapping[str, Any], path: str | os.PathLike[str]
) -> dict[str, Any]:
    project = validate_project(payload)
    project["modified_utc"] = _utc_now()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(project, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return project
