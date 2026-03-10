import os
from dataclasses import field
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).resolve().parent.parent

class ProjectPaths:
    """
    Пути к директориям и файлам проекта.

    Все пути формируются относительно BASE_DIR.
    """
    # Корневая директория var/
    VAR_DIR: Path = BASE_DIR / "var"

    # Директории
    LOGS_DIR: Path = VAR_DIR / "log"
    SCHEDULER_DIR: Path = VAR_DIR / "scheduler"
    DB_DIR: Path = VAR_DIR / "db"

    # Файлы
    SCHEDULER_STATE_FILE: Path = SCHEDULER_DIR / "scheduler_state.json"
    BOT_PERSISTENCE_FILE: Path = DB_DIR / "persistence.pkl" #TODO: deprecated

    @classmethod
    def ensure_dirs(cls) -> None:
        """Создать все необходимые директории."""
        cls.VAR_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCHEDULER_DIR.mkdir(parents=True, exist_ok=True)
        cls.DB_DIR.mkdir(parents=True, exist_ok=True)


class Application(BaseModel):
    debug: bool = False

class BotConfig(BaseModel):
    token: str = ''
    persistence: str = str(ProjectPaths.BOT_PERSISTENCE_FILE)
    callback_data_max_len: int = 64  # Максимальная длинна json который можно пихать в callback кнопки
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
    path: str = str(ProjectPaths.LOGS_DIR)


class SchedulerConfig(BaseModel):
    """
    Конфигурация планировщика задач.

    Атрибуты:
        state_file: Путь к файлу состояния планировщика
        quiet: Тихий режим (минимум логов)
        max_retries: Максимальное количество попыток выполнения задачи
    """
    state_file: str = str(ProjectPaths.SCHEDULER_STATE_FILE)
    quiet: bool = True
    max_retries: int = 3


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
    scheduler: SchedulerConfig = SchedulerConfig()


settings = Settings()


class PeriodicAwardConfig:
    """
    Конфигурация периодических зачислений.

    Единое расписание для всех чатов.
    Зачисления происходят раз в неделю в указанное время.

    Атрибуты:
        DEFAULT_AMOUNT: Базовая сумма зачисления (очков)
        TIMEZONE: Часовой пояс для выполнения
        CRON_EXPRESSION: Cron-выражение для запуска producer
                         Формат: "минута час день месяц день_недели"
                         По умолчанию: пятница 18:00
    """

    # Базовая сумма зачисления для всех чатов
    DEFAULT_AMOUNT: int = 50

    # Часовой пояс для выполнения зачислений
    TIMEZONE: str = "Europe/Moscow"

    # Cron-выражение для запуска producer (создания batch)
    # Пятница, 18:00 (окно зачисления 18:00-19:00)
    CRON_EXPRESSION: str = "00 22 * * 2"

    # Размер батча для обработки за один проход worker
    BATCH_SIZE: int = 50

    # Интервал проверки worker (секунды)
    WORKER_POLL_INTERVAL: int = 30


# Глобальный экземпляр конфигурации
periodic_award_config = PeriodicAwardConfig()
