"""Projects, Jobs, Analysis, Results, Materials, and Chat API routers."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_db_context
from app.models import db_models as M
from app.models import schemas as S

logger = structlog.get_logger(__name__)


async def _job_count(db: AsyncSession, project_id: str) -> int:
    """Count jobs for a project without triggering lazy loading."""
    result = await db.execute(
        select(func.count(M.Job.id)).where(M.Job.project_id == project_id)
    )
    return result.scalar() or 0


def _project_response(p: M.Project, job_count: int = 0) -> S.ProjectResponse:
    return S.ProjectResponse(
        id=p.id, name=p.name, description=p.description,
        cad_filename=p.cad_filename, cad_format=p.cad_format,
        cad_file_size=p.cad_file_size,
        created_at=p.created_at, updated_at=p.updated_at,
        job_count=job_count,
    )

# ── Projects ────────────────────────────────────────────────────────────────────

router = APIRouter()

projects_router = APIRouter(prefix="/projects")

@projects_router.get("", response_model=List[S.ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(M.Project).order_by(M.Project.created_at.desc()))).scalars().all()
    result = []
    for p in rows:
        cnt = await _job_count(db, p.id)
        result.append(_project_response(p, cnt))
    return result


@projects_router.get("/{project_id}", response_model=S.ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(M.Project).where(M.Project.id == project_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")
    cnt = await _job_count(db, p.id)
    return _project_response(p, cnt)


@projects_router.get("/{project_id}/geometry", response_model=S.GeometryFeaturesResponse)
async def get_geometry(project_id: str, db: AsyncSession = Depends(get_db)):
    g = (await db.execute(
        select(M.GeometryFeatures).where(M.GeometryFeatures.project_id == project_id)
    )).scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Geometry features not found")
    com = [float(x) for x in g.center_of_mass.split(",")] if g.center_of_mass else None
    return S.GeometryFeaturesResponse(
        volume=g.volume, surface_area=g.surface_area,
        bounding_box=S.BoundingBox(x=g.bbox_x or 0, y=g.bbox_y or 0, z=g.bbox_z or 0),
        center_of_mass=com,
        slenderness_ratio=g.slenderness_ratio,
        surface_volume_ratio=g.surface_volume_ratio,
        is_thin_walled=g.is_thin_walled,
        has_holes=g.has_holes,
        has_fillets=g.has_fillets,
        has_internal_cavity=g.has_internal_cavity,
        has_symmetry=g.has_symmetry,
        is_sheet_metal=g.is_sheet_metal,
        element_count=g.element_count,
        node_count=g.node_count,
        mesh_quality=g.mesh_quality,
    )


@projects_router.get("/{project_id}/suggestions")
async def get_suggestions(project_id: str, db: AsyncSession = Depends(get_db)):
    g = (await db.execute(
        select(M.GeometryFeatures).where(M.GeometryFeatures.project_id == project_id)
    )).scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Geometry not found — upload a CAD file first")
    return {"suggestions": g.suggestions or []}


@projects_router.get("/{project_id}/mesh")
async def get_project_mesh(project_id: str, db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(M.Project).where(M.Project.id == project_id))).scalar_one_or_none()
    if not p or not p.cad_file_path:
        raise HTTPException(404, "Project or CAD file not found")
    
    from pathlib import Path
    path = Path(p.cad_file_path)
    if not path.exists():
        raise HTTPException(404, "CAD file not found on disk")
        
    try:
        from app.cad_import.parser import parse_cad_file
        geom_data = await parse_cad_file(path)
        
        # Serialize vertices and faces
        verts = geom_data.vertices.tolist() if geom_data.vertices is not None else []
        faces = geom_data.faces.tolist() if geom_data.faces is not None else []
        
        return {
            "vertices": verts,
            "faces": faces,
            "bbox": geom_data.bbox,
            "center_of_mass": geom_data.center_of_mass
        }
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to load mesh: {e}")


# ── Analysis / Jobs ─────────────────────────────────────────────────────────────

analysis_router = APIRouter(prefix="/projects/{project_id}/jobs")


@analysis_router.post("", response_model=S.JobResponse, status_code=201)
async def create_job(
    project_id: str,
    body: S.JobCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create and dispatch an analysis job."""
    p = (await db.execute(select(M.Project).where(M.Project.id == project_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Project not found")

    job = M.Job(
        project_id=project_id,
        analysis_type=body.analysis_type,
        parameters=body.parameters,
        status=M.JobStatus.PENDING,
    )
    db.add(job)
    await db.flush()

    # Get mesh file path if available
    mesh_file = None
    geo = (await db.execute(
        select(M.GeometryFeatures).where(M.GeometryFeatures.project_id == project_id)
    )).scalar_one_or_none()
    if geo and p.cad_file_path:
        mesh_file = p.cad_file_path

    from app.config import settings
    if settings.mock_solver_mode:
        # Run analysis inline as a background asyncio task (no Celery needed)
        import asyncio
        async def _run_inline():
            from app.workers.inline_runner import run_analysis_inline
            await run_analysis_inline(job.id, body.analysis_type.value, body.parameters, mesh_file)
        asyncio.create_task(_run_inline())
    else:
        # Dispatch to Celery (requires Redis + celery worker)
        try:
            from app.workers.tasks import run_analysis_task
            task = run_analysis_task.apply_async(
                args=[job.id, body.analysis_type.value, body.parameters, mesh_file],
            )
            job.celery_task_id = task.id
        except ImportError:
            logger.warning("Celery not available — falling back to inline runner")
            import asyncio
            async def _run_inline_fallback():
                from app.workers.inline_runner import run_analysis_inline
                await run_analysis_inline(job.id, body.analysis_type.value, body.parameters, mesh_file)
            asyncio.create_task(_run_inline_fallback())

    return S.JobResponse(
        id=job.id, project_id=job.project_id,
        analysis_type=job.analysis_type, status=job.status,
        progress_percent=job.progress_percent,
        progress_message=job.progress_message,
        celery_task_id=job.celery_task_id,
        created_at=job.created_at, started_at=job.started_at,
        completed_at=job.completed_at, error_message=job.error_message,
    )


@analysis_router.get("", response_model=List[S.JobResponse])
async def list_jobs(project_id: str, db: AsyncSession = Depends(get_db)):
    jobs = (await db.execute(
        select(M.Job).where(M.Job.project_id == project_id).order_by(M.Job.created_at.desc())
    )).scalars().all()
    return [_job_response(j) for j in jobs]


def _job_response(j: M.Job) -> S.JobResponse:
    return S.JobResponse(
        id=j.id, project_id=j.project_id,
        analysis_type=j.analysis_type, status=j.status,
        progress_percent=j.progress_percent, progress_message=j.progress_message,
        celery_task_id=j.celery_task_id,
        created_at=j.created_at, started_at=j.started_at,
        completed_at=j.completed_at, error_message=j.error_message,
    )


# ── Jobs (standalone router) ───────────────────────────────────────────────────

jobs_router = APIRouter(prefix="/jobs")


@jobs_router.get("/{job_id}", response_model=S.JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    j = (await db.execute(select(M.Job).where(M.Job.id == job_id))).scalar_one_or_none()
    if not j:
        raise HTTPException(404, "Job not found")
    return _job_response(j)


@jobs_router.get("/{job_id}/progress")
async def job_progress_stream(job_id: str, db: AsyncSession = Depends(get_db)):
    """Server-Sent Events stream for live job progress."""
    async def event_generator() -> AsyncGenerator[str, None]:
        last_pct = -1
        for _ in range(300):  # 5 min max
            await db.rollback()
            j = (await db.execute(select(M.Job).where(M.Job.id == job_id))).scalar_one_or_none()

            if not j:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            if j.progress_percent != last_pct:
                last_pct = j.progress_percent
                payload = {
                    "job_id": job_id,
                    "status": j.status,
                    "progress_percent": j.progress_percent,
                    "message": j.progress_message or "",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield f"data: {json.dumps(payload)}\n\n"

            if j.status in (M.JobStatus.COMPLETED, M.JobStatus.FAILED, M.JobStatus.CANCELLED):
                yield f"data: {json.dumps({'done': True, 'status': j.status})}\n\n"
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Results ────────────────────────────────────────────────────────────────────

results_router = APIRouter(prefix="/jobs/{job_id}/results")


@results_router.get("", response_model=S.AnalysisResultResponse)
async def get_results(job_id: str, db: AsyncSession = Depends(get_db)):
    r = (await db.execute(
        select(M.AnalysisResult).where(M.AnalysisResult.job_id == job_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Results not found — job may still be running")
    return S.AnalysisResultResponse(
        id=r.id, job_id=r.job_id,
        summary=S.ResultSummary(
            max_stress=r.max_stress,
            min_stress=r.min_stress,
            max_displacement=r.max_displacement,
            max_temperature=r.max_temperature,
            min_temperature=r.result_data.get("min_temperature_c") if r.result_data else None,
            min_safety_factor=r.min_safety_factor,
            natural_frequencies=r.natural_frequencies,
            buckling_factors=r.buckling_factors,
            fatigue_life_cycles=r.fatigue_life_cycles,
        ),
        vtk_available=bool(r.vtk_file_path),
        report_pdf_available=bool(r.report_pdf_path),
        report_docx_available=bool(r.report_docx_path),
        result_data=r.result_data,
    )


# ── Materials ──────────────────────────────────────────────────────────────────

materials_router = APIRouter(prefix="/materials")


@materials_router.get("", response_model=List[S.MaterialSchema])
async def list_materials(db: AsyncSession = Depends(get_db)):
    mats = (await db.execute(select(M.Material).order_by(M.Material.name))).scalars().all()
    return [S.MaterialSchema.model_validate(m) for m in mats]


@materials_router.post("", response_model=S.MaterialSchema, status_code=201)
async def create_material(body: S.MaterialSchema, db: AsyncSession = Depends(get_db)):
    mat = M.Material(**body.model_dump(exclude={"id"}), is_custom=True)
    db.add(mat)
    await db.flush()
    return S.MaterialSchema.model_validate(mat)


# ── Chat ───────────────────────────────────────────────────────────────────────

chat_router = APIRouter(prefix="/chat")


@chat_router.post("")
async def chat(body: S.ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    """Send a message to the CAE chatbot. Returns streaming SSE response."""
    from app.chatbot.claude_client import stream_chat_response
    from app.config import settings

    # Save user message
    user_msg = M.ChatMessage(
        project_id=body.project_id,
        job_id=body.job_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    if not settings.anthropic_api_key:
        # Fallback stub
        async def stub():
            demo = (
                "I'm the CAE Analysis Assistant. Your Claude API key isn't configured yet — "
                "set ANTHROPIC_API_KEY in your .env file to enable full AI responses.\n\n"
                "In the meantime, here are some tips:\n"
                "- Upload a STEP, IGES, or STL file to begin\n"
                "- Select analysis types based on the suggestions\n"
                "- Fill in material properties and boundary conditions\n"
                "- Submit the job and monitor progress in real-time"
            )
            for char in demo:
                yield f"data: {json.dumps({'token': char})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(stub(), media_type="text/event-stream")

    # Build context for Claude
    context = await _build_chat_context(body.project_id, body.job_id, db)

    # Capture values needed by the generator (don't capture `db` — FastAPI closes
    # the dependency session when this function returns, before streaming finishes)
    project_id = body.project_id
    job_id = body.job_id
    message = body.message

    async def sse_generator():
        full_response = ""
        try:
            async for token in stream_chat_response(message, context):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # Save assistant response using a fresh session (FastAPI dep already closed)
        try:
            async with get_db_context() as save_db:
                asst_msg = M.ChatMessage(
                    project_id=project_id,
                    job_id=job_id,
                    role="assistant",
                    content=full_response,
                )
                save_db.add(asst_msg)
                await save_db.commit()
        except Exception as e:
            logger.warning(f"Failed to save assistant message: {str(e)}")

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


async def _build_chat_context(
    project_id: str,
    job_id: Optional[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """Gather project + job context to inject into the Claude system prompt."""
    ctx: Dict[str, Any] = {"project_id": project_id}

    p = (await db.execute(select(M.Project).where(M.Project.id == project_id))).scalar_one_or_none()
    if p:
        ctx["project_name"] = p.name
        ctx["cad_format"] = p.cad_format

    geo = (await db.execute(
        select(M.GeometryFeatures).where(M.GeometryFeatures.project_id == project_id)
    )).scalar_one_or_none()
    if geo:
        ctx["geometry"] = {
            "volume_mm3": geo.volume,
            "surface_area_mm2": geo.surface_area,
            "is_thin_walled": geo.is_thin_walled,
            "has_holes": geo.has_holes,
            "has_internal_cavity": geo.has_internal_cavity,
        }

    if job_id:
        j = (await db.execute(select(M.Job).where(M.Job.id == job_id))).scalar_one_or_none()
        if j:
            ctx["job"] = {
                "type": j.analysis_type,
                "status": j.status,
                "progress": j.progress_percent,
            }
        r = (await db.execute(
            select(M.AnalysisResult).where(M.AnalysisResult.job_id == job_id)
        )).scalar_one_or_none()
        if r:
            ctx["results"] = {
                "max_stress_mpa": r.max_stress,
                "max_displacement_mm": r.max_displacement,
                "safety_factor": r.min_safety_factor,
                "frequencies_hz": r.natural_frequencies,
            }

    # Last 10 chat messages for conversation history
    hist = (await db.execute(
        select(M.ChatMessage)
        .where(M.ChatMessage.project_id == project_id)
        .order_by(M.ChatMessage.created_at.desc())
        .limit(10)
    )).scalars().all()
    ctx["history"] = [
        {"role": m.role, "content": m.content}
        for m in reversed(hist)
    ]

    return ctx
