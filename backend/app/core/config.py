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

    # "s3" talks to S3 or anything S3-compatible (MinIO locally) using the
    # access/secret pair below. "gcs" talks to Google Cloud Storage as whatever
    # service account the process is already running as, so there is no key to
    # configure, leak or rotate -- the right choice on Cloud Run, where the
    # container has an identity of its own.
    storage_backend: str = "s3"
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

    # Public URL of the frontend. Used to build the links inside outbound email
    # (password reset, invitations), so it must be what recipients can reach —
    # not localhost — in any deployed environment.
    app_base_url: str = "http://localhost:3000"

    # SMTP delivery. Works with any provider that speaks SMTP (SES, SendGrid,
    # Mailgun, Postmark, Google Workspace). Leave smtp_host empty to disable
    # sending entirely: mail is then logged and recorded but never transmitted.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    # STARTTLS on the standard submission port. Set smtp_use_ssl instead for
    # implicit TLS on port 465; the two are mutually exclusive.
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 15
    mail_from_email: str = "no-reply@ats-tracker.local"
    mail_from_name: str = "ATS Tracker"

    # Escape hatch for when no mailer is configured: returns the raw reset token
    # straight from /auth/forgot-password so the flow stays testable. It leaks
    # account existence and hands out a working credential-reset token, so it is
    # refused outright when app_env is production, regardless of this flag.
    expose_password_reset_token: bool = False

    # Interactive API docs (/docs, /redoc, /openapi.json). Off in production
    # because they publish every endpoint and schema to unauthenticated callers.
    expose_api_docs: bool = False

    # Error tracking. Empty by default — sentry_sdk.init is simply never
    # called, so this costs nothing when unset. Point it at a Sentry DSN (or
    # any Sentry-compatible ingest, e.g. self-hosted GlitchTip) to get
    # unhandled exceptions and their request context automatically.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0

    default_org_name: str = "Peer Consulting Resources Inc."
    default_org_slug: str = "peer-consulting"
    default_super_admin_email: str = "admin@ats-tracker.local"
    default_super_admin_password: str = "change-me"

    # Break-glass recovery. The seed script only ever *creates* the Super Admin,
    # so an account left over from an earlier deploy keeps whatever password it
    # was created with — and on a managed runtime like Cloud Run there is no
    # shell to go and fix that from. Setting this to true makes the next seed
    # run reset the Super Admin's password to default_super_admin_password and
    # reactivate the account. Turn it off again once you are back in: while it
    # is true, every container start resets that password.
    force_super_admin_password_reset: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def mail_enabled(self) -> bool:
        """Whether outbound email can actually be transmitted."""
        return bool(self.smtp_host)


@lru_cache
def get_settings() -> Settings:
    return Settings()
