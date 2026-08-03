from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    storage_endpoint_url: str = "http://localhost:9000"
    storage_bucket: str = "ats-tracker"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_region: str = "us-east-1"

    ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openrouter_api_key: str = ""
    openrouter_model: str = ""

    # Local sentence-transformers embeddings for deterministic JD<->resume semantic
    # scoring. Off by default; when enabled it replaces the LLM's numeric match
    # guess with an embedding cosine similarity (the LLM still writes the narrative).
    embeddings_enabled: bool = False
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Persisted so the model downloads once and survives container recreation.
    embeddings_cache_dir: str = "/app/.model_cache"

    # Weight of the skill/requirement fit vs. the holistic semantic understanding
    # in the overall AI match score. Lower it to reward strong generalists whose
    # résumé fits the role even when they miss niche must-have tags. Range 0-1.
    evaluation_skill_weight: float = 0.6

    cors_origins: str = "http://localhost:3000"

    default_org_name: str = "Peer Consulting Resources Inc."
    default_org_slug: str = "peer-consulting"
    default_super_admin_email: str = "admin@ats-tracker.local"
    default_super_admin_password: str = "change-me"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
