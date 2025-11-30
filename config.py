"""Configuration management for Smart Study Buddy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    """Application configuration with validation."""

    # API Configuration
    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"

    # Search Configuration
    default_max_results: int = 3
    search_max_retries: int = 3
    search_retry_delay: float = 1.0  # seconds

    # Memory Configuration
    memory_limit: int = 10
    memory_token_limit: Optional[int] = None  # None means no token limit

    # Quiz Configuration
    min_quiz_options: int = 2
    max_quiz_options: int = 6

    # User Input Configuration
    max_input_retries: int = 3

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required")

        if self.default_max_results < 1:
            raise ValueError("default_max_results must be at least 1")

        if self.memory_limit < 1:
            raise ValueError("memory_limit must be at least 1")

        if self.min_quiz_options < 2:
            raise ValueError("min_quiz_options must be at least 2")

        if self.max_quiz_options < self.min_quiz_options:
            raise ValueError("max_quiz_options must be >= min_quiz_options")

        if self.max_input_retries < 1:
            raise ValueError("max_input_retries must be at least 1")

    @classmethod
    def from_env(cls) -> AppConfig:
        """Create configuration from environment variables."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set.\n"
                "Please do one of the following:\n"
                "  1. Create a .env file: cp .env.example .env\n"
                "     Then edit .env and add your API key\n"
                "  2. Export the variable: export GEMINI_API_KEY='your-key'\n"
                "  3. Get your API key from: https://aistudio.google.com/app/apikey"
            )

        return cls(
            gemini_api_key=api_key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            default_max_results=int(os.getenv("DEFAULT_MAX_RESULTS", "3")),
            search_max_retries=int(os.getenv("SEARCH_MAX_RETRIES", "3")),
            search_retry_delay=float(os.getenv("SEARCH_RETRY_DELAY", "1.0")),
            memory_limit=int(os.getenv("MEMORY_LIMIT", "10")),
            min_quiz_options=int(os.getenv("MIN_QUIZ_OPTIONS", "2")),
            max_quiz_options=int(os.getenv("MAX_QUIZ_OPTIONS", "6")),
            max_input_retries=int(os.getenv("MAX_INPUT_RETRIES", "3")),
        )

