import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import db_models as M
from app.cad_import.parser import parse_cad_file
from app.geometry_analysis.feature_extractor import extract_features

async def rebuild_mesh(
    project_id: str,
    db: AsyncSession,
    global_element_size: float
) -> dict:
    """
    Resets any edited/modified mesh and regenerates it from CAD file using the new global size.
    Updates the GeometryFeatures database record.
    """
    p = (
        await db.execute(
            select(M.Project)
            .where(M.Project.id == project_id)
        )
    ).scalar_one_or_none()
    if not p:
        raise ValueError("Project not found")
        
    path = Path(p.cad_file_path)
    edited_path = path.parent / f"{project_id}_edited.stl"
    if edited_path.exists():
        try:
            os.remove(edited_path)
        except Exception:
            pass
        
    g = (await db.execute(
        select(M.GeometryFeatures).where(M.GeometryFeatures.project_id == project_id)
    )).scalar_one_or_none()
    if not g:
        raise ValueError("Geometry features not found")
        
    geom_data = await parse_cad_file(path, deflection=global_element_size)
    features = extract_features(geom_data)
    
    g.element_count = features.element_count
    g.node_count = features.node_count
    g.mesh_quality = features.mesh_quality
    
    raw = g.raw_features or {}
    raw["mesh_settings"] = {
        "global_element_size": global_element_size,
        "refine_curvature": False
    }
    raw["mesh_quality_metrics"] = features.raw.get("mesh_quality_metrics")
    g.raw_features = raw
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(g, "raw_features")
    
    await db.commit()
    
    return {
        "success": True,
        "element_count": g.element_count,
        "node_count": g.node_count,
        "mesh_quality": g.mesh_quality,
        "mesh_quality_metrics": raw["mesh_quality_metrics"]
    }
