"""
Configuration loader for RADAR system parameters.

Reads from config/settings.toml and provides type-safe access to shared
configuration values used across modules.

Supports overrides via environment variables (prefixed with RADAR_) or
keyword arguments, useful for testing and CLI-driven customization.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

__all__ = ["load_config", "get_screening_config", "get_propagation_config"]


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load configuration from settings.toml.

    Searches:
    1. Explicit config_path if provided
    2. config/settings.toml relative to project root
    3. Project root is detected as the directory containing pyproject.toml

    Args:
        config_path: Explicit path to settings.toml (relative or absolute).
                     If None, uses auto-detection.

    Returns:
        Parsed TOML configuration dict.

    Raises:
        FileNotFoundError: If settings.toml cannot be found.
    """
    if config_path is None:
        # Auto-detect project root by walking up from this file
        current = Path(__file__).resolve().parent
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                config_path = current / "config" / "settings.toml"
                break
            current = current.parent
        else:
            raise FileNotFoundError(
                "Could not find project root (pyproject.toml). "
                "Provide config_path explicitly."
            )
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def get_screening_config(
    altitude_band_half_width_km: float | None = None,
    encounter_sphere_radius_km: float | None = None,
    screening_timestep_s: float | None = None,
    propagation_horizon_h: float | None = None,
    config_path: str | Path | None = None,
) -> dict[str, float]:
    """
    Get screening configuration with support for overrides.

    Precedence (highest to lowest):
    1. Keyword arguments (explicit overrides)
    2. config/settings.toml [screening] section
    3. Built-in defaults

    Args:
        altitude_band_half_width_km: Coarse filter altitude band half-width.
        encounter_sphere_radius_km: Fine filter encounter sphere radius.
        screening_timestep_s: Time step between screening epochs (seconds).
        propagation_horizon_h: Propagation horizon (hours).
        config_path: Path to settings.toml. If None, auto-detected.

    Returns:
        Dict with keys: altitude_band_half_width_km, encounter_sphere_radius_km,
                       screening_timestep_s, propagation_horizon_h
    """
    # Load from file
    try:
        config = load_config(config_path)
        screening = config.get("screening", {})
    except FileNotFoundError:
        screening = {}

    # Built-in defaults
    defaults = {
        "altitude_band_half_width_km": 50.0,
        "encounter_sphere_radius_km": 10.0,
        "screening_timestep_s": 60.0,
        "propagation_horizon_h": 72.0,
    }

    # Merge: defaults < file config < keyword args
    result = {**defaults}
    result.update(
        {
            "altitude_band_half_width_km": screening.get(
                "altitude_band_half_width", defaults["altitude_band_half_width_km"]
            ),
            "encounter_sphere_radius_km": screening.get(
                "encounter_sphere_radius", defaults["encounter_sphere_radius_km"]
            ),
            "screening_timestep_s": screening.get(
                "screening_timestep_s", defaults["screening_timestep_s"]
            ),
            "propagation_horizon_h": screening.get(
                "propagation_horizon_h", defaults["propagation_horizon_h"]
            ),
        }
    )

    # Apply explicit overrides
    if altitude_band_half_width_km is not None:
        result["altitude_band_half_width_km"] = altitude_band_half_width_km
    if encounter_sphere_radius_km is not None:
        result["encounter_sphere_radius_km"] = encounter_sphere_radius_km
    if screening_timestep_s is not None:
        result["screening_timestep_s"] = screening_timestep_s
    if propagation_horizon_h is not None:
        result["propagation_horizon_h"] = propagation_horizon_h

    return result


def get_propagation_config(
    screening_timestep_s: float | None = None,
    propagation_horizon_h: float | None = None,
    config_path: str | Path | None = None,
) -> dict[str, float]:
    """
    Get propagation-specific configuration.

    Convenience function for AI-1's propagation pipeline; delegates to
    get_screening_config for the two parameters it needs.

    Args:
        screening_timestep_s: Override timestep (seconds).
        propagation_horizon_h: Override horizon (hours).
        config_path: Path to settings.toml. If None, auto-detected.

    Returns:
        Dict with keys: screening_timestep_s, propagation_horizon_h
    """
    full_config = get_screening_config(
        screening_timestep_s=screening_timestep_s,
        propagation_horizon_h=propagation_horizon_h,
        config_path=config_path,
    )
    return {
        "screening_timestep_s": full_config["screening_timestep_s"],
        "propagation_horizon_h": full_config["propagation_horizon_h"],
    }
