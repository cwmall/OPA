"""Shared perturbation-vector analysis helpers."""

import numpy as np


PERTURBATION_PARAMETERS = (
    "Magnitude",
    "ax",
    "ay",
    "az",
    "aR",
    "aT",
    "aN",
)


def rtn_basis(state):
    """Return the radial, along-track, and orbit-normal unit vectors."""

    state = np.asarray(state, dtype=float)
    if state.shape != (6,) or not np.all(np.isfinite(state)):
        raise ValueError("state must be a finite 6-element vector.")
    position = state[:3]
    velocity = state[3:]
    position_norm = float(np.linalg.norm(position))
    angular_momentum = np.cross(position, velocity)
    momentum_norm = float(np.linalg.norm(angular_momentum))
    if position_norm <= 0.0 or momentum_norm <= 0.0:
        raise ValueError("state cannot define an RTN frame.")

    radial = position / position_norm
    normal = angular_momentum / momentum_norm
    along_track = np.cross(normal, radial)
    along_track /= np.linalg.norm(along_track)
    return radial, along_track, normal


def acceleration_components(acceleration, state):
    """Return inertial and RTN components for one acceleration vector."""

    acceleration = np.asarray(acceleration, dtype=float)
    if acceleration.shape != (3,) or not np.all(np.isfinite(acceleration)):
        raise ValueError("acceleration must be a finite 3-element vector.")
    radial, along_track, normal = rtn_basis(state)
    return {
        "Magnitude": float(np.linalg.norm(acceleration)),
        "ax": float(acceleration[0]),
        "ay": float(acceleration[1]),
        "az": float(acceleration[2]),
        "aR": float(np.dot(acceleration, radial)),
        "aT": float(np.dot(acceleration, along_track)),
        "aN": float(np.dot(acceleration, normal)),
    }
