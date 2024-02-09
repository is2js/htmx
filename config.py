from platform import system
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    app_name: str
    base_dir: Path = Path(__file__).parent
    local_mode: bool = (
        True if system().lower().startswith("darwin") or system().lower().startswith("windows") else False
    )

    jwt_algorithm: str = "HS256"
    jwt_secret_key: str
    access_token_expire_minutes: int = 60 * 24 * 1  # one day
    refresh_token_expire_minutes: int = 60 * 24 * 60  # sixty day

    aws_bucket_name: str
    aws_region: str
    aws_access_key_id: str
    aws_secret_access_key: str


settings = Settings()
