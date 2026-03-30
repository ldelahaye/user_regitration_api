from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "User Registration API"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/registration"

    model_config = {"env_prefix": "APP_", "env_file": ".env"}


settings = Settings()
