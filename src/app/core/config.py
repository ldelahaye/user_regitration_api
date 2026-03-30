from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "User Registration API"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/registration"
    database_min_pool_size: int = 2
    database_max_pool_size: int = 10

    model_config = {"env_prefix": "APP_", "env_file": ".env"}


settings = Settings()
