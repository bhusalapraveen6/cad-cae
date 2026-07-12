"""OpenFOAM CFD wrapper with mock mode."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from pathlib import Path
import numpy as np
import structlog
from app.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class CFDResult:
    max_velocity: float = 0.0
    max_pressure: float = 0.0
    pressure_drop: float = 0.0
    result_data: Dict = None

    def __post_init__(self):
        if self.result_data is None:
            self.result_data = {}

    def to_dict(self):
        return {
            "max_velocity_ms": round(self.max_velocity, 4),
            "max_pressure_pa": round(self.max_pressure, 2),
            "pressure_drop_pa": round(self.pressure_drop, 2),
        }


async def run_cfd(
    job_id: str,
    mesh_file: Optional[Path],
    parameters: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
    analysis_type: str = "cfd_internal",
) -> CFDResult:
    """Run OpenFOAM CFD internal or external flow analysis."""
    if settings.mock_solver_mode:
        return await _mock_cfd(parameters, progress_callback, is_external=(analysis_type == "cfd_external"))
    raise NotImplementedError("OpenFOAM CFD requires Docker environment")


async def _mock_cfd(params: Dict, cb: Optional[Callable], is_external: bool = False) -> CFDResult:
    stages = [
        (10, "Generating OpenFOAM external wind tunnel domain…"),
        (25, "Mesh generation around airfoil/body (snappyHexMesh)…"),
        (45, "Setting free-stream boundary conditions (U_inf)…"),
        (70, "Running simpleFoam flow solver (converging)…"),
        (90, "Integrating surface pressure for drag/lift…"),
        (100, "CFD external flow analysis complete ✓"),
    ] if is_external else [
        (10, "Generating OpenFOAM case directory…"),
        (25, "Setting boundary conditions (0/ folder)…"),
        (40, "Running blockMesh / snappyHexMesh…"),
        (60, "Running simpleFoam (500 iterations)…"),
        (80, "Post-processing velocity/pressure fields…"),
        (100, "CFD analysis complete ✓"),
    ]
    for pct, msg in stages:
        if cb:
            if asyncio.iscoroutinefunction(cb): await cb(pct, msg)
            else: cb(pct, msg)
        await asyncio.sleep(0.6)

    bcs = params.get("boundary_conditions", [])
    inlet = next((b for b in bcs if b.get("type") == "inlet"), {})
    v_inlet = inlet.get("velocity", 1.0)
    rho = params.get("fluid_density", 1.225)
    mu = params.get("dynamic_viscosity", 1.81e-5)

    if is_external:
        # Simulate external flow past a bluff body / airfoil
        cd = 0.82
        cl = 0.15
        area = 0.05  # m² projected area
        drag_force = 0.5 * rho * v_inlet**2 * cd * area
        lift_force = 0.5 * rho * v_inlet**2 * cl * area

        r = CFDResult(
            max_velocity=round(v_inlet * 1.45, 4),  # speedup over body
            max_pressure=round(0.5 * rho * v_inlet**2, 2),  # stagnation pressure
            pressure_drop=0.0,
        )
        r.result_data = {
            **r.to_dict(),
            "drag_coefficient": cd,
            "lift_coefficient": cl,
            "drag_force_n": round(drag_force, 4),
            "lift_force_n": round(lift_force, 4),
        }
        return r
    else:
        # Hagen-Poiseuille for circular pipe estimate
        D = 0.02; L = 0.1
        Re = rho * v_inlet * D / mu
        dP = 128 * mu * v_inlet * L / (3.14159 * D**4) if Re < 2300 else 0.5 * rho * v_inlet**2 * 0.02 * L / D

        r = CFDResult(
            max_velocity=round(v_inlet * 2.0, 4),
            max_pressure=round(dP, 2),
            pressure_drop=round(dP, 2),
        )
        r.result_data = r.to_dict()
        return r
