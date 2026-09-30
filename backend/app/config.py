import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- TypeSafe / Jev ---
    typesafe_api_key: str = ""
    jev_model: str = "jev-1.13.0"
    jev_input_price_per_million: float = 0.042

    # --- LLM Baseline ---
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"

    # --- LLM Pricing ---
    llm_input_price_per_million: float = 0.59
    llm_output_price_per_million: float = 0.79

    # --- Application ---
    cors_origins: Union[str, List[str]] = "http://localhost:5173"
    log_level: str = "info"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.cors_origins, list):
            return self.cors_origins
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()
