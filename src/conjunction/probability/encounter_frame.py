"""
Encounter Frame Transformations

Calculates the rotation matrix from ECI to the encounter plane (B-plane) and projects covariance matrices.
"""

from typing import Tuple
import numpy as np


def compute_encounter_frame(
    r_rel: np.ndarray,
    v_rel: np.ndarray,
) -> np.ndarray:
    """
    Compute the 3x3 rotation matrix from ECI to the encounter frame.
    
    The encounter frame is defined by:
    - w: Along relative velocity
    - n: Normal to the orbital plane (v_rel x r_rel)
    - t: Tangential (n x w)
    
    Args:
        r_rel: Relative position vector (3,) in km.
        v_rel: Relative velocity vector (3,) in km/s.
        
    Returns:
        3x3 rotation matrix where rows are [e_t, e_n, e_w].
    """
    v_norm = np.linalg.norm(v_rel)
    if v_norm == 0:
        raise ValueError("Relative velocity is zero. Cannot define encounter frame.")
        
    e_w = v_rel / v_norm
    
    cross_product = np.cross(v_rel, r_rel)
    cross_norm = np.linalg.norm(cross_product)
    
    if cross_norm == 0:
        # Collinear relative position and velocity. Pick arbitrary orthogonal vector.
        # This is extremely rare in practice.
        if abs(e_w[0]) < 0.9:
            arbitrary = np.array([1.0, 0.0, 0.0])
        else:
            arbitrary = np.array([0.0, 1.0, 0.0])
        e_n = np.cross(e_w, arbitrary)
        e_n /= np.linalg.norm(e_n)
    else:
        e_n = cross_product / cross_norm
        
    e_t = np.cross(e_n, e_w)
    
    # Return matrix where each row is a basis vector of the new frame
    return np.vstack([e_t, e_n, e_w])


def project_to_encounter_plane(
    r_rel: np.ndarray,
    cov_pos_combined: np.ndarray,
    rotation: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Project relative position and combined covariance to the 2D encounter plane (B-plane).
    
    Args:
        r_rel: Relative position vector in ECI (3,) km.
        cov_pos_combined: Combined position covariance in ECI (3, 3) km^2.
        rotation: 3x3 rotation matrix from ECI to encounter frame.
        
    Returns:
        Tuple of (b_vector (2,), cov_enc (2, 2))
    """
    # Project position to the new frame
    r_enc = rotation @ r_rel
    
    # The miss vector is the first two components (tangential and normal)
    # The w-component (along velocity) should be approximately 0 at TCA
    b_vector = r_enc[:2]
    
    # Projection matrix P (2x3) extracts the first two components
    P = rotation[:2, :]
    
    # Project covariance
    cov_enc = P @ cov_pos_combined @ P.T
    
    return b_vector, cov_enc
