import os
import time
import numpy as np

from spice_loader import load_kernels
from time_utils import get_current_utc, utc_to_et
from satellite import (
    TARGET_SATELLITE_DISPLAY_NAME,
    TARGET_SATELLITE_NAME,
    get_satellite_position,
)
from moon import get_moon_position, get_sun_position
from moon_perturbation import moon_perturbation
from sun_perturbation import sun_perturbation


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def run_monitor(update_interval=10):

    load_kernels()

    while True:

        utc = get_current_utc()
        et = utc_to_et(utc)

        r_sat = get_satellite_position(
            TARGET_SATELLITE_NAME,
            utc
        )

        r_moon = get_moon_position(et)
        r_sun = get_sun_position(et)

        a_moon = moon_perturbation(r_sat, r_moon)
        a_sun = sun_perturbation(r_sat, r_sun)
        a_total = a_moon + a_sun

        clear()

        print("=" * 60)
        print("        ORBITAL PERTURBATION ANALYZER")
        print("=" * 60)

        print(f"\nUTC : {utc}")

        print(f"\n----- {TARGET_SATELLITE_DISPLAY_NAME} -----")
        print(f"X : {r_sat[0]:12.3f} km")
        print(f"Y : {r_sat[1]:12.3f} km")
        print(f"Z : {r_sat[2]:12.3f} km")
        print(f"Distance : {np.linalg.norm(r_sat):.3f} km")

        print("\n----- MOON -----")
        print(f"X : {r_moon[0]:12.3f} km")
        print(f"Y : {r_moon[1]:12.3f} km")
        print(f"Z : {r_moon[2]:12.3f} km")
        print(f"Distance : {np.linalg.norm(r_moon):.3f} km")

        print("\n----- THIRD-BODY PERTURBATION -----")
        print(f"Moon |a| : {np.linalg.norm(a_moon):.6e} km/s²")
        print(f"Sun β |a|: {np.linalg.norm(a_sun):.6e} km/s²")
        print(f"ax : {a_total[0]:.6e} km/s²")
        print(f"ay : {a_total[1]:.6e} km/s²")
        print(f"az : {a_total[2]:.6e} km/s²")
        print(f"Combined |a| : {np.linalg.norm(a_total):.6e} km/s²")

        print("\nUpdating in", update_interval, "seconds...")

        time.sleep(update_interval)
