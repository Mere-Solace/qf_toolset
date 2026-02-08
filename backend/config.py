from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    database_url: str = "sqlite:///data/finance.db"
    fred_api_key: str = ""
    bls_api_key: str = ""
    bea_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
