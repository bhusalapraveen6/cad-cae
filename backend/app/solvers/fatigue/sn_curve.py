"""
Fatigue life post-processing module.
Uses S-N curve data with Goodman/Soderberg/Gerber mean-stress corrections
to compute fatigue life (cycles to failure) and safety factor fields.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FatigueResult:
    min_life_cycles: float = 1e9
    max_life_cycles: float = 1e9
    min_safety_factor: float = 1.0
    critical_node_idx: int = 0
    life_field: np.ndarray = None
    safety_factor_field: np.ndarray = None
    result_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.result_data is None:
            self.result_data = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_life_cycles": self.min_life_cycles,
            "max_life_cycles": self.max_life_cycles,
            "min_safety_factor": round(self.min_safety_factor, 3),
            "critical_node_idx": self.critical_node_idx,
        }


# ── S-N curve utilities ────────────────────────────────────────────────────────

def interpolate_sn_curve(
    sn_data: List[Tuple[float, float]],
    stress_amplitude: float,
) -> float:
    """
    Log-log interpolation on an S-N curve.
    sn_data: list of (N_cycles, stress_amplitude_MPa) pairs, sorted by cycles ascending.
    Returns estimated cycles to failure (capped at 1e9 for run-out).
    """
    if not sn_data or stress_amplitude <= 0:
        return 1e9

    # Sort by cycles
    sn_sorted = sorted(sn_data, key=lambda x: x[0])
    cycles_arr = np.array([p[0] for p in sn_sorted])
    stress_arr = np.array([p[1] for p in sn_sorted])

    # Below minimum stress → infinite life
    if stress_amplitude <= stress_arr[-1]:
        return 1e9

    # Above maximum stress → use extrapolation
    if stress_amplitude >= stress_arr[0]:
        # Linear log-log extrapolation from first two points
        logN1, logS1 = math.log10(cycles_arr[0]), math.log10(stress_arr[0])
        logN2, logS2 = math.log10(cycles_arr[1]), math.log10(stress_arr[1])
        slope = (logN2 - logN1) / (logS2 - logS1)
        logN = logN1 + slope * (math.log10(stress_amplitude) - logS1)
        return max(1.0, 10**logN)

    # Interpolate in log-log space
    log_stress = math.log10(stress_amplitude)
    log_stress_arr = np.log10(stress_arr)
    log_cycles_arr = np.log10(cycles_arr)
    log_N = float(np.interp(log_stress, log_stress_arr[::-1], log_cycles_arr[::-1]))
    return 10**log_N


def apply_mean_stress_correction(
    stress_amplitude: float,
    mean_stress: float,
    ultimate_strength: float,
    yield_strength: float,
    method: str = "goodman",
) -> float:
    """
    Return an equivalent fully-reversed stress amplitude after mean-stress correction.
    Methods: 'goodman', 'soderberg', 'gerber', 'none'
    """
    if method == "none" or mean_stress <= 0:
        return stress_amplitude
    if mean_stress >= ultimate_strength:
        return float("inf")

    if method == "goodman":
        # σ_a / S_e + σ_m / S_u = 1  →  σ_a_eq = σ_a / (1 - σ_m/S_u)
        return stress_amplitude / (1.0 - mean_stress / ultimate_strength)
    elif method == "soderberg":
        return stress_amplitude / (1.0 - mean_stress / yield_strength)
    elif method == "gerber":
        return stress_amplitude / (1.0 - (mean_stress / ultimate_strength) ** 2)
    return stress_amplitude


# ── Main fatigue analysis function ─────────────────────────────────────────────

def compute_fatigue_life(
    von_mises_field: np.ndarray,
    material: Dict[str, Any],
    stress_ratio: float = -1.0,     # R = σ_min / σ_max  (-1 = fully reversed)
    correction_method: str = "goodman",
) -> FatigueResult:
    """
    Compute fatigue life at each node given the von Mises stress field from a static result.

    Args:
        von_mises_field: (N,) array of von Mises stresses [MPa]
        material: material dict with sn_curve_data, ultimate_strength, yield_strength
        stress_ratio: R = σ_min / σ_max (−1 for fully reversed)
        correction_method: mean stress correction method

    Returns:
        FatigueResult with life_field and safety_factor_field per node
    """
    if von_mises_field is None or len(von_mises_field) == 0:
        return _mock_fatigue_result()

    sigma_max = von_mises_field
    sigma_min = stress_ratio * sigma_max

    # Stress amplitude and mean stress
    stress_amplitude = (sigma_max - sigma_min) / 2.0
    mean_stress       = (sigma_max + sigma_min) / 2.0

    ult = material.get("ultimate_strength", 400.0)    # MPa
    yld = material.get("yield_strength",   250.0)     # MPa
    sn_data = material.get("sn_curve_data") or _default_steel_sn()

    # Apply mean stress correction per node
    eq_amplitude = np.array([
        apply_mean_stress_correction(
            float(sa), float(ms), ult, yld, correction_method
        )
        for sa, ms in zip(stress_amplitude, mean_stress)
    ])

    # Compute life per node
    life = np.array([
        interpolate_sn_curve(sn_data, float(sa))
        for sa in eq_amplitude
    ])
    life = np.clip(life, 1.0, 1e9)

    # Safety factor: ratio of endurance limit to equivalent amplitude
    endurance_limit = sn_data[-1][1] if sn_data else ult * 0.4   # MPa
    sf = np.where(eq_amplitude > 0, endurance_limit / np.maximum(eq_amplitude, 1e-9), 99.0)
    sf = np.clip(sf, 0.01, 99.0)

    crit_idx = int(np.argmin(life))

    result = FatigueResult(
        min_life_cycles=float(life.min()),
        max_life_cycles=float(life.max()),
        min_safety_factor=float(sf.min()),
        critical_node_idx=crit_idx,
        life_field=life.astype(np.float32),
        safety_factor_field=sf.astype(np.float32),
    )
    result.result_data = result.to_dict()

    logger.info(
        "Fatigue analysis complete",
        min_life=result.min_life_cycles,
        min_sf=result.min_safety_factor,
        correction=correction_method,
    )
    return result


def _default_steel_sn() -> List[Tuple[float, float]]:
    """Default S-N curve for structural steel (ASTM A36 approximate)."""
    return [
        (1e3,  500.0),
        (1e4,  350.0),
        (1e5,  250.0),
        (1e6,  180.0),
        (2e6,  160.0),
        (1e7,  145.0),   # endurance limit region
        (1e8,  140.0),
    ]


def _mock_fatigue_result() -> FatigueResult:
    import numpy as np
    n = 100
    life = np.random.uniform(1e5, 1e7, n).astype(np.float32)
    sf   = np.random.uniform(1.5, 5.0, n).astype(np.float32)
    return FatigueResult(
        min_life_cycles=float(life.min()),
        max_life_cycles=float(life.max()),
        min_safety_factor=float(sf.min()),
        critical_node_idx=int(np.argmin(life)),
        life_field=life,
        safety_factor_field=sf,
        result_data={
            "min_life_cycles": float(life.min()),
            "max_life_cycles": float(life.max()),
            "min_safety_factor": round(float(sf.min()), 3),
        },
    )
