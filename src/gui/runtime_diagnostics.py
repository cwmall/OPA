"""Persistent diagnostics for otherwise silent desktop-runtime failures."""

from __future__ import annotations

from datetime import datetime, timezone
import faulthandler
from pathlib import Path
import sys
import tempfile
import threading
import traceback


_DIAGNOSTIC_STREAM = None
_DIAGNOSTIC_PATH = None


def _open_diagnostic_stream(base_directory):
    candidates = (
        Path(base_directory) / "diagnostics",
        Path(tempfile.gettempdir()) / "OPA" / "diagnostics",
    )
    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / "opa_runtime.log"
            return path, path.open("a", encoding="utf-8", buffering=1)
        except OSError:
            continue
    return None, None


def install_runtime_diagnostics(base_directory):
    """Install exception and native-fault logging once per process."""

    global _DIAGNOSTIC_PATH, _DIAGNOSTIC_STREAM
    if _DIAGNOSTIC_STREAM is not None:
        return str(_DIAGNOSTIC_PATH)

    path, stream = _open_diagnostic_stream(base_directory)
    if stream is None:
        return None
    _DIAGNOSTIC_PATH = path
    _DIAGNOSTIC_STREAM = stream
    stream.write(
        "\n"
        + "=" * 78
        + "\nSTART UTC: "
        + datetime.now(timezone.utc).isoformat()
        + f"\nPython: {sys.version}\n"
    )

    try:
        faulthandler.enable(file=stream, all_threads=True)
    except (RuntimeError, OSError):
        pass

    def exception_hook(exception_type, exception, traceback_object):
        stream.write(
            "\nUNHANDLED EXCEPTION UTC: "
            + datetime.now(timezone.utc).isoformat()
            + f"\nThread: {threading.current_thread().name}\n"
        )
        traceback.print_exception(
            exception_type,
            exception,
            traceback_object,
            file=stream,
        )
        traceback.print_exception(
            exception_type,
            exception,
            traceback_object,
            file=sys.stderr,
        )

    sys.excepthook = exception_hook
    return str(path)


def diagnostic_path():
    return str(_DIAGNOSTIC_PATH) if _DIAGNOSTIC_PATH is not None else None


def record_runtime_event(message):
    if _DIAGNOSTIC_STREAM is None:
        return False
    _DIAGNOSTIC_STREAM.write(
        "EVENT UTC: "
        + datetime.now(timezone.utc).isoformat()
        + " — "
        + str(message)
        + "\n"
    )
    return True
