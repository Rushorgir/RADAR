from __future__ import annotations

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
from src.propagation.current_positions import ObjectPosition, current_positions
from src.propagation.launch_corridor import (
    LAUNCH_SITES,
    AscentWaypoint,
    CorridorConflict,
    LaunchSafetyResult,
    check_launch_corridor_safety,
    generate_ascent_waypoints,
)
from src.propagation.models import (
    BatchPropagationResult,
    PropagatedState,
    PropagationError,
    SGP4ErrorCode,
    TrajectoryResult,
)
from src.propagation.reentry import (
    DescentWaypoint,
    ReentryPrediction,
    ReentryRiskTier,
    classify_perigee_risk,
    estimate_days_to_reentry,
    generate_descent_waypoints,
    predict_reentry_watch,
)
from src.propagation.sgp4_engine import (
    SGP4PropagationFailure,
    SGP4Propagator,
    build_epoch_grid,
    build_jd_fr_grid,
)

__all__ = [
    "DEFAULT_SIGMA_MODELS",
    "LAUNCH_SITES",
    "AscentWaypoint",
    "BatchPropagationResult",
    "CatalogPropagationArrays",
    "CorridorConflict",
    "DescentWaypoint",
    "LaunchSafetyResult",
    "ObjectPosition",
    "PropagatedState",
    "PropagationError",
    "RICSigmaModel",
    "ReentryPrediction",
    "ReentryRiskTier",
    "SGP4ErrorCode",
    "SGP4PropagationFailure",
    "SGP4Propagator",
    "TrajectoryResult",
    "build_epoch_grid",
    "build_jd_fr_grid",
    "check_launch_corridor_safety",
    "classify_perigee_risk",
    "current_positions",
    "estimate_covariance_6x6",
    "estimate_covariance_6x6_batch",
    "estimate_days_to_reentry",
    "generate_ascent_waypoints",
    "generate_descent_waypoints",
    "is_positive_definite",
    "predict_reentry_watch",
    "propagate_catalog",
    "propagate_catalog_arrays",
    "summarize_covariance_health",
]
