"""
Geometry feature extractor.
Takes a GeometryData object and computes feature flags used by the suggestion engine.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import structlog

from app.cad_import.parser import GeometryData

logger = structlog.get_logger(__name__)

# ── Thresholds ─────────────────────────────────────────────────────────────────

THIN_WALL_THRESHOLD = 5.0          # mm — if min bbox dim / max bbox dim < this fraction
SLENDERNESS_HIGH = 8.0             # max_dim / min_dim
SURFACE_VOLUME_THIN = 0.8          # mm⁻¹ — high ratio → shell-like part
CAVITY_VOLUME_FRACTION = 0.15      # internal void > 15% of convex hull → cavity


@dataclass
class GeometryFeatures:
    """Structured output from the feature extractor."""
    # Geometry metrics
    volume: float = 0.0
    surface_area: float = 0.0
    bbox: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    center_of_mass: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    slenderness_ratio: float = 1.0
    surface_volume_ratio: float = 0.0

    # Feature flags
    is_thin_walled: bool = False
    has_holes: bool = False
    has_fillets: bool = False
    has_internal_cavity: bool = False
    has_symmetry: bool = False
    is_sheet_metal: bool = False
    is_slender: bool = False

    # Mesh metadata (set after meshing)
    element_count: Optional[int] = None
    node_count: Optional[int] = None
    mesh_quality: Optional[float] = None

    # Raw numeric data for display
    raw: dict = None

    def __post_init__(self):
        if self.raw is None:
            self.raw = {}


def extract_features(geom: GeometryData) -> GeometryFeatures:
    """
    Analyse a GeometryData object and return enriched GeometryFeatures.
    Works with trimesh-parsed data on Windows; more accurate with pythonocc.
    """
    bbox = geom.bbox
    dx, dy, dz = float(bbox[0]), float(bbox[1]), float(bbox[2])

    dims_sorted = sorted([dx, dy, dz])
    min_dim = dims_sorted[0] if dims_sorted[0] > 0 else 1.0
    max_dim = dims_sorted[2] if dims_sorted[2] > 0 else 1.0

    slenderness = float(max_dim / min_dim)

    volume = float(max(geom.volume, 1e-9))
    sv_ratio = float(geom.surface_area / volume)   # mm⁻¹

    # ── Thin-wall detection ────────────────────────────────────────────────────
    thin_wall_ratio = float(dims_sorted[0] / dims_sorted[2] if dims_sorted[2] > 0 else 1.0)
    is_thin_walled = bool(thin_wall_ratio < 0.15 or sv_ratio > SURFACE_VOLUME_THIN)
    is_sheet_metal  = bool(thin_wall_ratio < 0.08)  # very thin plate

    # ── Hole / fillet detection ────────────────────────────────────────────────
    # Heuristic: use face normals variance — many small curved surfaces suggest holes/fillets
    has_holes = False
    has_fillets = False
    if geom.normals is not None and len(geom.normals) > 10:
        # Compute variance of face normals in XY plane
        nx_var = float(np.var(geom.normals[:, 0]))
        ny_var = float(np.var(geom.normals[:, 1]))
        nz_var = float(np.var(geom.normals[:, 2]))
        normal_variance = nx_var + ny_var + nz_var
        # High variance → many curved surfaces → holes/fillets likely
        has_holes = bool(normal_variance > 0.3)
        has_fillets = bool(normal_variance > 0.15)

    # ── Internal cavity detection ──────────────────────────────────────────────
    # Heuristic: if geometry is not watertight, or has multiple components, likely has cavities
    has_internal_cavity = bool(
        not geom.is_watertight or
        geom.num_components > 1 or
        _estimate_cavity_fraction(geom) > CAVITY_VOLUME_FRACTION
    )

    # ── Symmetry detection ─────────────────────────────────────────────────────
    has_symmetry = bool(_detect_symmetry(geom))

    # ── Slender ───────────────────────────────────────────────────────────────
    is_slender = bool(slenderness > SLENDERNESS_HIGH)

    from app.geometry_analysis.mesh_quality import compute_mesh_quality
    quality_data = compute_mesh_quality(geom.vertices, geom.faces)

    raw = {
        "bbox_x_mm": float(dx),
        "bbox_y_mm": float(dy),
        "bbox_z_mm": float(dz),
        "volume_mm3": round(float(geom.volume), 2),
        "surface_area_mm2": round(float(geom.surface_area), 2),
        "slenderness_ratio": round(float(slenderness), 2),
        "surface_volume_ratio": round(float(sv_ratio), 4),
        "thin_wall_ratio": round(float(thin_wall_ratio), 3),
        "is_watertight": bool(geom.is_watertight),
        "num_components": int(geom.num_components),
        "mesh_quality_metrics": quality_data,
    }

    features = GeometryFeatures(
        volume=float(geom.volume),
        surface_area=float(geom.surface_area),
        bbox=(float(geom.bbox[0]), float(geom.bbox[1]), float(geom.bbox[2])),
        center_of_mass=(float(geom.center_of_mass[0]), float(geom.center_of_mass[1]), float(geom.center_of_mass[2])),
        slenderness_ratio=float(slenderness),
        surface_volume_ratio=float(sv_ratio),
        is_thin_walled=bool(is_thin_walled),
        has_holes=bool(has_holes),
        has_fillets=bool(has_fillets),
        has_internal_cavity=bool(has_internal_cavity),
        has_symmetry=bool(has_symmetry),
        is_sheet_metal=bool(is_sheet_metal),
        is_slender=bool(is_slender),
        element_count=int(len(geom.faces)) if geom.faces is not None else 0,
        node_count=int(len(geom.vertices)) if geom.vertices is not None else 0,
        mesh_quality=float(quality_data["overall_quality_score"]) if quality_data["overall_quality_score"] is not None else None,
        raw=raw,
    )

    logger.info(
        "Geometry features extracted",
        slenderness=round(slenderness, 2),
        thin_wall=is_thin_walled,
        holes=has_holes,
        cavity=has_internal_cavity,
        symmetry=has_symmetry,
        elements=len(geom.faces) if geom.faces is not None else 0,
        nodes=len(geom.vertices) if geom.vertices is not None else 0,
        mesh_quality=round(quality_data["overall_quality_score"], 4),
    )

    return features


def _estimate_cavity_fraction(geom: GeometryData) -> float:
    """Rough estimate of internal void fraction using convex hull vs actual volume ratio."""
    if geom.vertices is None or len(geom.vertices) < 4:
        return 0.0
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(geom.vertices)
        convex_volume = float(hull.volume)  # mm³
        actual_volume = float(geom.volume)
        if convex_volume > 0 and actual_volume > 0:
            return float(max(0.0, (convex_volume - actual_volume) / convex_volume))
    except Exception:
        pass
    return 0.0


def _detect_symmetry(geom: GeometryData) -> bool:
    """
    Detect approximate symmetry by checking if center of mass is near
    the geometric centroid of the bounding box.
    """
    bbox = geom.bbox
    com = geom.center_of_mass
    centroid = (float(bbox[0]) / 2, float(bbox[1]) / 2, float(bbox[2]) / 2)

    # Allow 10% offset
    dx_frac = abs(float(com[0]) - centroid[0]) / (float(bbox[0]) + 1e-9)
    dy_frac = abs(float(com[1]) - centroid[1]) / (float(bbox[1]) + 1e-9)

    return bool(dx_frac < 0.10 or dy_frac < 0.10)
