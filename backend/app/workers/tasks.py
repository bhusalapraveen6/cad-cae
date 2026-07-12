"""
Celery tasks for analysis job execution.
"""
from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from app.workers.celery_app import celery_app
from app.config import settings

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, name="app.workers.tasks.run_analysis_task", max_retries=1)
def run_analysis_task(
    self,
    job_id: str,
    analysis_type: str,
    parameters: Dict[str, Any],
    mesh_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main analysis task. Called by the API after job creation.
    Updates job progress in the database and dispatches to the appropriate solver.
    """
    return _run_async(_run_analysis_async(self, job_id, analysis_type, parameters, mesh_file_path))


async def _run_analysis_async(
    task,
    job_id: str,
    analysis_type: str,
    parameters: Dict[str, Any],
    mesh_file_path: Optional[str],
) -> Dict[str, Any]:
    from app.database import get_db_context
    from app.models.db_models import Job, JobStatus, AnalysisResult

    log = logger.bind(job_id=job_id, analysis_type=analysis_type)
    log.info("Analysis task started")

    async def update_progress(pct: int, msg: str):
        async with get_db_context() as db:
            from sqlalchemy import select
            job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
            if job:
                job.progress_percent = pct
                job.progress_message = msg
                if not isinstance(job.log_messages, list):
                    job.log_messages = []
                job.log_messages = job.log_messages + [
                    {"pct": pct, "msg": msg, "ts": datetime.now(timezone.utc).isoformat()}
                ]
        log.debug("Progress update", pct=pct, msg=msg)

    # ── Set job to SOLVING ────────────────────────────────────────────────────
    async with get_db_context() as db:
        from sqlalchemy import select
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job.status = JobStatus.SOLVING
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = task.request.id

    try:
        mesh_file = Path(mesh_file_path) if mesh_file_path else None
        result_dict = {}

        # ── Dispatch to solver ────────────────────────────────────────────────
        if analysis_type == "static_structural":
            from app.solvers.structural.calculix_wrapper import run_static_structural
            result = await run_static_structural(job_id, mesh_file, parameters, update_progress)
            result_dict = result.to_dict()
            summary = {
                "max_stress": result.max_stress,
                "min_stress": result.min_stress,
                "max_displacement": result.max_displacement,
                "min_safety_factor": result.min_safety_factor,
            }

        elif analysis_type == "modal":
            from app.solvers.structural.calculix_wrapper import run_modal
            result = await run_modal(job_id, mesh_file, parameters, update_progress)
            result_dict = result.to_dict()
            summary = {
                "natural_frequencies": result.frequencies,
            }

        elif analysis_type == "thermal_steady" or analysis_type == "thermal_transient":
            from app.solvers.thermal.thermal_solver import run_thermal
            result = await run_thermal(job_id, mesh_file, parameters, update_progress)
            result_dict = result.to_dict()
            summary = {"max_temperature": result.max_temperature}

        elif analysis_type == "fatigue":
            from app.solvers.fatigue.sn_curve import compute_fatigue_life, _mock_fatigue_result
            if settings.mock_solver_mode:
                result = _mock_fatigue_result()
            else:
                # Load static result von Mises field
                result = compute_fatigue_life(
                    von_mises_field=None,
                    material=parameters.get("material", {}),
                    stress_ratio=parameters.get("stress_ratio", -1.0),
                    correction_method=parameters.get("mean_stress_correction", "goodman"),
                )
            result_dict = result.to_dict()
            summary = {
                "fatigue_life_cycles": result.min_life_cycles,
                "min_safety_factor": result.min_safety_factor,
            }

        elif analysis_type in ("cfd_internal", "cfd_external"):
            from app.solvers.cfd.openfoam_wrapper import run_cfd
            result = await run_cfd(job_id, mesh_file, parameters, update_progress)
            result_dict = result.to_dict()
            summary = {}

        else:
            # Generic mock for unimplemented types
            await update_progress(50, f"Running {analysis_type} (mock)…")
            await asyncio.sleep(2)
            await update_progress(100, "Complete")
            result_dict = {"status": "mock_complete"}
            summary = {}

        # ── Save result ───────────────────────────────────────────────────────
        async with get_db_context() as db:
            from sqlalchemy import select
            job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.progress_percent = 100

            analysis_result = AnalysisResult(
                job_id=job_id,
                max_stress=summary.get("max_stress"),
                min_stress=summary.get("min_stress"),
                max_displacement=summary.get("max_displacement"),
                max_temperature=summary.get("max_temperature"),
                min_safety_factor=summary.get("min_safety_factor"),
                natural_frequencies=summary.get("natural_frequencies"),
                fatigue_life_cycles=summary.get("fatigue_life_cycles"),
                result_data=result_dict,
            )
            db.add(analysis_result)

        log.info("Analysis completed successfully")
        return result_dict

    except Exception as exc:
        log.error("Analysis task failed", error=str(exc), tb=traceback.format_exc())
        async with get_db_context() as db:
            from sqlalchemy import select
            job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.completed_at = datetime.now(timezone.utc)
        raise


@celery_app.task(name="app.workers.tasks.generate_report_task")
def generate_report_task(job_id: str, format: str = "pdf") -> str:
    """Generate a PDF/DOCX report for a completed job."""
    return _run_async(_generate_report_async(job_id, format))


async def _generate_report_async(job_id: str, format: str) -> str:
    from app.results.report_generator import generate_pdf_report
    output_path = await generate_pdf_report(job_id)
    return str(output_path)
