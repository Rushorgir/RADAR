"""SGP4/SDP4 orbit propagation: single-object engine, covariance estimation, batch orchestration."""

from src.propagation.batch_arrays import CatalogPropagationArrays, propagate_catalog_arrays
from src.propagation.batch_propagator import propagate_catalog, summarize_covariance_health
from src.propagation.covariance import (
    DEFAULT_SIGMA_MODELS,
    RICSigmaModel,
    estimate_covariance_6x6,
    estimate_covariance_6x6_batch,
    is_positive_definite,
)
from src.propagation.models import BatchPropagationResult, PropagatedState, PropagationError, SGP4ErrorCode, TrajectoryResult
from src.propagation.sgp4_engine import SGP4Propagator, SGP4PropagationFailure, build_epoch_grid, build_jd_fr_grid

__all__ = [
    "propagate_catalog",
    "propagate_catalog_arrays",
    "CatalogPropagationArrays",
    "summarize_covariance_health",
    "DEFAULT_SIGMA_MODELS",
    "RICSigmaModel",
    "estimate_covariance_6x6",
    "estimate_covariance_6x6_batch",
    "is_positive_definite",
    "BatchPropagationResult",
    "PropagatedState",
    "PropagationError",
    "SGP4ErrorCode",
    "TrajectoryResult",
    "SGP4Propagator",
    "SGP4PropagationFailure",
    "build_epoch_grid",
    "build_jd_fr_grid",
]
