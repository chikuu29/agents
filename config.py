# config.py
"""
Central configuration for the agent system.

Loads settings from environment variables and .env file.
Supports all LLM providers, logging levels, and observability config.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # --- LLM Provider Configuration ---
    llm_provider: str = Field(
        default="anthropic",
        description="LLM provider: 'anthropic' | 'openai' | 'gemini' | 'ollama' | 'deepseek'",
    )
    llm_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model name/identifier for the selected provider",
    )
    llm_api_key: str = Field(
        default="",
        description="API key for the LLM provider (not needed for Ollama)",
    )
    llm_base_url: str = Field(
        default="",
        description="Custom base URL (for Ollama, DeepSeek, or proxy endpoints)",
    )
    llm_max_tokens: int = Field(
        default=4096,
        description="Default max tokens for LLM responses",
    )
    llm_temperature: float = Field(
        default=0.7,
        description="Default temperature for LLM responses",
    )

    # --- Reflection LLM (can be a cheaper/different model) ---
    reflection_provider: str = Field(
        default="",
        description="Override LLM provider for reflection. Empty = use main provider",
    )
    reflection_model: str = Field(
        default="",
        description="Override model for reflection. Empty = use main model",
    )

    # --- Logging ---
    log_level: str = Field(default="INFO", description="Log level: DEBUG|INFO|WARNING|ERROR")
    log_format: str = Field(
        default="console",
        description="Log format: 'console' (colored dev) | 'json' (production)",
    )
    log_file: str = Field(default="logs/agent.log", description="Log file path")

    # --- Observability ---
    otlp_endpoint: str = Field(
        default="",
        description="OTLP collector endpoint (e.g. http://localhost:4317). Empty = console only",
    )
    service_name: str = Field(default="agent-system", description="Service name for tracing")

    # --- MCP ---
    mcp_registry_path: str = Field(
        default="config/mcp_registry.json",
        description="Path to MCP server registry JSON",
    )

    # --- Paths ---
    skills_dir: str = Field(default="skills", description="Skills directory path")
    brain_db_path: str = Field(default="brain/episodes.db", description="Episodic memory DB path")
    brain_chroma_path: str = Field(default="brain/chroma", description="Semantic memory path")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "",
        "case_sensitive": False,
        "extra": "ignore",
    }
