"""
Unit tests for the Stage 2 fine filter (k-d tree spatial proximity).
"""

import numpy as np
import pytest

from src.conjunction.screening.fine_filter import fine_filter_at_epoch
from src.shared.constants.physical import SCREENING

def test_fine_filter_at_epoch_no_pairs():
    positions = np.array([
        [0.0, 0.0, 0.0],
        [100.0, 0.0, 0.0],
        [0.0, 100.0, 0.0]
    ])
    object_ids = ["A", "B", "C"]
    
    pairs = fine_filter_at_epoch(positions, object_ids, threshold_km=10.0)
    assert len(pairs) == 0

def test_fine_filter_at_epoch_with_pairs():
    positions = np.array([
        [0.0, 0.0, 0.0],
        [5.0, 0.0, 0.0],  # Within 10km of A
        [15.0, 0.0, 0.0]  # Outside 10km of A, but 10km exactly from B
    ])
    object_ids = ["A", "B", "C"]
    
    pairs = fine_filter_at_epoch(positions, object_ids, threshold_km=10.0)
    # A-B is 5km. B-C is 10km. A-C is 15km.
    assert len(pairs) == 2
    
    # Check results
    pairs_set = {(p[0], p[1]) for p in pairs}
    assert ("A", "B") in pairs_set
    assert ("B", "C") in pairs_set
    
    # Check distance
    for id1, id2, dist in pairs:
        if id1 == "A" and id2 == "B":
            assert dist == pytest.approx(5.0)
        elif id1 == "B" and id2 == "C":
            assert dist == pytest.approx(10.0)

def test_fine_filter_empty():
    positions = np.array([])
    object_ids = []
    pairs = fine_filter_at_epoch(positions, object_ids)
    assert len(pairs) == 0
