"""
Unit tests for the shared configuration loader.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.shared.config import get_propagation_config, get_screening_config, load_config


class TestConfigLoader:
    """Test configuration file loading and merging."""

    def test_load_config_with_valid_file(self, tmp_path: Path) -> None:
        """Test loading a valid TOML config file."""
        config_file = tmp_path / "settings.toml"
        config_file.write_text(
            """
[screening]
screening_timestep_s = 30.0
propagation_horizon_h = 48.0
altitude_band_half_width = 100.0
encounter_sphere_radius = 5.0
"""
        )
        config = load_config(config_file)
        assert config["screening"]["screening_timestep_s"] == 30.0
        assert config["screening"]["propagation_horizon_h"] == 48.0

    def test_load_config_missing_file(self, tmp_path: Path) -> None:
        """Test loading a nonexistent config file raises FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent.toml"
        with pytest.raises(FileNotFoundError):
            load_config(nonexistent)

    def test_get_screening_config_defaults(self) -> None:
        """Test that defaults are returned when config file is missing."""
        # When the config file doesn't exist, defaults should be returned
        config = get_screening_config(config_path="/nonexistent/path.toml")
        assert config["screening_timestep_s"] == 60.0
        assert config["propagation_horizon_h"] == 72.0
        assert config["altitude_band_half_width_km"] == 50.0
        assert config["encounter_sphere_radius_km"] == 10.0

    def test_get_screening_config_with_overrides(self) -> None:
        """Test that keyword arguments override defaults."""
        config = get_screening_config(
            screening_timestep_s=90.0,
            propagation_horizon_h=48.0,
            config_path="/nonexistent/path.toml",
        )
        assert config["screening_timestep_s"] == 90.0
        assert config["propagation_horizon_h"] == 48.0
        # Other values should use defaults
        assert config["altitude_band_half_width_km"] == 50.0

    def test_get_propagation_config(self) -> None:
        """Test the convenience function for propagation config."""
        config = get_propagation_config(
            screening_timestep_s=120.0,
            propagation_horizon_h=36.0,
            config_path="/nonexistent/path.toml",
        )
        assert "screening_timestep_s" in config
        assert "propagation_horizon_h" in config
        assert config["screening_timestep_s"] == 120.0
        assert config["propagation_horizon_h"] == 36.0
        # Should NOT have screening-specific fields
        assert "altitude_band_half_width_km" not in config

    def test_get_screening_config_cli_overrides_file(self, tmp_path: Path) -> None:
        """Test that CLI overrides take precedence over config file values."""
        config_file = tmp_path / "settings.toml"
        config_file.write_text(
            """
[screening]
screening_timestep_s = 30.0
propagation_horizon_h = 48.0
"""
        )
        # File has 30.0, but we override to 120.0
        config = get_screening_config(
            screening_timestep_s=120.0,
            config_path=config_file,
        )
        assert config["screening_timestep_s"] == 120.0
        # propagation_horizon_h comes from file (no override)
        assert config["propagation_horizon_h"] == 48.0
