from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./traces.db"
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
