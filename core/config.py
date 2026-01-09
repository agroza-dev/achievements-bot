import os
from dataclasses import field
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).resolve().parent.parent


class Application(BaseModel):
    debug: bool = False

class BotConfig(BaseModel):
    token: str = ''
    persistence: str = os.path.join(BASE_DIR, "var/db/persistence.pkl")
    callback_data_max_len: int = 64 # Максимальная длинна json который можно пихать в callback кнопки
    builder: dict[str, float] = field(default_factory=lambda: {
        'connect': 3.0,
        'read': 10.0,
        'write': 10.0,
        'pool': 2.0,
    })


class DatabaseConfig(BaseModel):
    host: str = 'localhost'
    port: int = 5432
    name: str = 'achievements'
    login: str = ''
    password: str = ''
    pool_min_size: int = 1
    pool_max_size: int = 10
    ssl_mode: str = 'prefer'  # Options: disable, allow, prefer, require, verify-ca, verify-full


class LoggerConfig(BaseModel):
    path: str = os.path.join(BASE_DIR, "var/log")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(os.path.join(BASE_DIR, ".env"), os.path.join(BASE_DIR, ".env.dev")),
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__"
    )
    app: Application = Application()
    bot: BotConfig = BotConfig()
    logs: LoggerConfig = LoggerConfig()
    db: DatabaseConfig = DatabaseConfig()


settings = Settings()
