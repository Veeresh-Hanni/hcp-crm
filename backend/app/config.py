from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central app config. All values are overridable via a .env file
    (see .env.example) or real environment variables.
    """

    database_url: str = "postgresql+psycopg2://postgres:psqlpass@localhost:5432/hcp_crm"

    groq_api_key: str = ""
    groq_fast_model: str = "gemma2-9b-it"          # router + extraction calls
    groq_reasoning_model: str = "llama-3.3-70b-versatile"  # deeper reasoning calls

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
