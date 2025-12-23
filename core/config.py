import os
from dataclasses import field
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).resolve().parent.parent


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



class LoggerConfig(BaseModel):
    path: str = os.path.join(BASE_DIR, "var/log")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(os.path.join(BASE_DIR, ".env"), os.path.join(BASE_DIR, ".env.dev")),
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__"
    )
    bot: BotConfig = BotConfig()
    logs: LoggerConfig = LoggerConfig()


settings = Settings()
