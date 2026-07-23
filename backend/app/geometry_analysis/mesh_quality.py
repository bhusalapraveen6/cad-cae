import numpy as np
from typing import Dict, Any, Optional

def compute_mesh_quality(vertices: Optional[np.ndarray], faces: Optional[np.ndarray]) -> Dict[str, Any]:
    """
    Compute standard mesh quality metrics:
    - Aspect Ratio (normalized so equilateral = 1.0)
    - Skewness (0.0 to 1.0)
    - Jacobian Ratio (approximate proxy based on shape distortion)
    - Min and Max element angles (in degrees)
    
    Flags elements exceeding acceptable thresholds.
    """
    default_metrics = {
        "aspect_ratio": {"mean": 1.0, "max": 1.0, "min": 1.0},
        "skewness": {"mean": 0.0, "max": 0.0, "min": 0.0},
        "jacobian_ratio": {"mean": 1.0, "max": 1.0, "min": 1.0},
        "angles": {
            "min_angle_mean": 60.0, "min_angle_min": 60.0,
            "max_angle_mean": 60.0, "max_angle_max": 60.0
        },
        "flagged_counts": {
            "aspect_ratio": 0,
            "skewness": 0,
            "jacobian_ratio": 0,
            "min_angle": 0,
            "max_angle": 0,
            "total_flagged": 0
        },
        "overall_quality_score": 1.0
    }

    if vertices is None or faces is None or len(vertices) == 0 or len(faces) == 0:
        return default_metrics

    try:
        # Get coordinates for the three vertices of each face
        # shape of faces is (M, 3)
        # shape of vertices is (N, 3)
        ptsA = vertices[faces[:, 0]]
        ptsB = vertices[faces[:, 1]]
        ptsC = vertices[faces[:, 2]]
        
        # Compute edge vectors
        v_AB = ptsB - ptsA
        v_BC = ptsC - ptsB
        v_CA = ptsA - ptsC
        
        # Compute edge lengths
        c = np.linalg.norm(v_AB, axis=1)
        a = np.linalg.norm(v_BC, axis=1)
        b = np.linalg.norm(v_CA, axis=1)
        
        # Filter degenerate faces (very small edges or area)
        cross_prod = np.cross(v_AB, -v_CA)
        areas = 0.5 * np.linalg.norm(cross_prod, axis=1)
        
        valid_mask = (areas > 1e-9) & (a > 1e-5) & (b > 1e-5) & (c > 1e-5)
        if not np.any(valid_mask):
            return default_metrics
            
        a, b, c, areas = a[valid_mask], b[valid_mask], c[valid_mask], areas[valid_mask]
        
        # Aspect Ratio = (a * b * c) / (8 * (s-a) * (s-b) * (s-c))
        s = (a + b + c) / 2.0
        denom = 8.0 * (s - a) * (s - b) * (s - c)
        denom = np.where(denom < 1e-12, 1e-12, denom)
        ar = (a * b * c) / denom
        # Clean up any infinities
        ar = np.where(np.isnan(ar) | np.isinf(ar), 99.0, ar)
        
        # Compute angles using Law of Cosines
        # cos A = (b^2 + c^2 - a^2) / (2 * b * c)
        cos_A = np.clip((b**2 + c**2 - a**2) / (2.0 * b * c + 1e-12), -1.0, 1.0)
        cos_B = np.clip((a**2 + c**2 - b**2) / (2.0 * a * c + 1e-12), -1.0, 1.0)
        cos_C = np.clip((a**2 + b**2 - c**2) / (2.0 * a * b + 1e-12), -1.0, 1.0)
        
        angle_A = np.arccos(cos_A) * 180.0 / np.pi
        angle_B = np.arccos(cos_B) * 180.0 / np.pi
        angle_C = np.arccos(cos_C) * 180.0 / np.pi
        
        all_angles = np.column_stack([angle_A, angle_B, angle_C])
        max_angles = np.max(all_angles, axis=1)
        min_angles = np.min(all_angles, axis=1)
        
        # Skewness = max((max_angle - 60) / 120, (60 - min_angle) / 60)
        skewness = np.maximum((max_angles - 60.0) / 120.0, (60.0 - min_angles) / 60.0)
        
        # Jacobian Ratio = 1.0 + 0.1 * (ar - 1.0) as a proxy
        jacobian = 1.0 + 0.1 * (ar - 1.0)
        
        # Flags / Threshold check
        bad_ar = ar > 5.0
        bad_skew = skewness > 0.8
        bad_jac = jacobian > 1.5
        bad_min_ang = min_angles < 20.0
        bad_max_ang = max_angles > 140.0
        
        total_flagged_mask = bad_ar | bad_skew | bad_jac | bad_min_ang | bad_max_ang
        
        flagged_counts = {
            "aspect_ratio": int(np.sum(bad_ar)),
            "skewness": int(np.sum(bad_skew)),
            "jacobian_ratio": int(np.sum(bad_jac)),
            "min_angle": int(np.sum(bad_min_ang)),
            "max_angle": int(np.sum(bad_max_ang)),
            "total_flagged": int(np.sum(total_flagged_mask))
        }
        
        # Quality score = percentage of unflagged elements
        overall_score = float(1.0 - np.sum(total_flagged_mask) / len(areas))
        
        return {
            "aspect_ratio": {
                "mean": float(np.mean(ar)),
                "max": float(np.max(ar)),
                "min": float(np.min(ar))
            },
            "skewness": {
                "mean": float(np.mean(skewness)),
                "max": float(np.max(skewness)),
                "min": float(np.min(skewness))
            },
            "jacobian_ratio": {
                "mean": float(np.mean(jacobian)),
                "max": float(np.max(jacobian)),
                "min": float(np.min(jacobian))
            },
            "angles": {
                "min_angle_mean": float(np.mean(min_angles)),
                "min_angle_min": float(np.min(min_angles)),
                "max_angle_mean": float(np.mean(max_angles)),
                "max_angle_max": float(np.max(max_angles))
            },
            "flagged_counts": flagged_counts,
            "overall_quality_score": overall_score
        }
    except Exception as e:
        # Fallback in case of numpy errors
        return default_metrics
