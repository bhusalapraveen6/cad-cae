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


# ── Authentication & Security ──────────────────────────────────────────────────
import hashlib
import hmac
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_token(payload: dict, secret: str) -> str:
    payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
    return f"{payload_str}.{signature}"

def verify_token(token: str, secret: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_str, signature = parts
        expected_sig = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_str.encode()).decode())
        return payload
    except Exception:
        return None

def _get_master_key_bytes(secret: str) -> bytes:
    import hashlib
    return hashlib.sha256(secret.encode()).digest()

def encrypt_api_key(api_key: str, secret: str) -> str:
    import os
    key_bytes = _get_master_key_bytes(secret)
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, api_key.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_api_key(encrypted_base64: str, secret: str) -> str:
    try:
        key_bytes = _get_master_key_bytes(secret)
        aesgcm = AESGCM(key_bytes)
        data = base64.b64decode(encrypted_base64.encode())
        nonce = data[:12]
        ct = data[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()
    except Exception:
        return ""

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> M.User:
    tok = None
    if credentials:
        tok = credentials.credentials
    elif token:
        tok = token

    if not tok:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(tok, settings.secret_key)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload["user_id"]
    user = (await db.execute(select(M.User).where(M.User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def _get_project_verified(project_id: str, db: AsyncSession, user_id: str) -> M.Project:
    p = (
        await db.execute(
            select(M.Project)
            .where(M.Project.id == project_id)
            .where((M.Project.user_id == user_id) | M.Project.user_id.is_(None))
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return p

async def _get_job_verified(job_id: str, db: AsyncSession, user_id: str) -> M.Job:
    stmt = (
        select(M.Job)
        .join(M.Project)
        .where(M.Job.id == job_id)
        .where((M.Project.user_id == user_id) | M.Project.user_id.is_(None))
    )
    j = (await db.execute(stmt)).scalar_one_or_none()
    if not j:
        raise HTTPException(status_code=404, detail="Job not found or access denied")
    return j


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

# ── Authentication Router ──────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/auth")

@auth_router.post("/signup", status_code=201)
async def signup(body: S.UserSignupRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(M.User).where(M.User.username == body.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = M.User(username=body.username, hashed_password=hash_password(body.password))
    db.add(user)
    await db.flush()
    return {"success": True, "user_id": user.id, "username": user.username}

@auth_router.post("/login", response_model=S.TokenResponse)
async def login(body: S.UserLoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(M.User).where(M.User.username == body.username))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    token = create_token({"user_id": user.id, "username": user.username}, settings.secret_key)
    return S.TokenResponse(token=token, user_id=user.id, username=user.username)


@auth_router.get("/{provider}")
async def oauth_login(provider: str, redirect_uri: str):
    if provider not in ("google", "github", "microsoft"):
        raise HTTPException(status_code=400, detail="Invalid provider")
    state = "random-oauth-state"
    auth_urls = {
        "google": f"https://accounts.google.com/o/oauth2/v2/auth?client_id=google_client_id&response_type=code&scope=openid%20email%20profile&redirect_uri={redirect_uri}&state={state}",
        "github": f"https://github.com/login/oauth/authorize?client_id=github_client_id&scope=user:email&redirect_uri={redirect_uri}&state={state}",
        "microsoft": f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=ms_client_id&response_type=code&scope=openid%20email%20profile&redirect_uri={redirect_uri}&state={state}"
    }
    return {"url": auth_urls[provider]}


@auth_router.post("/callback", response_model=S.TokenResponse)
async def oauth_callback(body: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    provider = body.get("provider")
    code = body.get("code")
    if not provider or not code:
        raise HTTPException(status_code=400, detail="Provider and code are required")

    email = "oauth_user@example.com"
    if provider == "google":
        email = "google_user@gmail.com"
    elif provider == "github":
        email = "github_user@github.com"
    elif provider == "microsoft":
        email = "ms_user@outlook.com"

    # Match/link existing user by username (email) or provision a new one
    user = (await db.execute(select(M.User).where(M.User.username == email))).scalar_one_or_none()
    if not user:
        user = M.User(username=email, hashed_password=hash_password("oauth_locked_password_123!"))
        db.add(user)
        await db.flush()

    token = create_token({"user_id": user.id, "username": user.username}, settings.secret_key)
    return S.TokenResponse(token=token, user_id=user.id, username=user.username)


@auth_router.get("/api-key", response_model=S.UserApiKeyResponse)
async def get_user_api_key(
    current_user: M.User = Depends(get_current_user)
):
    if not current_user.gemini_api_key:
        return S.UserApiKeyResponse(has_key=False)
    
    decrypted = decrypt_api_key(current_user.gemini_api_key, settings.secret_key)
    if not decrypted:
        return S.UserApiKeyResponse(has_key=False)
    
    masked = decrypted[:6] + "..." + decrypted[-4:] if len(decrypted) > 10 else "AIzaSy..."
    return S.UserApiKeyResponse(has_key=True, masked_key=masked)


@auth_router.post("/api-key", response_model=S.UserApiKeyResponse)
async def update_user_api_key(
    body: S.UserApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user)
):
    encrypted = encrypt_api_key(body.gemini_api_key, settings.secret_key)
    current_user.gemini_api_key = encrypted
    await db.commit()
    
    masked = body.gemini_api_key[:6] + "..." + body.gemini_api_key[-4:] if len(body.gemini_api_key) > 10 else "AIzaSy..."
    return S.UserApiKeyResponse(has_key=True, masked_key=masked)


@auth_router.delete("/api-key", response_model=S.UserApiKeyResponse)
async def delete_user_api_key(
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user)
):
    current_user.gemini_api_key = None
    await db.commit()
    return S.UserApiKeyResponse(has_key=False)


# ── Projects ────────────────────────────────────────────────────────────────────

router = APIRouter()

projects_router = APIRouter(prefix="/projects")

@projects_router.get("", response_model=List[S.ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(M.Project)
            .where((M.Project.user_id == current_user.id) | M.Project.user_id.is_(None))
            .order_by(M.Project.created_at.desc())
        )
    ).scalars().all()
    result = []
    for p in rows:
        cnt = await _job_count(db, p.id)
        result.append(_project_response(p, cnt))
    return result


@projects_router.get("/{project_id}", response_model=S.ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    p = await _get_project_verified(project_id, db, current_user.id)
    cnt = await _job_count(db, p.id)
    return _project_response(p, cnt)


@projects_router.get("/{project_id}/geometry", response_model=S.GeometryFeaturesResponse)
async def get_geometry(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    await _get_project_verified(project_id, db, current_user.id)
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
async def get_suggestions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    await _get_project_verified(project_id, db, current_user.id)
    g = (await db.execute(
        select(M.GeometryFeatures).where(M.GeometryFeatures.project_id == project_id)
    )).scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Geometry not found — upload a CAD file first")
    return {"suggestions": g.suggestions or []}


@projects_router.get("/{project_id}/mesh")
async def get_project_mesh(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    p = await _get_project_verified(project_id, db, current_user.id)
    if not p.cad_file_path:
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
    current_user: M.User = Depends(get_current_user),
):
    """Create and dispatch an analysis job."""
    p = await _get_project_verified(project_id, db, current_user.id)

    job = M.Job(
        project_id=project_id,
        analysis_types=[t.value for t in body.analysis_types],
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
            await run_analysis_inline(job.id, [t.value for t in body.analysis_types], body.parameters, mesh_file)
        asyncio.create_task(_run_inline())
    else:
        # Dispatch to Celery (requires Redis + celery worker)
        try:
            from app.workers.tasks import run_multiple_analyses_task
            task = run_multiple_analyses_task.apply_async(
                args=[job.id, [t.value for t in body.analysis_types], body.parameters, mesh_file],
            )
            job.celery_task_id = task.id
        except ImportError:
            logger.warning("Celery not available — falling back to inline runner")
            import asyncio
            async def _run_inline_fallback():
                from app.workers.inline_runner import run_analysis_inline
                await run_analysis_inline(job.id, [t.value for t in body.analysis_types], body.parameters, mesh_file)
            asyncio.create_task(_run_inline_fallback())

    return S.JobResponse(
        id=job.id, project_id=job.project_id,
        analysis_types=[S.AnalysisType(t) for t in job.analysis_types], status=job.status,
        progress_percent=job.progress_percent,
        progress_message=job.progress_message,
        celery_task_id=job.celery_task_id,
        created_at=job.created_at, started_at=job.started_at,
        completed_at=job.completed_at, error_message=job.error_message,
    )


@analysis_router.get("", response_model=List[S.JobResponse])
async def list_jobs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    await _get_project_verified(project_id, db, current_user.id)
    jobs = (await db.execute(
        select(M.Job).where(M.Job.project_id == project_id).order_by(M.Job.created_at.desc())
    )).scalars().all()
    return [_job_response(j) for j in jobs]


def _job_response(j: M.Job) -> S.JobResponse:
    return S.JobResponse(
        id=j.id, project_id=j.project_id,
        analysis_types=[S.AnalysisType(t) for t in j.analysis_types], status=j.status,
        progress_percent=j.progress_percent, progress_message=j.progress_message,
        celery_task_id=j.celery_task_id,
        created_at=j.created_at, started_at=j.started_at,
        completed_at=j.completed_at, error_message=j.error_message,
    )


# ── Jobs (standalone router) ───────────────────────────────────────────────────

jobs_router = APIRouter(prefix="/jobs")


@jobs_router.get("/{job_id}", response_model=S.JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    j = await _get_job_verified(job_id, db, current_user.id)
    return _job_response(j)


@jobs_router.get("/{job_id}/progress")
async def job_progress_stream(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    """Server-Sent Events stream for live job progress."""
    # Verify ownership before opening the stream
    await _get_job_verified(job_id, db, current_user.id)

    async def event_generator() -> AsyncGenerator[str, None]:
        last_pct = -1
        for _ in range(300):  # 5 min max
            await db.rollback()
            # No need to verify ownership again in the loop, just fetch the job
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
async def get_results(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    await _get_job_verified(job_id, db, current_user.id)
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


@results_router.get("/pdf")
async def download_pdf_report(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    from fastapi.responses import FileResponse
    await _get_job_verified(job_id, db, current_user.id)
    r = (await db.execute(
        select(M.AnalysisResult).where(M.AnalysisResult.job_id == job_id)
    )).scalar_one_or_none()
    
    if not r or not r.report_pdf_path or not Path(r.report_pdf_path).exists():
        from app.results.report_generator import generate_reports_for_job
        pdf, _ = await generate_reports_for_job(job_id, db)
        if not pdf or not pdf.exists():
            raise HTTPException(404, "PDF report file not found and could not be generated")
        r_pdf_path = pdf
    else:
        r_pdf_path = Path(r.report_pdf_path)

    return FileResponse(
        r_pdf_path,
        media_type="application/pdf",
        filename=f"CAE_Report_{job_id}.pdf"
    )


@results_router.get("/docx")
async def download_docx_report(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    from fastapi.responses import FileResponse
    await _get_job_verified(job_id, db, current_user.id)
    r = (await db.execute(
        select(M.AnalysisResult).where(M.AnalysisResult.job_id == job_id)
    )).scalar_one_or_none()
    
    if not r or not r.report_docx_path or not Path(r.report_docx_path).exists():
        from app.results.report_generator import generate_reports_for_job
        _, docx = await generate_reports_for_job(job_id, db)
        if not docx or not docx.exists():
            raise HTTPException(404, "DOCX report file not found and could not be generated")
        r_docx_path = docx
    else:
        r_docx_path = Path(r.report_docx_path)

    return FileResponse(
        r_docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"CAE_Report_{job_id}.docx"
    )


# ── Materials ──────────────────────────────────────────────────────────────────

materials_router = APIRouter(prefix="/materials")


@materials_router.get("", response_model=List[S.MaterialSchema])
async def list_materials(
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user)
):
    from sqlalchemy import or_
    mats = (await db.execute(
        select(M.Material)
        .where(or_(M.Material.user_id == None, M.Material.user_id == current_user.id))
        .order_by(M.Material.name)
    )).scalars().all()
    return [S.MaterialSchema.model_validate(m) for m in mats]


@materials_router.post("", response_model=S.MaterialSchema, status_code=201)
async def create_material(
    body: S.MaterialSchema,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user)
):
    mat = M.Material(**body.model_dump(exclude={"id"}), user_id=current_user.id, is_custom=True)
    db.add(mat)
    await db.flush()
    return S.MaterialSchema.model_validate(mat)


# ── Chat ───────────────────────────────────────────────────────────────────────

chat_router = APIRouter(prefix="/chat")


@chat_router.post("")
async def chat(
    body: S.ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    """Send a message to the CAE chatbot. Returns streaming SSE response."""
    from app.chatbot.gemini_client import stream_chat_response
    from app.config import settings

    # Verify project ownership before proceeding
    await _get_project_verified(body.project_id, db, current_user.id)
    if body.job_id:
        await _get_job_verified(body.job_id, db, current_user.id)

    # Save user message
    user_msg = M.ChatMessage(
        project_id=body.project_id,
        job_id=body.job_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    user_api_key = None
    if current_user.gemini_api_key:
        user_api_key = decrypt_api_key(current_user.gemini_api_key, settings.secret_key)

    if not user_api_key and not settings.gemini_api_key:
        # Fallback stub
        async def stub():
            demo = (
                "I'm the CAE Analysis Assistant. Your Gemini API key isn't configured yet — "
                "set GEMINI_API_KEY in your .env file or provide your own API key in settings to enable full AI responses.\n\n"
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

    # Build context for Gemini
    context = await _build_chat_context(body.project_id, body.job_id, db)

    # Capture values needed by the generator
    project_id = body.project_id
    job_id = body.job_id
    message = body.message

    async def sse_generator():
        full_response = ""
        try:
            async for token in stream_chat_response(message, context, user_api_key=user_api_key):
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
                "types": j.analysis_types,
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
