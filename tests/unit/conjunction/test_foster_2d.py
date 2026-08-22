"""
Unit tests for Foster's 2D Pc method.
"""

import numpy as np
import pytest

from src.conjunction.probability.foster_2d import foster_2d_pc
from src.shared.constants.physical import PC

def test_foster_2d_degenerate_covariance():
    b_vector = np.array([0.0, 0.0])
    # Singular covariance matrix
    cov_enc = np.array([[1.0, 1.0], [1.0, 1.0]]) 
    
    with pytest.raises(ValueError, match="Degenerate covariance"):
        foster_2d_pc(b_vector, cov_enc, combined_radius_km=0.015)

def test_foster_2d_head_on_zero_miss():
    b_vector = np.array([0.0, 0.0])
    # 1 km^2 variance in both directions
    cov_enc = np.diag([1.0, 1.0]) 
    combined_radius_km = 0.015
    
    pc = foster_2d_pc(b_vector, cov_enc, combined_radius_km)
    
    # Since b=0, the integral of 1/(2*pi*sigma^2) * exp(- (x^2+y^2)/(2*sigma^2))
    # over a small circle is approx Area * PDF(0,0)
    # Area = pi * R^2 = pi * (0.015)^2
    # PDF(0,0) = 1 / (2 * pi * 1.0)
    # pc approx (pi * 0.015^2) / (2 * pi) = (0.015^2) / 2 = 0.0001125
    assert pc == pytest.approx(0.0001125, rel=1e-2)

def test_foster_2d_large_miss():
    # Miss distance is 10 km, standard deviation is 1 km
    # It's a 10 sigma event. Pc should be essentially 0.
    b_vector = np.array([10.0, 0.0])
    cov_enc = np.diag([1.0, 1.0])
    combined_radius_km = 0.015
    
    pc = foster_2d_pc(b_vector, cov_enc, combined_radius_km)
    assert pc < 1e-15
