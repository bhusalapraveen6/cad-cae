import numpy as np
import trimesh

def local_density_refine(
    vertices: np.ndarray,
    faces: np.ndarray,
    bbox_min: np.ndarray | list[float],
    bbox_max: np.ndarray | list[float],
    target_size: float
) -> tuple[np.ndarray, np.ndarray]:
    """
    Subdivides faces in a local bounding box whose edge lengths exceed target_size.
    Returns (new_vertices, new_faces).
    """
    bbox_min = np.array(bbox_min, dtype=np.float32)
    bbox_max = np.array(bbox_max, dtype=np.float32)
    
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    
    # Run subdivision iterations (up to 4 to prevent excessive element generation)
    for _ in range(4):
        centroids = mesh.triangles_center
        in_bbox = np.all((centroids >= bbox_min) & (centroids <= bbox_max), axis=1)
        if not np.any(in_bbox):
            break
            
        triangles = mesh.triangles[in_bbox]
        
        # Calculate edge lengths for the selected triangles
        e0 = np.linalg.norm(triangles[:, 0] - triangles[:, 1], axis=1)
        e1 = np.linalg.norm(triangles[:, 1] - triangles[:, 2], axis=1)
        e2 = np.linalg.norm(triangles[:, 2] - triangles[:, 0], axis=1)
        max_edges = np.maximum(np.maximum(e0, e1), e2)
        
        # Find which faces in bbox exceed target_size
        to_subdivide_local = np.where(max_edges > target_size)[0]
        if len(to_subdivide_local) == 0:
            break
            
        bbox_face_indices = np.where(in_bbox)[0]
        global_face_indices = bbox_face_indices[to_subdivide_local]
        
        new_vertices, new_faces = trimesh.remesh.subdivide(
            mesh.vertices, mesh.faces, face_index=global_face_indices
        )
        mesh = trimesh.Trimesh(vertices=new_vertices, faces=new_faces, process=False)
        
    return np.array(mesh.vertices, dtype=np.float32), np.array(mesh.faces, dtype=np.int32)
