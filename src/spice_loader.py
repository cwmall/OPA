from pathlib import Path

import spiceypy as spice


# ============================================================
# PATHS
# ============================================================

SRC_DIR = Path(__file__).resolve().parent

PROJECT_DIR = SRC_DIR.parent

KERNEL_DIR = PROJECT_DIR / "kernels"


# ============================================================
# REQUIRED KERNELS
# ============================================================

LEAP_SECONDS_KERNEL = (
    KERNEL_DIR
    / "naif0012.tls"
)

PLANETARY_EPHEMERIS_KERNEL = (
    KERNEL_DIR
    / "de440s.bsp"
)


# ============================================================
# OPTIONAL KERNELS
# ============================================================

PLANETARY_CONSTANTS_KERNEL = (
    KERNEL_DIR
    / "pck00010.tpc"
)


# ============================================================
# STATE
# ============================================================

_loaded = False


# ============================================================
# LOAD KERNELS
# ============================================================

def load_kernels():
    """
    Load SPICE kernels required by the project.

    Required
    --------
    naif0012.tls
        Leap-second kernel.

    de440s.bsp
        JPL DE440 short-span planetary ephemeris.

    Optional
    --------
    pck00010.tpc
        Planetary constants kernel.

        It is not required for the current Earth + EGM96 4x4 + Moon
        propagation model in an inertial J2000 frame, but it
        can be loaded automatically if present.

    Notes
    -----
    Kernels are loaded only once per Python process.
    """

    global _loaded

    if _loaded:
        return

    # --------------------------------------------------------
    # REQUIRED FILES
    # --------------------------------------------------------

    required_kernels = [
        LEAP_SECONDS_KERNEL,
        PLANETARY_EPHEMERIS_KERNEL,
    ]

    for kernel in required_kernels:

        if not kernel.exists():

            raise FileNotFoundError(
                "Required SPICE kernel not found:\n"
                f"{kernel}"
            )

    # --------------------------------------------------------
    # LOAD REQUIRED KERNELS
    # --------------------------------------------------------

    for kernel in required_kernels:

        spice.furnsh(
            str(kernel)
        )

    # --------------------------------------------------------
    # LOAD OPTIONAL PCK IF AVAILABLE
    # --------------------------------------------------------

    if PLANETARY_CONSTANTS_KERNEL.exists():

        spice.furnsh(
            str(
                PLANETARY_CONSTANTS_KERNEL
            )
        )

    _loaded = True


# ============================================================
# UNLOAD KERNELS
# ============================================================

def unload_kernels():
    """
    Clear all SPICE kernels from memory.
    """

    global _loaded

    spice.kclear()

    _loaded = False


# ============================================================
# STATUS
# ============================================================

def kernels_loaded():
    """
    Return True if the required project kernels
    have already been loaded.
    """

    return _loaded


# ============================================================
# KERNEL INFORMATION
# ============================================================

def get_kernel_status():
    """
    Return information about the project's SPICE kernels.

    Returns
    -------
    dict
        Kernel paths and availability.
    """

    return {
        "naif0012.tls": {
            "path": str(
                LEAP_SECONDS_KERNEL
            ),
            "exists": (
                LEAP_SECONDS_KERNEL.exists()
            ),
            "required": True,
        },

        "de440s.bsp": {
            "path": str(
                PLANETARY_EPHEMERIS_KERNEL
            ),
            "exists": (
                PLANETARY_EPHEMERIS_KERNEL.exists()
            ),
            "required": True,
        },

        "pck00010.tpc": {
            "path": str(
                PLANETARY_CONSTANTS_KERNEL
            ),
            "exists": (
                PLANETARY_CONSTANTS_KERNEL.exists()
            ),
            "required": False,
        },
    }
