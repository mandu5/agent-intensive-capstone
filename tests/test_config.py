"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from config import AppConfig


class TestAppConfig:
    """Test AppConfig class."""

    def test_from_env_success(self):
        """Test successful configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key-123",
                "GEMINI_MODEL": "gemini-1.5-pro",
            },
        ):
            config = AppConfig.from_env()
            assert config.gemini_api_key == "test-key-123"
            assert config.gemini_model == "gemini-1.5-pro"
            assert config.default_max_results == 3
            assert config.memory_limit == 10

    def test_from_env_missing_api_key(self):
        """Test that missing API key raises EnvironmentError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError, match="GEMINI_API_KEY is not set"):
                AppConfig.from_env()

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = AppConfig(
            gemini_api_key="test-key",
            default_max_results=5,
            memory_limit=20,
        )
        assert config.default_max_results == 5
        assert config.memory_limit == 20

        # Invalid: negative max_results
        with pytest.raises(ValueError, match="default_max_results must be at least 1"):
            AppConfig(gemini_api_key="test-key", default_max_results=0)

        # Invalid: negative memory_limit
        with pytest.raises(ValueError, match="memory_limit must be at least 1"):
            AppConfig(gemini_api_key="test-key", memory_limit=0)

        # Invalid: empty API key
        with pytest.raises(ValueError, match="GEMINI_API_KEY is required"):
            AppConfig(gemini_api_key="")

        # Invalid: min_quiz_options < 2
        with pytest.raises(ValueError, match="min_quiz_options must be at least 2"):
            AppConfig(gemini_api_key="test-key", min_quiz_options=1)

        # Invalid: max_quiz_options < min_quiz_options
        with pytest.raises(ValueError, match="max_quiz_options must be >= min_quiz_options"):
            AppConfig(gemini_api_key="test-key", min_quiz_options=5, max_quiz_options=3)

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = AppConfig(gemini_api_key="test-key")
        assert config.gemini_model == "gemini-1.5-flash"
        assert config.default_max_results == 3
        assert config.search_max_retries == 3
        assert config.search_retry_delay == 1.0
        assert config.memory_limit == 10
        assert config.min_quiz_options == 2
        assert config.max_quiz_options == 6
        assert config.max_input_retries == 3

