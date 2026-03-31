from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "User Registration API"
    debug: bool = False

    database_url: SecretStr = SecretStr("postgresql://postgres:postgres@localhost:5432/registration")
    database_min_pool_size: int = 2
    database_max_pool_size: int = 10

    email_mock: bool = True
    email_api_url: str = "http://localhost:8025/api/v1/send"
    email_api_key: SecretStr = SecretStr("")
    email_from: str = "noreply@registration.local"

    activation_code_ttl_minutes: int = 1
    activation_max_attempts: int = 5
    bcrypt_rounds: int = 12
    hmac_secret: SecretStr = SecretStr("change-me-in-production")

    password_min_length: int = 12
    password_max_length: int = 128
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True

    model_config = {"env_prefix": "APP_", "env_file": ".env"}


settings = Settings()
