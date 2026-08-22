"""
Unit tests for the encounter frame coordinate transformation.
"""

import numpy as np
import pytest

from src.conjunction.probability.encounter_frame import compute_encounter_frame, project_to_encounter_plane


def test_compute_encounter_frame_orthonormal():
    r_rel = np.array([10.0, 0.0, 0.0])
    v_rel = np.array([0.0, 14.0, 0.0])
    
    rotation = compute_encounter_frame(r_rel, v_rel)
    
    # Check shape
    assert rotation.shape == (3, 3)
    
    # Check orthonormality (R * R^T = I)
    identity = rotation @ rotation.T
    np.testing.assert_allclose(identity, np.eye(3), atol=1e-10)
    
    # Check specific axes
    # v_rel is along +y. So e_w is [0, 1, 0]
    np.testing.assert_allclose(rotation[2], [0.0, 1.0, 0.0], atol=1e-10)
    
    # e_n is v_rel x r_rel / norm
    # v_rel x r_rel = [0, 14, 0] x [10, 0, 0] = [0, 0, -140]
    # e_n should be [0, 0, -1]
    np.testing.assert_allclose(rotation[1], [0.0, 0.0, -1.0], atol=1e-10)
    
    # e_t is e_n x e_w = [0, 0, -1] x [0, 1, 0] = [1, 0, 0]
    np.testing.assert_allclose(rotation[0], [1.0, 0.0, 0.0], atol=1e-10)


def test_project_to_encounter_plane():
    r_rel = np.array([10.0, 0.0, 0.0])
    v_rel = np.array([0.0, 14.0, 0.0])
    
    # Combined covariance: mostly uncertain in X and Z
    cov_pos_combined = np.diag([100.0, 1.0, 400.0])
    
    rotation = compute_encounter_frame(r_rel, v_rel)
    b_vector, cov_enc = project_to_encounter_plane(r_rel, cov_pos_combined, rotation)
    
    # b_vector should have the lengths along e_t and e_n
    # e_t is along X ([1, 0, 0]), e_n is along -Z ([0, 0, -1])
    # r_rel is [10, 0, 0], so projection along e_t is 10, along e_n is 0
    assert b_vector.shape == (2,)
    np.testing.assert_allclose(b_vector, [10.0, 0.0], atol=1e-10)
    
    # covariance projection
    # X variance (100) maps to e_t
    # Z variance (400) maps to e_n
    assert cov_enc.shape == (2, 2)
    np.testing.assert_allclose(cov_enc, [[100.0, 0.0], [0.0, 400.0]], atol=1e-10)
