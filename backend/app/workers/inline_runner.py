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
    analysis_types: list[str],
    parameters: Dict[str, Any],
    mesh_file: Optional[str] = None,
) -> None:
    """Run multiple analysis types in parallel inline (asyncio, no Celery). Updates DB progress live."""

    # Give the FastAPI request handler time to commit the job row first
    await asyncio.sleep(0.3)

    # Coordinate progress updates
    progress_dict = {atype: 0 for atype in analysis_types}
    progress_msg_dict = {atype: "Queued" for atype in analysis_types}

    async def update_overall_progress():
        overall_pct = sum(progress_dict.values()) // len(analysis_types)
        overall_msg = "; ".join(f"{atype}: {progress_msg_dict[atype]}" for atype in analysis_types)
        try:
            async with get_db_context() as db:
                from sqlalchemy import select
                job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
                if job:
                    job.progress_percent = overall_pct
                    job.progress_message = overall_msg[:450]
        except Exception as e:
            logger.warning("Overall progress update failed", job_id=job_id, error=str(e))

    def make_progress_cb(atype: str):
        def cb(pct: int, msg: str):
            progress_dict[atype] = pct
            progress_msg_dict[atype] = msg
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(update_overall_progress())
            except Exception:
                pass
        return cb

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

        logger.info("Starting inline multiple analysis", job_id=job_id, types=analysis_types)

        async def run_single(atype_str: str):
            from app.models.db_models import AnalysisType
            atype = AnalysisType(atype_str)
            mesh_path = Path(mesh_file) if mesh_file else None
            summary_single = {}
            res_data_single = {}
            cb = make_progress_cb(atype_str)

            cb(10, "Starting solver initialization...")

            if atype == AnalysisType.STATIC_STRUCTURAL or atype == AnalysisType.NONLINEAR:
                from app.solvers.structural.calculix_wrapper import run_static_structural, StructuralResult
                solver_params = {**parameters}
                if atype == AnalysisType.NONLINEAR:
                    solver_params["nonlinear"] = True
                res: StructuralResult = await run_static_structural(job_id, mesh_path, solver_params, cb)
                summary_single = {
                    "max_stress": round(res.max_stress, 4),
                    "min_stress": round(res.min_stress, 4),
                    "max_displacement": round(res.max_displacement, 6),
                    "min_safety_factor": round(res.min_safety_factor, 3),
                }
                res_data_single = res.result_data or {}

            elif atype == AnalysisType.BUCKLING:
                from app.solvers.structural.calculix_wrapper import run_buckling, BucklingResult
                res: BucklingResult = await run_buckling(job_id, mesh_path, parameters, cb)
                summary_single = {
                    "buckling_factors": res.eigenvalues,
                    "min_buckling_factor": round(min(res.eigenvalues), 3) if res.eigenvalues else None,
                }
                res_data_single = res.result_data or {}

            elif atype == AnalysisType.MODAL:
                from app.solvers.structural.calculix_wrapper import run_modal, ModalResult
                res: ModalResult = await run_modal(job_id, mesh_path, parameters, cb)
                summary_single = {
                    "natural_frequencies": res.frequencies,
                    "mode_count": len(res.frequencies) if res.frequencies else 0,
                }
                res_data_single = res.result_data or {}

            elif atype in (AnalysisType.THERMAL_STEADY, AnalysisType.THERMAL_TRANSIENT, AnalysisType.THERMAL_STRUCTURAL):
                from app.solvers.thermal.thermal_solver import run_thermal, ThermalResult
                solver_params = {**parameters}
                if atype == AnalysisType.THERMAL_TRANSIENT:
                    solver_params["steady_state"] = False
                res: ThermalResult = await run_thermal(job_id, mesh_path, solver_params, cb)
                summary_single = {
                    "max_temperature": round(res.max_temperature, 2),
                    "min_temperature": round(res.min_temperature, 2),
                }
                res_data_single = res.result_data or {}

            elif atype == AnalysisType.FATIGUE:
                from app.solvers.fatigue.sn_curve import compute_fatigue_life, FatigueResult
                import numpy as np
                mat = parameters.get("material", {})
                stress_amplitude = float(parameters.get("stress_amplitude", 100.0))
                stress_ratio = float(parameters.get("stress_ratio", -1.0))
                correction = parameters.get("mean_stress_correction", "goodman")
                von_mises = np.array([stress_amplitude], dtype=float)

                cb(20, "Loading S-N curve data...")
                await asyncio.sleep(0.3)
                cb(60, "Running fatigue life calculation...")
                res: FatigueResult = await asyncio.to_thread(
                    compute_fatigue_life, von_mises, mat, stress_ratio, correction
                )
                cb(95, "Computing safety factors...")
                await asyncio.sleep(0.2)
                summary_single = {
                    "fatigue_life_cycles": res.min_life_cycles,
                    "min_safety_factor": round(res.min_safety_factor, 3),
                }
                res_data_single = res.result_data or {}

            elif atype in (AnalysisType.CFD_INTERNAL, AnalysisType.CFD_EXTERNAL):
                from app.solvers.cfd.openfoam_wrapper import run_cfd, CFDResult
                res: CFDResult = await run_cfd(job_id, mesh_path, parameters, cb, analysis_type=atype.value)
                summary_single = {
                    "max_velocity": round(res.max_velocity, 4),
                    "max_pressure": round(res.max_pressure, 2),
                    "pressure_drop": round(res.pressure_drop, 2),
                }
                res_data_single = res.result_data or {}

            else:
                raise ValueError(f"Unknown analysis type: {atype_str}")

            cb(100, "Done")
            return atype_str, summary_single, res_data_single

        # Run all selected analysis types in parallel
        tasks = [run_single(atype) for atype in analysis_types]
        results_list = await asyncio.gather(*tasks)

        # Aggregate summaries and results data
        merged_summary = {}
        merged_result_data = {}
        for atype_str, s, rd in results_list:
            merged_summary[atype_str] = s
            merged_result_data[atype_str] = rd

        # Extract scalar summary fields (lift up first available metric for DB columns compatibility)
        max_stress = None
        min_stress = None
        max_displacement = None
        min_safety_factor = None
        max_temperature = None
        natural_frequencies = None
        buckling_factors = None
        fatigue_life_cycles = None

        for _, s, _ in results_list:
            if s.get("max_stress") is not None: max_stress = s["max_stress"]
            if s.get("min_stress") is not None: min_stress = s["min_stress"]
            if s.get("max_displacement") is not None: max_displacement = s["max_displacement"]
            if s.get("min_safety_factor") is not None:
                if min_safety_factor is None or s["min_safety_factor"] < min_safety_factor:
                    min_safety_factor = s["min_safety_factor"]
            if s.get("max_temperature") is not None: max_temperature = s["max_temperature"]
            if s.get("natural_frequencies") is not None: natural_frequencies = s["natural_frequencies"]
            if s.get("buckling_factors") is not None: buckling_factors = s["buckling_factors"]
            if s.get("fatigue_life_cycles") is not None: fatigue_life_cycles = s["fatigue_life_cycles"]

        # ── Serialise numpy arrays in result_data ──────────────────────────────
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

        merged_result_data = _make_serialisable(merged_result_data)
        merged_summary = _make_serialisable(merged_summary)

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
                max_stress=max_stress,
                min_stress=min_stress,
                max_displacement=max_displacement,
                min_safety_factor=min_safety_factor,
                max_temperature=max_temperature,
                natural_frequencies=natural_frequencies,
                buckling_factors=buckling_factors,
                fatigue_life_cycles=fatigue_life_cycles,
                # Store full combined dictionary in result_data
                result_data={"summaries": merged_summary, "results": merged_result_data},
            )
            db.add(result_row)
            await db.flush()

            from app.results.report_generator import generate_reports_for_job
            await generate_reports_for_job(job_id, db)

        logger.info("Inline multiple analysis complete", job_id=job_id, types=analysis_types)

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
