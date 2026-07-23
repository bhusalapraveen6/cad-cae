import numpy as np
import trimesh

def laplacian_smoothing(
    vertices: np.ndarray,
    faces: np.ndarray,
    iterations: int = 10,
    lambda_param: float = 0.5,
    pin_boundary: bool = True,
    pin_sharp: bool = True,
    sharp_threshold_deg: float = 30.0
) -> tuple[np.ndarray, np.ndarray]:
    """
    Laplacian smoothing of a mesh.
    Pins boundary vertices and/or sharp feature vertices if requested.
    """
    import trimesh
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    
    n_verts = len(vertices)
    pinned = np.zeros(n_verts, dtype=bool)
    
    # 1. Identify boundary vertices
    if pin_boundary:
        edges = mesh.edges_sorted
        unique_edges, counts = np.unique(edges, axis=0, return_counts=True)
        boundary_edges = unique_edges[counts == 1]
        if len(boundary_edges) > 0:
            pinned[boundary_edges.flatten()] = True
            
    # 2. Identify sharp feature vertices based on dihedral angles
    if pin_sharp:
        adj = mesh.face_adjacency
        if len(adj) > 0:
            normals = mesh.face_normals
            n0 = normals[adj[:, 0]]
            n1 = normals[adj[:, 1]]
            # Cosine of angles between normals
            dots = np.sum(n0 * n1, axis=1)
            dots = np.clip(dots, -1.0, 1.0)
            angles = np.arccos(dots) * 180.0 / np.pi
            
            # Sharp edges are where angle > threshold
            sharp_edges_mask = angles > sharp_threshold_deg
            sharp_edges = mesh.face_adjacency_edges[sharp_edges_mask]
            if len(sharp_edges) > 0:
                pinned[sharp_edges.flatten()] = True
                
    # 3. Perform smoothing iterations
    adj_list = [set() for _ in range(n_verts)]
    for face in faces:
        u, v, w = face
        adj_list[u].update([v, w])
        adj_list[v].update([u, w])
        adj_list[w].update([u, v])
        
    current_vertices = vertices.copy()
    for _ in range(iterations):
        next_vertices = current_vertices.copy()
        for i in range(n_verts):
            if pinned[i]:
                continue
            neighbors = list(adj_list[i])
            if len(neighbors) == 0:
                continue
            # Laplacian step: average of neighbor positions
            neighbor_avg = np.mean(current_vertices[neighbors], axis=0)
            next_vertices[i] = current_vertices[i] + lambda_param * (neighbor_avg - current_vertices[i])
        current_vertices = next_vertices
        
    return np.array(current_vertices, dtype=np.float32), faces
