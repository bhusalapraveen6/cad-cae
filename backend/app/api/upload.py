"""Upload router — handles CAD file ingestion and geometry analysis."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.db_models import GeometryFeatures, Project
from app.models.schemas import UploadResponse

from app.api._routers import get_current_user
import app.models.db_models as M

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_cad_file(
    file: UploadFile = File(...),
    project_name: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    current_user: M.User = Depends(get_current_user),
):
    """
    Upload a CAD file (STEP, IGES, STL, OBJ).
    Returns project ID, geometry features, and analysis suggestions.
    """
    # ── Check file size & sanity check ────────────────────────────────────────
    file_bytes = await file.read()
    suffix = Path(file.filename).suffix.lower()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb} MB limit")

    # ── Save file ─────────────────────────────────────────────────────────────
    project_id = str(uuid.uuid4())
    upload_dir = settings.upload_dir / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / file.filename
    saved_path.write_bytes(file_bytes)
    logger.info("CAD file saved", path=str(saved_path), size_mb=round(size_mb, 2))

    # ── Parse geometry ────────────────────────────────────────────────────────
    from app.cad_import.parser import parse_cad_file
    from app.geometry_analysis.feature_extractor import extract_features
    from app.geometry_analysis.suggestion_engine import suggest_analyses

    geom_data = None
    features = None
    suggestions = []
    parsing_status = "success"
    error_message = None

    try:
        geom_data = await parse_cad_file(saved_path)
        features  = extract_features(geom_data)
        suggestions  = suggest_analyses(features, None)
    except Exception as e:
        logger.error("Geometry analysis/parsing failed", error=str(e), exc_info=True)
        parsing_status = "failed"
        error_message = str(e)

    # ── Persist to database ───────────────────────────────────────────────────
    name = project_name or Path(file.filename).stem
    project = Project(
        id=project_id,
        name=name,
        cad_filename=file.filename,
        cad_format=suffix.lstrip("."),
        cad_file_path=str(saved_path),
        cad_file_size=len(file_bytes),
        user_id=current_user.id,
    )
    db.add(project)

    com = features.center_of_mass if features else (0.0, 0.0, 0.0)
    geo_db = GeometryFeatures(
        project_id=project_id,
        volume=features.volume if features else None,
        surface_area=features.surface_area if features else None,
        bbox_x=features.bbox[0] if features else None,
        bbox_y=features.bbox[1] if features else None,
        bbox_z=features.bbox[2] if features else None,
        center_of_mass=f"{com[0]:.2f},{com[1]:.2f},{com[2]:.2f}",
        slenderness_ratio=features.slenderness_ratio if features else None,
        surface_volume_ratio=features.surface_volume_ratio if features else None,
        is_thin_walled=features.is_thin_walled if features else False,
        has_holes=features.has_holes if features else False,
        has_fillets=features.has_fillets if features else False,
        has_internal_cavity=features.has_internal_cavity if features else False,
        has_symmetry=features.has_symmetry if features else False,
        is_sheet_metal=features.is_sheet_metal if features else False,
        raw_features=features.raw if features else {},
        suggestions=[
            {
                "analysis_type": s.analysis_type.value,
                "title": s.title,
                "rationale": s.rationale,
                "confidence": s.confidence,
                "icon": s.icon,
                "category": s.category,
                "priority": s.priority,
            }
            for s in suggestions
        ],
    )
    db.add(geo_db)
    await db.flush()

    # ── Build response ────────────────────────────────────────────────────────
    from app.models.schemas import (
        AnalysisSuggestion, BoundingBox, GeometryFeaturesResponse
    )
    from app.models.db_models import AnalysisType

    geo_response = None
    if features:
        geo_response = GeometryFeaturesResponse(
            volume=features.volume,
            surface_area=features.surface_area,
            bounding_box=BoundingBox(x=features.bbox[0], y=features.bbox[1], z=features.bbox[2]),
            center_of_mass=list(features.center_of_mass),
            slenderness_ratio=features.slenderness_ratio,
            surface_volume_ratio=features.surface_volume_ratio,
            is_thin_walled=features.is_thin_walled,
            has_holes=features.has_holes,
            has_fillets=features.has_fillets,
            has_internal_cavity=features.has_internal_cavity,
            has_symmetry=features.has_symmetry,
            is_sheet_metal=features.is_sheet_metal,
        )

    return UploadResponse(
        project_id=project_id,
        filename=file.filename,
        file_format=suffix.lstrip("."),
        file_size=len(file_bytes),
        parsing_status=parsing_status,
        error_message=error_message,
        geometry_features=geo_response,
        suggestions=[
            AnalysisSuggestion(
                analysis_type=AnalysisType(s.analysis_type.value),
                title=s.title,
                rationale=s.rationale,
                confidence=s.confidence,
                icon=s.icon,
                category=s.category,
                priority=s.priority,
            )
            for s in suggestions
        ],
    )
