import pytest
import numpy as np
import trimesh
from app.meshing.density import local_density_refine
from app.meshing.edit_ops import move_vertices, split_face_centroid, split_edge_midpoint, replace_patch
from app.meshing.smoothing import laplacian_smoothing
from app.geometry_analysis.mesh_quality import compute_mesh_quality

def create_test_cube():
    # Use trimesh to create a box
    mesh = trimesh.creation.box(extents=[10.0, 10.0, 10.0])
    return np.array(mesh.vertices, dtype=np.float32), np.array(mesh.faces, dtype=np.int32)

def test_local_density_refine():
    vertices, faces = create_test_cube()
    init_v_count = len(vertices)
    init_f_count = len(faces)
    
    # Subdivide faces in a bounding box containing part of the cube
    new_vertices, new_faces = local_density_refine(
        vertices, faces, bbox_min=[-6, -6, -6], bbox_max=[6, 6, 6], target_size=1.0
    )
    
    assert len(new_vertices) >= init_v_count
    assert len(new_faces) >= init_f_count
    assert not np.any(np.isnan(new_vertices))
    quality = compute_mesh_quality(new_vertices, new_faces)
    assert quality["overall_quality_score"] >= 0.0

def test_move_vertices():
    vertices, faces = create_test_cube()
    idx = [0]
    delta = [1.0, 0.0, 0.0]
    
    # Move without radius (topological falloff)
    new_vertices, new_faces = move_vertices(vertices, faces, idx, delta)
    assert np.allclose(new_vertices[0], vertices[0] + delta)
    # Check that neighbors also moved slightly
    assert not np.allclose(new_vertices[1], vertices[1])
    
    # Move with radius (Euclidean falloff)
    new_vertices_rad, _ = move_vertices(vertices, faces, idx, delta, radius=15.0)
    assert np.allclose(new_vertices_rad[0], vertices[0] + delta)
    assert not np.any(np.isnan(new_vertices_rad))

def test_split_face_centroid():
    vertices, faces = create_test_cube()
    init_v_count = len(vertices)
    init_f_count = len(faces)
    
    new_vertices, new_faces = split_face_centroid(vertices, faces, 0)
    assert len(new_vertices) == init_v_count + 1
    assert len(new_faces) == init_f_count + 2
    assert not np.any(np.isnan(new_vertices))
    
    quality = compute_mesh_quality(new_vertices, new_faces)
    assert quality["overall_quality_score"] >= 0.0

def test_split_edge_midpoint():
    vertices, faces = create_test_cube()
    init_v_count = len(vertices)
    init_f_count = len(faces)
    
    v_start, v_end = faces[0][0], faces[0][1]
    
    new_vertices, new_faces = split_edge_midpoint(vertices, faces, v_start, v_end)
    assert len(new_vertices) == init_v_count + 1
    assert len(new_faces) > init_f_count
    assert not np.any(np.isnan(new_vertices))

def test_replace_patch():
    vertices, faces = create_test_cube()
    init_v_count = len(vertices)
    init_f_count = len(faces)
    
    # Select first two faces as the patch
    patch_indices = [0, 1]
    new_vertices, new_faces = replace_patch(vertices, faces, patch_indices, target_size=1.0)
    
    assert len(new_vertices) >= init_v_count
    assert len(new_faces) >= init_f_count
    assert not np.any(np.isnan(new_vertices))
    
    quality = compute_mesh_quality(new_vertices, new_faces)
    assert quality["overall_quality_score"] >= 0.0

def test_laplacian_smoothing():
    vertices, faces = create_test_cube()
    
    new_vertices, new_faces = laplacian_smoothing(
        vertices, faces, iterations=5, lambda_param=0.5, pin_boundary=True, pin_sharp=True
    )
    
    assert len(new_vertices) == len(vertices)
    assert len(new_faces) == len(faces)
    assert not np.any(np.isnan(new_vertices))
    
    quality = compute_mesh_quality(new_vertices, new_faces)
    assert quality["overall_quality_score"] >= 0.0
