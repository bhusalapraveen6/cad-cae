import numpy as np
import trimesh

def move_vertices(
    vertices: np.ndarray,
    faces: np.ndarray,
    vertex_indices: list[int],
    delta: list[float] | np.ndarray,
    radius: float | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """
    Move vertex_indices by delta, with falloff propagation to neighbors.
    If radius is given, use Euclidean distance falloff.
    Otherwise, use topological graph-ring falloff (3 rings).
    """
    new_vertices = np.array(vertices, dtype=np.float32)
    delta = np.array(delta, dtype=np.float32)
    
    if len(vertex_indices) == 0:
        return new_vertices, faces
        
    if radius is not None and radius > 0:
        # Euclidean distance falloff
        weights = np.zeros(len(vertices), dtype=np.float32)
        for v_idx in vertex_indices:
            if v_idx < 0 or v_idx >= len(vertices):
                continue
            v_coord = vertices[v_idx]
            dists = np.linalg.norm(vertices - v_coord, axis=1)
            v_weights = np.clip(1.0 - dists / radius, 0.0, 1.0)
            weights = np.maximum(weights, v_weights)
            
        new_vertices += weights[:, np.newaxis] * delta
    else:
        # Topological neighbor falloff (ring-based BFS)
        adj = [set() for _ in range(len(vertices))]
        for face in faces:
            u, v, w = face
            adj[u].update([v, w])
            adj[v].update([u, w])
            adj[w].update([u, v])
            
        weights = np.zeros(len(vertices), dtype=np.float32)
        for start_v in vertex_indices:
            if start_v < 0 or start_v >= len(vertices):
                continue
            visited = {start_v: 0.0}
            queue = [(start_v, 0)]
            while queue:
                curr, depth = queue.pop(0)
                weight = 1.0 / (2**depth)
                weights[curr] = max(weights[curr], weight)
                if depth < 3:
                    for neighbor in adj[curr]:
                        if neighbor not in visited or visited[neighbor] > depth + 1:
                            visited[neighbor] = depth + 1
                            queue.append((neighbor, depth + 1))
                            
        new_vertices += weights[:, np.newaxis] * delta
        
    return new_vertices, faces

def split_face_centroid(
    vertices: np.ndarray,
    faces: np.ndarray,
    face_index: int
) -> tuple[np.ndarray, np.ndarray]:
    """
    1-to-3 split of a selected face by inserting a vertex at its centroid.
    """
    if face_index < 0 or face_index >= len(faces):
        raise ValueError(f"Face index {face_index} is out of bounds.")
        
    new_vertices = list(vertices)
    new_faces = list(faces)
    
    face = faces[face_index]
    v0, v1, v2 = face
    
    # Calculate centroid
    centroid = (vertices[v0] + vertices[v1] + vertices[v2]) / 3.0
    new_vertices.append(centroid)
    new_v_idx = len(new_vertices) - 1
    
    # Remove old face, add 3 new ones
    new_faces.pop(face_index)
    new_faces.append([v0, v1, new_v_idx])
    new_faces.append([v1, v2, new_v_idx])
    new_faces.append([v2, v0, new_v_idx])
    
    return np.array(new_vertices, dtype=np.float32), np.array(new_faces, dtype=np.int32)

def split_edge_midpoint(
    vertices: np.ndarray,
    faces: np.ndarray,
    v_start: int,
    v_end: int
) -> tuple[np.ndarray, np.ndarray]:
    """
    Split the edge between v_start and v_end by inserting a vertex at the midpoint
    and splitting the adjacent faces to prevent T-junctions.
    """
    if v_start < 0 or v_start >= len(vertices) or v_end < 0 or v_end >= len(vertices):
        raise ValueError("Vertex index is out of bounds.")
        
    new_vertices = list(vertices)
    new_faces = []
    
    # Calculate midpoint
    midpoint = (vertices[v_start] + vertices[v_end]) / 2.0
    new_vertices.append(midpoint)
    new_v_idx = len(new_vertices) - 1
    
    edge = {v_start, v_end}
    
    for face in faces:
        v0, v1, v2 = face
        edges_in_face = [{v0, v1}, {v1, v2}, {v2, v0}]
        if edge in edges_in_face:
            if edge == {v0, v1}:
                opposite = v2
                new_faces.append([v0, new_v_idx, opposite])
                new_faces.append([new_v_idx, v1, opposite])
            elif edge == {v1, v2}:
                opposite = v0
                new_faces.append([v1, new_v_idx, opposite])
                new_faces.append([new_v_idx, v2, opposite])
            else: # edge == {v2, v0}
                opposite = v1
                new_faces.append([v2, new_v_idx, opposite])
                new_faces.append([new_v_idx, v0, opposite])
        else:
            new_faces.append(face)
            
    return np.array(new_vertices, dtype=np.float32), np.array(new_faces, dtype=np.int32)

def replace_patch(
    vertices: np.ndarray,
    faces: np.ndarray,
    patch_face_indices: list[int],
    target_size: float
) -> tuple[np.ndarray, np.ndarray]:
    """
    Replace patch_face_indices with a new tessellation at target_size.
    Isolates the patch, remeshes/subdivides, and merges it back, mapping boundary vertices.
    """
    if len(patch_face_indices) == 0:
        return vertices, faces
        
    face_mask = np.ones(len(faces), dtype=bool)
    face_mask[patch_face_indices] = False
    
    keep_faces = faces[face_mask]
    patch_faces = faces[~face_mask]
    
    # Find boundary vertices of the patch (vertices shared with kept mesh)
    keep_verts = set(keep_faces.flatten())
    patch_verts = set(patch_faces.flatten())
    boundary_verts = np.array(list(keep_verts.intersection(patch_verts)), dtype=np.int32)
    
    # Submesh of the patch
    patch_mesh = trimesh.Trimesh(vertices=vertices, faces=patch_faces, process=False)
    
    # Subdivide patch mesh to target_size
    try:
        from trimesh.remesh import subdivide_to_size
        new_patch_verts, new_patch_faces = subdivide_to_size(patch_mesh.vertices, patch_mesh.faces, max_edge=target_size)
    except Exception:
        new_patch_verts, new_patch_faces = patch_mesh.vertices, patch_mesh.faces
        for _ in range(3):
            e = patch_mesh.edges_unique_length
            if len(e) == 0 or np.max(e) <= target_size:
                break
            new_patch_verts, new_patch_faces = trimesh.remesh.subdivide(new_patch_verts, new_patch_faces)
            patch_mesh = trimesh.Trimesh(vertices=new_patch_verts, faces=new_patch_faces, process=False)
            
    # Merge patch back with kept vertices
    merged_vertices = list(vertices)
    patch_to_merged = {}
    
    for i, pt in enumerate(new_patch_verts):
        # Check boundary proximity
        if len(boundary_verts) > 0:
            dists = np.linalg.norm(vertices[boundary_verts] - pt, axis=1)
            min_idx = np.argmin(dists)
            if dists[min_idx] < 1e-4:
                patch_to_merged[i] = int(boundary_verts[min_idx])
                continue
                
        # Check overall proximity to original vertices
        dists_all = np.linalg.norm(vertices - pt, axis=1)
        min_idx_all = np.argmin(dists_all)
        if dists_all[min_idx_all] < 1e-4:
            patch_to_merged[i] = int(min_idx_all)
        else:
            merged_vertices.append(pt)
            patch_to_merged[i] = len(merged_vertices) - 1
            
    # Assemble final face list
    merged_faces = list(keep_faces)
    for face in new_patch_faces:
        merged_faces.append([patch_to_merged[face[0]], patch_to_merged[face[1]], patch_to_merged[face[2]]])
        
    return np.array(merged_vertices, dtype=np.float32), np.array(merged_faces, dtype=np.int32)
