"""
CalculiX solver wrapper — generates .inp input decks, runs ccx, parses .frd results.
Supports: static structural, modal, buckling.
Falls back to mock results when MOCK_SOLVER_MODE=true.
"""
from __future__ import annotations

import asyncio
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


# ── Result data classes ────────────────────────────────────────────────────────

class StructuralResult:
    def __init__(self):
        self.max_stress: float = 0.0         # MPa
        self.min_stress: float = 0.0
        self.max_displacement: float = 0.0   # mm
        self.min_safety_factor: float = 99.0
        self.node_coords: np.ndarray = np.zeros((0, 3))
        self.displacement_field: np.ndarray = np.zeros((0, 3))
        self.von_mises_field: np.ndarray = np.zeros((0,))
        self.result_data: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_stress_mpa": round(self.max_stress, 4),
            "min_stress_mpa": round(self.min_stress, 4),
            "max_displacement_mm": round(self.max_displacement, 6),
            "min_safety_factor": round(self.min_safety_factor, 3),
            "node_count": len(self.node_coords),
        }


class ModalResult:
    def __init__(self):
        self.frequencies: List[float] = []   # Hz
        self.mode_shapes: List[np.ndarray] = []
        self.result_data: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "natural_frequencies_hz": [round(f, 4) for f in self.frequencies],
            "num_modes": len(self.frequencies),
        }


class BucklingResult:
    def __init__(self):
        self.eigenvalues: List[float] = []   # buckling load factors
        self.mode_shapes: List[np.ndarray] = []
        self.result_data: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buckling_factors": [round(v, 4) for v in self.eigenvalues],
            "num_modes": len(self.eigenvalues),
        }


# ── Main solver functions ──────────────────────────────────────────────────────

async def run_static_structural(
    job_id: str,
    mesh_file: Path,
    parameters: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> StructuralResult:
    """Run CalculiX static structural analysis."""
    import shutil
    if settings.mock_solver_mode or not shutil.which(settings.ccx_binary):
        if not settings.mock_solver_mode:
            await _report(progress_callback, 5, "WARNING: CalculiX binary 'ccx' not found on system path.")
            await _report(progress_callback, 10, "Falling back to emulation solver mode...")
        return await _mock_static_result(parameters, progress_callback)

    workspace = settings.solver_workspace / job_id
    workspace.mkdir(parents=True, exist_ok=True)

    await _report(progress_callback, 10, "Generating CalculiX input deck…")
    inp_file = workspace / "job.inp"
    _write_static_inp(inp_file, mesh_file, parameters)

    await _report(progress_callback, 30, "Running CalculiX solver…")
    await _run_ccx(inp_file, workspace, progress_callback)

    await _report(progress_callback, 80, "Parsing results…")
    result = _parse_frd(workspace / "job.frd", parameters)

    await _report(progress_callback, 100, "Static structural complete")
    return result


async def run_modal(
    job_id: str,
    mesh_file: Path,
    parameters: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> ModalResult:
    """Run CalculiX modal (frequency) analysis."""
    import shutil
    if settings.mock_solver_mode or not shutil.which(settings.ccx_binary):
        if not settings.mock_solver_mode:
            await _report(progress_callback, 5, "WARNING: CalculiX binary 'ccx' not found on system path.")
            await _report(progress_callback, 10, "Falling back to emulation solver mode...")
        return await _mock_modal_result(parameters, progress_callback)

    workspace = settings.solver_workspace / job_id
    workspace.mkdir(parents=True, exist_ok=True)

    await _report(progress_callback, 10, "Generating modal input deck…")
    inp_file = workspace / "modal.inp"
    _write_modal_inp(inp_file, mesh_file, parameters)

    await _report(progress_callback, 30, "Running CalculiX FREQUENCY step…")
    await _run_ccx(inp_file, workspace, progress_callback)

    await _report(progress_callback, 85, "Extracting mode shapes…")
    result = _parse_modal_frd(workspace / "modal.frd", parameters)

    await _report(progress_callback, 100, "Modal analysis complete")
    return result


async def run_buckling(
    job_id: str,
    mesh_file: Path,
    parameters: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> BucklingResult:
    """Run CalculiX buckling analysis."""
    import shutil
    if settings.mock_solver_mode or not shutil.which(settings.ccx_binary):
        if not settings.mock_solver_mode:
            await _report(progress_callback, 5, "WARNING: CalculiX binary 'ccx' not found on system path.")
            await _report(progress_callback, 10, "Falling back to emulation solver mode...")
        return await _mock_buckling_result(parameters, progress_callback)

    workspace = settings.solver_workspace / job_id
    workspace.mkdir(parents=True, exist_ok=True)

    await _report(progress_callback, 10, "Generating buckling input deck…")
    inp_file = workspace / "buckling.inp"
    _write_buckling_inp(inp_file, mesh_file, parameters)

    await _report(progress_callback, 30, "Running CalculiX BUCKLE step…")
    await _run_ccx(inp_file, workspace, progress_callback)

    await _report(progress_callback, 85, "Extracting buckling factors…")
    result = _parse_buckling_frd(workspace / "buckling.frd", parameters)

    await _report(progress_callback, 100, "Buckling analysis complete")
    return result


# ── Input deck generators ──────────────────────────────────────────────────────

def _write_static_inp(
    inp_file: Path,
    mesh_file: Path,
    params: Dict[str, Any],
) -> None:
    """Generate a CalculiX .inp file for static structural analysis."""
    mat = params.get("material", {})
    E   = mat.get("youngs_modulus", 210.0) * 1000   # GPa → MPa
    nu  = mat.get("poissons_ratio", 0.3)
    rho = mat.get("density", 7850.0) * 1e-12       # kg/m³ → kg/mm³

    bcs = params.get("boundary_conditions", [])
    load_steps = params.get("load_steps", 1)
    nonlinear  = params.get("nonlinear", False)

    lines = [
        f"** CalculiX Static Structural — Job generated by CAD-CAE Analyzer",
        f"** Material: {mat.get('name', 'Unknown')}",
        f"*INCLUDE, INPUT={mesh_file}",
        f"",
        f"** Material definition",
        f"*MATERIAL, NAME=MAT",
        f"*ELASTIC",
        f"{E}, {nu}",
        f"*DENSITY",
        f"{rho}",
        f"",
        f"** Section assignment (all elements)",
        f"*SOLID SECTION, ELSET=EALL, MATERIAL=MAT",
        f"",
        f"** Boundary conditions",
    ]

    for bc in bcs:
        bc_type = bc.get("type", "")
        if bc_type == "fixed":
            node_set = _face_ids_to_nset(bc.get("face_ids", []))
            lines += [
                f"*NSET, NSET=FIXED_{bc.get('description','BC')}",
                f"  {node_set}",
                f"*BOUNDARY",
                f"  FIXED_{bc.get('description','BC')}, 1, 6, 0.0",
            ]
        elif bc_type == "force":
            node_set = _face_ids_to_nset(bc.get("face_ids", []))
            fx, fy, fz = bc.get("fx", 0), bc.get("fy", 0), bc.get("fz", 0)
            lines += [
                f"*NSET, NSET=FORCE_{bc.get('description','BC')}",
                f"  {node_set}",
                f"*CLOAD",
                f"  FORCE_{bc.get('description','BC')}, 1, {fx}",
                f"  FORCE_{bc.get('description','BC')}, 2, {fy}",
                f"  FORCE_{bc.get('description','BC')}, 3, {fz}",
            ]

    step_type = "*STEP, NLGEOM" if nonlinear else "*STEP"
    lines += [
        f"",
        f"** Analysis step",
        step_type,
        f"*STATIC",
        f"  0.1, 1.0, 0.01, 1.0",
        f"*NODE FILE",
        f"  U",
        f"*EL FILE",
        f"  S, MISES",
        f"*END STEP",
    ]

    inp_file.write_text("\n".join(lines))


def _write_modal_inp(
    inp_file: Path,
    mesh_file: Path,
    params: Dict[str, Any],
) -> None:
    """Generate a CalculiX .inp file for modal (frequency) analysis."""
    mat = params.get("material", {})
    E   = mat.get("youngs_modulus", 210.0) * 1000
    nu  = mat.get("poissons_ratio", 0.3)
    rho = mat.get("density", 7850.0) * 1e-12
    num_modes = params.get("num_modes", 10)

    lines = [
        f"** CalculiX Modal Analysis",
        f"*INCLUDE, INPUT={mesh_file}",
        f"*MATERIAL, NAME=MAT",
        f"*ELASTIC",
        f"{E}, {nu}",
        f"*DENSITY",
        f"{rho}",
        f"*SOLID SECTION, ELSET=EALL, MATERIAL=MAT",
        f"",
        f"*STEP",
        f"*FREQUENCY, STORAGE=YES",
        f"  {num_modes}",
        f"*NODE FILE",
        f"  U",
        f"*END STEP",
    ]

    inp_file.write_text("\n".join(lines))


def _write_buckling_inp(
    inp_file: Path,
    mesh_file: Path,
    params: Dict[str, Any],
) -> None:
    """Generate a CalculiX .inp file for linear buckling analysis."""
    mat = params.get("material", {})
    E   = mat.get("youngs_modulus", 210.0) * 1000   # GPa → MPa
    nu  = mat.get("poissons_ratio", 0.3)
    rho = mat.get("density", 7850.0) * 1e-12       # kg/m³ → kg/mm³
    num_modes = params.get("num_buckling_modes", 5)

    bcs = params.get("boundary_conditions", [])

    lines = [
        f"** CalculiX Buckling — Job generated by CAD-CAE Analyzer",
        f"** Material: {mat.get('name', 'Unknown')}",
        f"*INCLUDE, INPUT={mesh_file}",
        f"",
        f"** Material definition",
        f"*MATERIAL, NAME=MAT",
        f"*ELASTIC",
        f"{E}, {nu}",
        f"*DENSITY",
        f"{rho}",
        f"",
        f"** Section assignment",
        f"*SOLID SECTION, ELSET=EALL, MATERIAL=MAT",
        f"",
        f"** Step 1: Pre-load static step",
        f"*STEP",
        f"*STATIC",
    ]

    for bc in bcs:
        bc_type = bc.get("type", "")
        if bc_type == "fixed":
            node_set = _face_ids_to_nset(bc.get("face_ids", []))
            lines += [
                f"*NSET, NSET=FIXED_{bc.get('description','BC')}",
                f"  {node_set}",
                f"*BOUNDARY",
                f"  FIXED_{bc.get('description','BC')}, 1, 6, 0.0",
            ]
        elif bc_type == "force":
            node_set = _face_ids_to_nset(bc.get("face_ids", []))
            fx, fy, fz = bc.get("fx", 0), bc.get("fy", 0), bc.get("fz", 0)
            lines += [
                f"*NSET, NSET=FORCE_{bc.get('description','BC')}",
                f"  {node_set}",
                f"*CLOAD",
                f"  FORCE_{bc.get('description','BC')}, 1, {fx}",
                f"  FORCE_{bc.get('description','BC')}, 2, {fy}",
                f"  FORCE_{bc.get('description','BC')}, 3, {fz}",
            ]

    lines += [
        f"*END STEP",
        f"",
        f"** Step 2: Buckling eigenvalue step",
        f"*STEP",
        f"*BUCKLE",
        f"  {num_modes}",
        f"*NODE FILE",
        f"  U",
        f"*END STEP",
    ]

    inp_file.write_text("\n".join(lines))


def _face_ids_to_nset(face_ids: List[int]) -> str:
    """Convert face IDs to a dummy node set string."""
    if not face_ids:
        return "1, LAST"
    return ", ".join(str(f) for f in face_ids[:20])


# ── Subprocess runner ──────────────────────────────────────────────────────────

async def _run_ccx(
    inp_file: Path,
    workspace: Path,
    progress_callback: Optional[Callable],
) -> None:
    """Run CalculiX as a subprocess, streaming log output."""
    cmd = [settings.ccx_binary, "-i", inp_file.stem]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        log_lines = []
        async for line_bytes in proc.stdout:
            line = line_bytes.decode("utf-8", errors="replace").rstrip()
            log_lines.append(line)
            logger.debug("ccx", line=line)

            # Parse ccx progress indicators
            if "increment" in line.lower():
                await _report(progress_callback, 50, f"Solver: {line.strip()}")

        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"CalculiX exited with code {proc.returncode}\n" + "\n".join(log_lines[-20:]))

    except FileNotFoundError:
        raise RuntimeError(
            f"CalculiX binary '{settings.ccx_binary}' not found. "
            "Set MOCK_SOLVER_MODE=true or install CalculiX."
        )


# ── Result parsers ─────────────────────────────────────────────────────────────

def _parse_frd(frd_file: Path, params: Dict[str, Any]) -> StructuralResult:
    """Parse CalculiX .frd result file using meshio."""
    result = StructuralResult()
    if not frd_file.exists():
        raise FileNotFoundError(f"FRD file not found: {frd_file}")

    try:
        import meshio
        mesh = meshio.read(str(frd_file))

        # Extract displacements
        if "U" in mesh.point_data:
            displ = mesh.point_data["U"]
            magnitudes = np.linalg.norm(displ, axis=1)
            result.max_displacement = float(magnitudes.max())
            result.displacement_field = displ.astype(np.float32)

        # Extract von Mises stress
        if "S" in mesh.cell_data:
            s_data = np.concatenate([d for d in mesh.cell_data["S"]])
            result.max_stress = float(s_data.max())
            result.min_stress = float(s_data.min())
            result.von_mises_field = s_data.astype(np.float32)

        result.node_coords = np.array(mesh.points, dtype=np.float32)

        # Safety factor
        mat = params.get("material", {})
        yield_str = mat.get("yield_strength", 250.0)
        if result.max_stress > 0:
            result.min_safety_factor = yield_str / result.max_stress

    except Exception as e:
        logger.error("FRD parsing failed", error=str(e))
        raise

    result.result_data = result.to_dict()
    return result


def _parse_modal_frd(frd_file: Path, params: Dict[str, Any]) -> ModalResult:
    """Parse CalculiX .frd file for modal results."""
    result = ModalResult()
    if not frd_file.exists():
        return result

    # Simple text-based frequency extraction from .frd
    try:
        content = frd_file.read_text(errors="replace")
        freqs = []
        for line in content.splitlines():
            if "FREQUENCY" in line.upper() and "HZ" in line.upper():
                parts = line.split()
                for p in parts:
                    try:
                        f = float(p)
                        if 0 < f < 1e6:
                            freqs.append(f)
                    except ValueError:
                        pass
        result.frequencies = sorted(freqs)[: params.get("num_modes", 10)]
    except Exception as e:
        logger.error("Modal FRD parsing failed", error=str(e))

    result.result_data = result.to_dict()
    return result


def _parse_buckling_frd(frd_file: Path, params: Dict[str, Any]) -> BucklingResult:
    """Parse CalculiX .frd or .dat file for buckling eigenvalues (load factors)."""
    result = BucklingResult()
    if not frd_file.exists():
        return result

    # Check matching .dat file as well, since eigenvalues are usually printed there clearly
    dat_file = frd_file.with_suffix(".dat")
    eigenvalues = []

    files_to_check = [frd_file]
    if dat_file.exists():
        files_to_check.append(dat_file)

    for path in files_to_check:
        try:
            content = path.read_text(errors="replace")
            for line in content.splitlines():
                if "FACTOR" in line.upper() or "BUCKLING FACTOR" in line.upper():
                    parts = line.split()
                    for p in parts:
                        try:
                            clean_p = p.replace(":", "").replace("=", "")
                            val = float(clean_p)
                            if val not in eigenvalues and len(eigenvalues) < params.get("num_buckling_modes", 5):
                                eigenvalues.append(val)
                        except ValueError:
                            pass
        except Exception as e:
            logger.error("Error reading buckling result file", path=str(path), error=str(e))

    result.eigenvalues = sorted(eigenvalues)
    result.result_data = result.to_dict()
    return result


# ── Mock results ───────────────────────────────────────────────────────────────

async def _mock_static_result(
    params: Dict[str, Any],
    progress_callback: Optional[Callable],
) -> StructuralResult:
    """Generate physically plausible mock static/nonlinear results for demo/dev mode."""
    import asyncio
    import random

    mat = params.get("material", {})
    yield_str = mat.get("yield_strength", 250.0)  # MPa
    is_nonlinear = params.get("nonlinear", False)

    stages = [
        (15, "Setting up non-linear elastoplastic model…"),
        (15, "Setting up non-linear elastoplastic model..."),
        (30, "Increment 1: Solving load step (10% loaded)..."),
        (50, "Increment 2: Plasticity iterations (40% loaded)..."),
        (70, "Increment 3: Converging non-linear equilibrium (75% loaded)..."),
        (85, "Increment 4: Solving final load step (100% loaded)..."),
        (95, "Extracting elastoplastic stress/strain fields..."),
        (100, "Non-linear structural analysis complete [OK]"),
    ] if is_nonlinear else [
        (15, "Setting up finite element model..."),
        (30, "Assembling stiffness matrix..."),
        (50, "Solving linear system (PCG)..."),
        (70, "Computing stress and strain fields..."),
        (85, "Computing von Mises equivalent stress..."),
        (95, "Extracting result fields..."),
        (100, "Static structural complete [OK]"),
    ]
    for pct, msg in stages:
        await _report(progress_callback, pct, msg)
        await asyncio.sleep(0.6)

    # Synthetic cantilever-beam-like result
    bcs = params.get("boundary_conditions", [])
    total_force = sum(
        abs(bc.get("fz", 0)) + abs(bc.get("fy", 0)) + abs(bc.get("fx", 0))
        for bc in bcs if bc.get("type") == "force"
    ) or 1000.0  # N

    E_gpa = mat.get("youngs_modulus", 210.0)
    # Simple cantilever: δ = FL³/(3EI), σ = M*c/I
    L = 100e-3; b = 10e-3; h = 10e-3  # m
    I = b * h**3 / 12
    F = total_force
    max_disp = F * L**3 / (3 * E_gpa * 1e9 * I) * 1000  # mm
    max_stress = F * L * (h / 2) / I / 1e6  # MPa

    # Simulate non-linear yielding
    if is_nonlinear and max_stress > yield_str:
        excess_stress = max_stress - yield_str
        max_stress = yield_str + excess_stress * 0.15  # plastic hardening slope
        max_disp = max_disp * 1.6  # larger displacement due to plastic compliance

    result = StructuralResult()
    result.max_stress = round(max_stress + random.uniform(-5, 5), 2)
    result.min_stress = 0.0
    result.max_displacement = round(max_disp + random.uniform(-0.01, 0.01), 4)
    result.min_safety_factor = round(yield_str / max(result.max_stress, 1.0), 2)

    # Generate a small synthetic mesh for viewer
    n = 50
    xs = np.linspace(0, 100, n)
    result.node_coords = np.column_stack([xs, np.zeros(n), np.zeros(n)]).astype(np.float32)
    # Displacement field: zero at x=0, max at x=100
    result.displacement_field = np.column_stack([
        np.zeros(n), np.zeros(n),
        np.linspace(0, result.max_displacement, n)
    ]).astype(np.float32)
    result.von_mises_field = np.linspace(result.min_stress, result.max_stress, n).astype(np.float32)
    result.result_data = result.to_dict()
    return result


async def _mock_modal_result(
    params: Dict[str, Any],
    progress_callback: Optional[Callable],
) -> ModalResult:
    import asyncio

    stages = [
        (20, "Assembling mass matrix..."),
        (50, "Running Lanczos eigensolver..."),
        (85, "Normalising mode shapes..."),
        (100, "Modal analysis complete [OK]"),
    ]
    for pct, msg in stages:
        await _report(progress_callback, pct, msg)
        await asyncio.sleep(0.5)

    mat = params.get("material", {})
    E_gpa = mat.get("youngs_modulus", 210.0)
    rho   = mat.get("density", 7850.0)
    n     = params.get("num_modes", 10)

    # Euler-Bernoulli beam frequencies (approximate)
    L = 0.1; b = 0.01; h = 0.01
    beta_n = [1.8751, 4.6941, 7.8548, 10.996, 14.137, 17.279, 20.420, 23.562, 26.704, 29.845]
    E = E_gpa * 1e9; A = b * h; I = b * h**3 / 12
    freqs = []
    for i in range(min(n, len(beta_n))):
        f = (beta_n[i]**2 / (2 * math.pi)) * math.sqrt(E * I / (rho * A * L**4))
        freqs.append(round(f, 2))

    result = ModalResult()
    result.frequencies = freqs[:n]
    result.result_data = result.to_dict()
    return result


async def _mock_buckling_result(
    params: Dict[str, Any],
    progress_callback: Optional[Callable],
) -> BucklingResult:
    """Generate physically plausible mock buckling eigenvalues for demo/dev mode."""
    import asyncio
    import random

    stages = [
        (20, "Assembling geometric stiffness matrix..."),
        (50, "Solving buckling eigenvalue problem..."),
        (85, "Extracting buckling modes..."),
        (100, "Buckling analysis complete [OK]"),
    ]
    for pct, msg in stages:
        await _report(progress_callback, pct, msg)
        await asyncio.sleep(0.5)

    n = params.get("num_buckling_modes", 5)
    # Generate physically plausible buckling factors.
    base_factor = round(random.uniform(1.2, 2.5), 3)
    factors = [round(base_factor * (i + 1) + random.uniform(-0.05, 0.05), 3) for i in range(n)]

    result = BucklingResult()
    result.eigenvalues = sorted(factors)
    result.result_data = result.to_dict()
    return result


# ── Utility ────────────────────────────────────────────────────────────────────

async def _report(callback: Optional[Callable], pct: int, msg: str) -> None:
    if callback:
        if asyncio.iscoroutinefunction(callback):
            await callback(pct, msg)
        else:
            callback(pct, msg)
