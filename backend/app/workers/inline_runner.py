"""
Inline (non-Celery) analysis runner for development / mock mode.
Runs the same logic as the Celery task but as an asyncio coroutine,
allowing the FastAPI server to drive analyses without Redis.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import structlog

from app.config import settings
from app.database import get_db_context
from app.models.db_models import AnalysisResult, AnalysisType, Job, JobStatus

logger = structlog.get_logger(__name__)


async def run_analysis_inline(
    job_id: str,
    analysis_type: str,
    parameters: Dict[str, Any],
    mesh_file: Optional[str] = None,
) -> None:
    """Run an analysis job inline (asyncio, no Celery). Updates DB progress live."""

    # Give the FastAPI request handler time to commit the job row first
    await asyncio.sleep(0.3)

    async def update_progress(pct: int, msg: str) -> None:
        """Update job progress in the database."""
        try:
            async with get_db_context() as db:
                from sqlalchemy import select
                job = (await db.execute(
                    select(Job).where(Job.id == job_id)
                )).scalar_one_or_none()
                if job:
                    job.progress_percent = pct
                    job.progress_message = msg
        except Exception as e:
            logger.warning("Progress update failed", job_id=job_id, error=str(e))

    def sync_progress(pct: int, msg: str) -> None:
        """Sync wrapper for async update_progress — schedules on the running loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(update_progress(pct, msg))
        except Exception:
            pass

    try:
        # ── Mark job as SOLVING ────────────────────────────────────────────────
        job_found = False
        for attempt in range(3):
            async with get_db_context() as db:
                from sqlalchemy import select
                job = (await db.execute(
                    select(Job).where(Job.id == job_id)
                )).scalar_one_or_none()
                if job:
                    job.status = JobStatus.SOLVING
                    job.started_at = datetime.now(timezone.utc)
                    job.progress_percent = 0
                    job.progress_message = "Initializing..."
                    job_found = True
                    break
            if not job_found:
                logger.warning("Job not found yet, retrying", job_id=job_id, attempt=attempt)
                await asyncio.sleep(0.5)

        if not job_found:
            logger.error("Job not found after retries — aborting", job_id=job_id)
            return

        atype = AnalysisType(analysis_type)
        mesh_path = Path(mesh_file) if mesh_file else None
        logger.info("Starting inline analysis", job_id=job_id, type=analysis_type)

        # ── Dispatch to the correct solver ─────────────────────────────────────
        summary: Dict[str, Any] = {}
        result_data: Dict[str, Any] = {}

        if atype == AnalysisType.STATIC_STRUCTURAL or atype == AnalysisType.NONLINEAR:
            from app.solvers.structural.calculix_wrapper import run_static_structural, StructuralResult
            solver_params = {**parameters}
            if atype == AnalysisType.NONLINEAR:
                solver_params["nonlinear"] = True
            res: StructuralResult = await run_static_structural(job_id, mesh_path, solver_params, sync_progress)
            summary = {
                "max_stress": round(res.max_stress, 4),
                "min_stress": round(res.min_stress, 4),
                "max_displacement": round(res.max_displacement, 6),
                "min_safety_factor": round(res.min_safety_factor, 3),
            }
            result_data = res.result_data or {}

        elif atype == AnalysisType.BUCKLING:
            from app.solvers.structural.calculix_wrapper import run_buckling, BucklingResult
            res: BucklingResult = await run_buckling(job_id, mesh_path, parameters, sync_progress)
            summary = {
                "buckling_factors": res.eigenvalues,
                "min_buckling_factor": round(min(res.eigenvalues), 3) if res.eigenvalues else None,
            }
            result_data = res.result_data or {}

        elif atype == AnalysisType.MODAL:
            from app.solvers.structural.calculix_wrapper import run_modal, ModalResult
            res: ModalResult = await run_modal(job_id, mesh_path, parameters, sync_progress)
            summary = {
                "natural_frequencies": res.frequencies,
                "mode_count": len(res.frequencies) if res.frequencies else 0,
            }
            result_data = res.result_data or {}

        elif atype in (AnalysisType.THERMAL_STEADY, AnalysisType.THERMAL_TRANSIENT, AnalysisType.THERMAL_STRUCTURAL):
            from app.solvers.thermal.thermal_solver import run_thermal, ThermalResult
            solver_params = {**parameters}
            if atype == AnalysisType.THERMAL_TRANSIENT:
                solver_params["steady_state"] = False
            res: ThermalResult = await run_thermal(job_id, mesh_path, solver_params, sync_progress)
            summary = {
                "max_temperature": round(res.max_temperature, 2),
                "min_temperature": round(res.min_temperature, 2),
            }
            result_data = res.result_data or {}

        elif atype == AnalysisType.FATIGUE:
            from app.solvers.fatigue.sn_curve import compute_fatigue_life, FatigueResult
            import numpy as np
            mat = parameters.get("material", {})
            # Stress field from structural results or scalar fallback
            stress_amplitude = float(parameters.get("stress_amplitude", 100.0))
            stress_ratio = float(parameters.get("stress_ratio", -1.0))
            correction = parameters.get("mean_stress_correction", "goodman")
            # Build a minimal von-mises field for the fatigue calculation
            von_mises = np.array([stress_amplitude], dtype=float)

            await update_progress(20, "Loading S-N curve data...")
            await asyncio.sleep(0.3)
            await update_progress(60, "Running fatigue life calculation...")
            res: FatigueResult = await asyncio.to_thread(
                compute_fatigue_life, von_mises, mat, stress_ratio, correction
            )
            await update_progress(95, "Computing safety factors...")
            await asyncio.sleep(0.2)
            summary = {
                "fatigue_life_cycles": res.min_life_cycles,
                "min_safety_factor": round(res.min_safety_factor, 3),
            }
            result_data = res.result_data or {}

        elif atype in (AnalysisType.CFD_INTERNAL, AnalysisType.CFD_EXTERNAL):
            from app.solvers.cfd.openfoam_wrapper import run_cfd, CFDResult
            res: CFDResult = await run_cfd(job_id, mesh_path, parameters, sync_progress, analysis_type=atype.value)
            summary = {
                "max_velocity": round(res.max_velocity, 4),
                "max_pressure": round(res.max_pressure, 2),
                "pressure_drop": round(res.pressure_drop, 2),
            }
            result_data = res.result_data or {}

        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        # ── Serialise numpy arrays in result_data ──────────────────────────────
        import json
        def _make_serialisable(obj: Any) -> Any:
            try:
                import numpy as np
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.generic):
                    return obj.item()
            except ImportError:
                pass
            if isinstance(obj, dict):
                return {k: _make_serialisable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_make_serialisable(v) for v in obj]
            return obj

        result_data = _make_serialisable(result_data)
        summary = _make_serialisable(summary)

        # ── Save result and mark COMPLETED ─────────────────────────────────────
        async with get_db_context() as db:
            from sqlalchemy import select
            job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
            if job:
                job.status = JobStatus.COMPLETED
                job.progress_percent = 100
                job.progress_message = "Analysis complete"
                job.completed_at = datetime.now(timezone.utc)

            result_row = AnalysisResult(
                job_id=job_id,
                # Scalar summary fields (mapped from whichever analysis type ran)
                max_stress=summary.get("max_stress"),
                min_stress=summary.get("min_stress"),
                max_displacement=summary.get("max_displacement"),
                min_safety_factor=summary.get("min_safety_factor"),
                max_temperature=summary.get("max_temperature"),
                natural_frequencies=summary.get("natural_frequencies"),
                buckling_factors=summary.get("buckling_factors"),
                fatigue_life_cycles=summary.get("fatigue_life_cycles"),
                # Full result payload
                result_data={**summary, **result_data},
            )
            db.add(result_row)


        logger.info("Inline analysis complete", job_id=job_id, type=analysis_type, summary=summary)

    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        logger.error("Inline analysis failed", job_id=job_id, error=str(exc), traceback=tb)
        try:
            async with get_db_context() as db:
                from sqlalchemy import select
                job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                    job.progress_message = f"Failed: {exc}"
                    job.completed_at = datetime.now(timezone.utc)
        except Exception:
            pass
