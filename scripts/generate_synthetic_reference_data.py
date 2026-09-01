"""Regenerate the public, non-operational reference trajectories.

The inputs below were invented for this repository.  They are not fitted to,
copied from, or intended to represent any real spacecraft or operator.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from propagator import propagate_trajectory  # noqa: E402


EPOCH = datetime(2030, 1, 1, tzinfo=timezone.utc)
INITIAL_STATE = [42164.0, 0.0, 100.0, 0.0, 3.07466, 0.0]
STEP_SECONDS = 3600.0
DURATION_SECONDS = 86400.0
SRP_INPUTS = {
    "srp_coefficient": 1.2,
    "srp_area_m2": 18.0,
    "srp_mass_kg": 1000.0,
}


def main() -> None:
    output_directory = ROOT / "demo_data" / "reference"
    output_directory.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "demo_earth.csv": (False, False, False),
        "demo_earth_moon.csv": (True, False, False),
        "demo_earth_sun.csv": (False, True, False),
        "demo_earth_moon_sun.csv": (True, True, False),
        "demo_earth_srp.csv": (False, False, True),
        "demo_earth_moon_srp.csv": (True, False, True),
        "demo_earth_sun_srp.csv": (False, True, True),
        "demo_earth_moon_sun_srp.csv": (True, True, True),
    }
    for filename, (include_moon, include_sun, include_srp) in scenarios.items():
        times, states = propagate_trajectory(
            initial_state=INITIAL_STATE,
            initial_epoch=EPOCH,
            duration_seconds=DURATION_SECONDS,
            output_step=STEP_SECONDS,
            include_j2=True,
            include_moon=include_moon,
            include_sun=include_sun,
            include_srp=include_srp,
            **(SRP_INPUTS if include_srp else {}),
        )
        destination = output_directory / filename
        with destination.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(
                ("epoch_utc", "x_km", "y_km", "z_km", "vx_km_s", "vy_km_s", "vz_km_s")
            )
            for seconds, state in zip(times, states):
                epoch = EPOCH + timedelta(seconds=float(seconds))
                writer.writerow(
                    [epoch.isoformat(), *(f"{float(value):.15e}" for value in state)]
                )


if __name__ == "__main__":
    main()
