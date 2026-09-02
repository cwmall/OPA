"""Safe per-user desktop configuration persistence.

The public repository never stores a live user configuration.  Production
settings live below Qt's application-config location (LOCALAPPDATA on Windows),
while tests may point ``OPA_CONFIG_PATH`` at an isolated file.
"""

from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import shutil
from typing import Any, Mapping

from PySide6.QtCore import QStandardPaths


CONFIG_SCHEMA_VERSION = 4
APPLICATION_DIRECTORY_NAME = "OrbitalPerturbationAnalyzer"
CONFIG_FILENAME = "config.json"

DEFAULT_APPLICATION_CONFIG: dict[str, Any] = {
    "config_version": CONFIG_SCHEMA_VERSION,
    "theme": "normal",
    "language": "en",
    "integrator_rtol": "1e-11",
    "integrator_atol": "1e-12",
    "integrator_max_step": 300,
    "validation_minutes": 60,
    "eop_enabled": False,
    "active_profile_id": "synthetic_geo_demo",
    "window_geometry": None,
    "window_maximized": False,
    "active_module": 0,
    "active_tab": 0,
}

_last_config_warning = ""


def default_application_config_path() -> Path:
    override = os.environ.get("OPA_CONFIG_PATH", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    # AppConfigLocation includes Qt's current application/organization names.
    # Those names are not available yet when several OPA modules are imported,
    # which previously made the path change between the launcher and provisioning
    # utility.  LOCALAPPDATA is the stable Windows per-user root required here.
    windows_local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if os.name == "nt" and windows_local_app_data:
        base = Path(windows_local_app_data) / APPLICATION_DIRECTORY_NAME
    else:
        qt_location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        if qt_location:
            base = Path(qt_location)
            if base.name.casefold() != APPLICATION_DIRECTORY_NAME.casefold():
                base /= APPLICATION_DIRECTORY_NAME
        else:
            base = Path.home() / ".config" / APPLICATION_DIRECTORY_NAME
    return base / CONFIG_FILENAME


def _positive_float_text(value: Any, fallback: str) -> str:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    if not math.isfinite(number) or number <= 0.0:
        return fallback
    return str(value).strip()


def _bounded_integer(source: Mapping[str, Any], name: str, minimum: int, maximum: int) -> int:
    try:
        value = int(source.get(name, DEFAULT_APPLICATION_CONFIG[name]))
    except (TypeError, ValueError):
        value = int(DEFAULT_APPLICATION_CONFIG[name])
    return min(maximum, max(minimum, value))


def _boolean(value: Any, fallback: bool = False) -> bool:
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return fallback
    return bool(value)


def _window_geometry(value: Any) -> list[int] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x, y, width, height = (int(component) for component in value)
    except (TypeError, ValueError):
        return None
    if width < 980 or height < 700 or width > 16384 or height > 16384:
        return None
    if abs(x) > 32768 or abs(y) > 32768:
        return None
    return [x, y, width, height]


def normalise_application_config(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Migrate and validate the non-sensitive public settings schema."""

    source = dict(config) if isinstance(config, Mapping) else {}
    selected_theme = str(source.get("theme", "")).strip().casefold()
    if selected_theme not in {"normal", "retro"}:
        old_colour = str(source.get("color_theme", "")).strip().casefold()
        old_layout = str(source.get("visual_theme", "")).strip().casefold()
        selected_theme = "retro" if old_colour == "light" or old_layout == "legacy" else "normal"
    language = str(source.get("language", "en")).strip().casefold()
    if language not in {"az", "en"}:
        language = "en"
    profile_id = str(
        source.get(
            "active_profile_id",
            source.get("active_public_profile_id", DEFAULT_APPLICATION_CONFIG["active_profile_id"]),
        )
    ).strip()
    if profile_id != "synthetic_geo_demo":
        profile_id = str(DEFAULT_APPLICATION_CONFIG["active_profile_id"])
    return {
        "config_version": CONFIG_SCHEMA_VERSION,
        "theme": selected_theme,
        "language": language,
        "integrator_rtol": _positive_float_text(
            source.get("integrator_rtol"), str(DEFAULT_APPLICATION_CONFIG["integrator_rtol"])
        ),
        "integrator_atol": _positive_float_text(
            source.get("integrator_atol"), str(DEFAULT_APPLICATION_CONFIG["integrator_atol"])
        ),
        "integrator_max_step": _bounded_integer(source, "integrator_max_step", 1, 3600),
        "validation_minutes": _bounded_integer(source, "validation_minutes", 1, 1440),
        "eop_enabled": _boolean(source.get("eop_enabled"), False),
        "active_profile_id": profile_id,
        "window_geometry": _window_geometry(source.get("window_geometry")),
        "window_maximized": _boolean(source.get("window_maximized"), False),
        "active_module": _bounded_integer(source, "active_module", 0, 2),
        "active_tab": _bounded_integer(source, "active_tab", 0, 64),
    }


def get_last_config_warning() -> str:
    return _last_config_warning


def load_application_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load settings, recovering from a verified previous atomic copy."""

    global _last_config_warning
    _last_config_warning = ""
    config_path = Path(path) if path is not None else default_application_config_path()
    backup_path = config_path.with_suffix(config_path.suffix + ".bak")
    if not config_path.exists():
        return deepcopy(DEFAULT_APPLICATION_CONFIG)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("configuration root is not an object")
        return normalise_application_config(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        if backup_path.exists():
            try:
                payload = json.loads(backup_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    _last_config_warning = (
                        "Configuration was damaged; the previous safe copy was restored."
                    )
                    return normalise_application_config(payload)
            except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
                pass
        _last_config_warning = (
            "Configuration could not be read; safe default settings are active."
        )
        return deepcopy(DEFAULT_APPLICATION_CONFIG)


def save_application_config(
    config: Mapping[str, Any], path: str | os.PathLike[str] | None = None
) -> dict[str, Any]:
    """Atomically persist only allow-listed, non-sensitive settings."""

    normalised = normalise_application_config(config)
    config_path = Path(path) if path is not None else default_application_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_suffix(config_path.suffix + ".tmp")
    backup_path = config_path.with_suffix(config_path.suffix + ".bak")
    encoded = (json.dumps(normalised, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        with temporary_path.open("wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if config_path.exists():
            shutil.copy2(config_path, backup_path)
        os.replace(temporary_path, config_path)
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
    return normalised
