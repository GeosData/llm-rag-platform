from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "DocuQuery"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://docuquery:docuquery@localhost:5432/docuquery"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_key: str = "sk-change-me"
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "docuquery"

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64

    # RAG
    top_k: int = 5
    max_context_tokens: int = 3000

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100


settings = Settings()
