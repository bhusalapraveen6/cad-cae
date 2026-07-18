"""
CAD file parser — supports STL/OBJ via trimesh (mock_cad_mode=True)
and STEP/IGES via pythonocc-core (mock_cad_mode=False).
Returns a unified GeometryData object.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class GeometryData:
    """Unified geometry representation from any supported CAD format."""
    volume: float = 0.0              # mm³
    surface_area: float = 0.0        # mm²
    bbox: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (dx, dy, dz) in mm
    center_of_mass: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    vertices: Optional[np.ndarray] = field(default=None, repr=False)   # (N,3) float32
    faces: Optional[np.ndarray]   = field(default=None, repr=False)    # (M,3) int32
    normals: Optional[np.ndarray] = field(default=None, repr=False)    # (M,3) float32
    # Feature hints populated during parsing
    is_watertight: bool = False
    num_components: int = 1
    format: str = "unknown"


async def parse_cad_file(file_path: Path) -> GeometryData:
    """
    Parse a CAD file and return structured geometry data.
    Dispatches to the appropriate parser based on file extension and mode.
    """
    suffix = file_path.suffix.lower()
    logger.info("Parsing CAD file", path=str(file_path), format=suffix, mock=settings.mock_cad_mode)

    if suffix in (".stl", ".obj", ".ply"):
        return await _parse_mesh_file(file_path, suffix)
    elif suffix in (".step", ".stp", ".iges", ".igs"):
        if settings.mock_cad_mode:
            logger.warning("Mock CAD mode: STEP/IGES parsed as synthetic geometry")
            return _synthetic_geometry(suffix)
        else:
            return await _parse_step_iges(file_path, suffix)
    else:
        raise ValueError(f"Unsupported CAD format: {suffix}")


async def _parse_mesh_file(file_path: Path, suffix: str) -> GeometryData:
    """Parse STL or OBJ using trimesh (runs on Windows natively)."""
    import trimesh

    mesh = trimesh.load(str(file_path), force="mesh")

    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(mesh.geometry.values())

    # Scale detection: if bounding box suggests metres, convert to mm
    bbox_extent = mesh.bounding_box.extents  # (dx, dy, dz)
    if max(bbox_extent) < 0.1:
        # Likely in metres, scale to mm
        mesh.apply_scale(1000.0)
        bbox_extent = mesh.bounding_box.extents

    volume = float(mesh.volume) if mesh.is_watertight else float(mesh.convex_hull.volume)
    surface_area = float(mesh.area)
    com = mesh.center_mass.tolist()

    return GeometryData(
        volume=volume,
        surface_area=surface_area,
        bbox=(float(bbox_extent[0]), float(bbox_extent[1]), float(bbox_extent[2])),
        center_of_mass=(float(com[0]), float(com[1]), float(com[2])),
        vertices=np.array(mesh.vertices, dtype=np.float32),
        faces=np.array(mesh.faces, dtype=np.int32),
        normals=np.array(mesh.face_normals, dtype=np.float32),
        is_watertight=bool(mesh.is_watertight),
        num_components=len(mesh.split()) if hasattr(mesh, 'split') else 1,
        format=suffix.lstrip("."),
    )


async def _parse_step_iges(file_path: Path, suffix: str) -> GeometryData:
    """
    Parse STEP/IGES using pythonocc-core (OpenCASCADE).
    Only available in Docker environment.
    """
    try:
        from OCC.Core.BRep import BRep_Builder
        from OCC.Core.BRepBndLib import brepbndlib
        from OCC.Core.BRepGProp import brepgprop
        from OCC.Core.Bnd import Bnd_Box
        from OCC.Core.GProp import GProp_GProps
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.IGESControl import IGESControl_Reader
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Extend.DataExchange import read_step_file, read_iges_file

        if suffix in (".step", ".stp"):
            shape = read_step_file(str(file_path))
        else:
            shape = read_iges_file(str(file_path))

        # Compute mass properties
        props = GProp_GProps()
        brepgprop.VolumeProperties(shape, props)
        volume = props.Mass()  # mm³ (assuming mm units)
        com_pt = props.CentreOfMass()

        brepgprop.SurfaceProperties(shape, props)
        surface_area = props.Mass()

        # Bounding box
        bbox = Bnd_Box()
        brepbndlib.Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

        # Tessellate for viewer
        BRepMesh_IncrementalMesh(shape, 0.5, False, 0.5, True)
        vertices, faces = _extract_occ_mesh(shape)

        return GeometryData(
            volume=abs(volume),
            surface_area=abs(surface_area),
            bbox=(abs(xmax - xmin), abs(ymax - ymin), abs(zmax - zmin)),
            center_of_mass=(com_pt.X(), com_pt.Y(), com_pt.Z()),
            vertices=vertices,
            faces=faces,
            is_watertight=True,
            format=suffix.lstrip("."),
        )
    except ImportError:
        logger.error("pythonocc-core not available; falling back to synthetic geometry")
        return _synthetic_geometry(suffix)


def _extract_occ_mesh(shape) -> Tuple[np.ndarray, np.ndarray]:
    """Extract tessellated mesh from an OCC BRep shape."""
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopoDS import topods

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    all_verts, all_faces = [], []
    offset = 0

    while explorer.More():
        face = topods.Face(explorer.Current())
        triangulation = BRep_Tool.Triangulation_s(face, face.Location())
        if triangulation is not None:
            nodes = triangulation.Nodes()
            tris = triangulation.Triangles()
            verts = np.array([[nodes.Value(i + 1).X(), nodes.Value(i + 1).Y(), nodes.Value(i + 1).Z()]
                               for i in range(nodes.Size())], dtype=np.float32)
            faces_arr = np.array([[tris.Value(i + 1).Get()[j] - 1 for j in range(3)]
                                   for i in range(tris.Size())], dtype=np.int32) + offset
            all_verts.append(verts)
            all_faces.append(faces_arr)
            offset += len(verts)
        explorer.Next()

    if not all_verts:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.int32)

    return np.concatenate(all_verts), np.concatenate(all_faces)


def _synthetic_geometry(suffix: str) -> GeometryData:
    """
    Return synthetic bracket-like geometry for mock/demo mode.
    Used when pythonocc-core is not available (Windows native dev).
    """
    # Simulate a steel bracket: ~100×50×30 mm
    volume = 100.0 * 50.0 * 30.0 * 0.6   # subtract material for hollow regions
    surface_area = 2 * (100 * 50 + 100 * 30 + 50 * 30) * 1.2

    # Cube vertices for visualization
    verts = np.array([
        [0, 0, 0], [100, 0, 0], [100, 50, 0], [0, 50, 0],
        [0, 0, 30], [100, 0, 30], [100, 50, 30], [0, 50, 30],
    ], dtype=np.float32)
    faces = np.array([
        [0,1,2],[0,2,3], [4,5,6],[4,6,7],
        [0,1,5],[0,5,4], [1,2,6],[1,6,5],
        [2,3,7],[2,7,6], [3,0,4],[3,4,7],
    ], dtype=np.int32)

    return GeometryData(
        volume=volume,
        surface_area=surface_area,
        bbox=(100.0, 50.0, 30.0),
        center_of_mass=(50.0, 25.0, 15.0),
        vertices=verts,
        faces=faces,
        is_watertight=True,
        num_components=1,
        format=suffix.lstrip("."),
    )
