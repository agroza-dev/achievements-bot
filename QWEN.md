# Telegram Bot для группы (old-hustler-bot)

## Обзор проекта

Telegram-бот для взаимодействия с пользователями в группах. Бот отслеживает сообщения, реакции, управляет очками пользователей и предоставляет статистику.

### Архитектура

Проект использует **Clean Architecture** с разделением на слои:

```
├── bot/              # Telegram bot layer (handlers, keyboards, renders)
├── core/
│   ├── domain/       # Business logic (policies, entities)
│   ├── application/  # Use cases
│   ├── infrastructure/ # DB, external services
│   ├── models/       # SQLAlchemy table definitions
│   ├── dto/          # Data Transfer Objects
│   ├── ports/        # Interfaces
│   └── container.py  # Dependency Injection Container
├── tests/            # Unit и integration тесты
├── alembic/          # Database migrations
└── utils/            # Утилиты (logger, trace_logger)
```

### Технологии

- **Python 3.14+**
- **python-telegram-bot v22+** — PTB framework
- **SQLAlchemy 2.0+** — ORM
- **Alembic** — миграции БД
- **PostgreSQL** — база данных (asyncpg)
- **Pydantic Settings** — конфигурация
- **DI Container** — кастомная dependency injection
- **uv** — менеджер пакетов

## Установка и запуск

### Требования

- Python 3.14+
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- PostgreSQL

### Установка зависимостей

```bash
uv sync
```

### Настройка окружения

1. Создать файл `.env` на основе `.env.template`:

```bash
cp .env.template .env
```

2. Заполнить переменные окружения:

```env
APP_CONFIG__BOT__TOKEN=your_bot_token
APP_CONFIG__DB__LOGIN=db_user
APP_CONFIG__DB__PASSWORD=db_password
APP_CONFIG__DB__NAME=db_name
APP_CONFIG__DB__HOST=localhost  # опционально
APP_CONFIG__DB__PORT=5432       # опционально
```

### Запуск бота

```bash
python -m bot.main
```

### Миграции базы данных

```bash
# Применить все миграции
make migrate

# Проверить наличие новых миграций
make check-migrations
```

### Тесты

```bash
uv run pytest
```

### Линтинг (Ruff)

```bash
ruff check . --fix
```

## Структура кода

### Обработчики сообщений (`bot/handlers/`)

| Handler | Описание |
|---------|----------|
| `start_handler.py` | Команда `/start` |
| `personal_stats_handler.py` | Команда `/stats` и callback |
| `reaction_handler.py` | Обработка реакций на сообщения |
| `transfer_handler.py` | Перевод очков между пользователями |
| `bot_membership_handler.py` | События добавления бота в чат |
| `ensure_context_handler.py` | Middleware: гарантирует контекст (user, chat) |
| `message_metadata_handler.py` | Сохранение метаданных сообщений |
| `error_handler.py` | Глобальная обработка ошибок |

### Domain слой (`core/domain/`)

Бизнес-логика реализована через **Policy Pattern**:

- `ChatMessagePolicy` / `DefaultChatMessagePolicy` — правила обработки сообщений
- `ReactionPolicy` / `DefaultReactionPolicy` — правила обработки реакций
- `TransferPolicy` / `DefaultTransferPolicy` — правила переводов очков

### Application слой (`core/application/`)

Use cases (CQRS-style):

- `EnsureContextUseCase` — обеспечение существования user/chat/chat_user
- `ProcessChatMessageUseCase` — обработка входящих сообщений
- `ProcessReactionUseCase` — обработка реакций
- `TransferPointsUseCase` — перевод очков
- `GetPersonalStatsUseCase` — получение статистики пользователя
- `GetChatLeaderboardUseCase` — таблица лидеров чата

### Infrastructure слой (`core/infrastructure/`)

- `DatabaseManager` — управление пулом подключений asyncpg
- `DbUnitOfWork` — паттерн Unit of Work для транзакций
- Репозитории: `UserRepo`, `RatingLedgerRepo`, `RateLimiter`

### Модели данных (`core/models/`)

| Модель | Описание |
|--------|----------|
| `users` | Пользователи Telegram |
| `chats` | Чаты/группы |
| `chat_users` | Связь пользователей с чатами |
| `chat_messages` | Сообщения в чатах |
| `reactions` | Реакции на сообщения |
| `rating_ledger` | История изменений рейтинга (ledger) |

## Dependency Injection

DI Container реализован в `core/container.py`:

```python
# В handlers/getter
container: Container = context.application.bot_data['container']
use_case = container.get_process_message_use_case()
await use_case.execute(...)
```

## Конфигурация

`core/config.py` использует Pydantic Settings:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
    )
    app: Application
    bot: BotConfig
    db: DatabaseConfig
    logs: LoggerConfig
```

## Разработка

### Добавление нового обработчика

1. Создать handler в `bot/handlers/`
2. Зарегистрировать в `bot/main.py`
3. При необходимости создать Use Case в `core/application/`

### Добавление миграции

```bash
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

### Тестирование

- **Unit тесты**: `tests/unit/` — тестирование domain/application логики
- **Integration тесты**: `tests/application/` — тестирование с БД
- **Fake репозитории**: `tests/fakes/` — моки для изоляции тестов

## Текущие задачи и roadmap

### ✅ Выполнено

| Задача | Решение |
|--------|---------|
| Foreign key с CASCADE для reactions | Миграция `671cabe9ec56_003_add_foreign_keys_to_reactions.py` |
| Pickle → JSON/БД (persistence) | PostgreSQLPersistence в `core/infrastructure/repositories/` |
| BotGateway абстракция | Интерфейс + Production/Fake реализации |
| Интеграционные тесты | testcontainers + PostgreSQL |

### 🚧 В работе / Планируется

#### 1. Группы участников
**Идея:** Добавить возможность делить участников чата на группы для удобного управления и упоминания.

**Функционал:**
- [ ] Создание группы командой вида `Создай группу <название>` (например, "Создай группу Собакены")
- [ ] Бот запрашивает, кого добавить в группу (список пользователей или выбор через UI)
- [ ] Управление группами (добавление/удаление участников, переименование, удаление группы)
- [ ] Упоминание группы командой вида "Позови <название_группы>" — бот тегирует всех участников

**Файлы:**
- `core/models/user_groups.py` (новая модель: группы и связи с пользователями)
- `bot/handlers/user_groups_handler.py` (новый хендлер для команд)
- `core/application/create_user_group_use_case.py` (и другие use cases)
- `alembic/versions/` (миграция для таблиц групп)

#### 2. Redis rate limiter
- Заменить in-memory rate limiter на Redis-based для production
- Файл: `core/infrastructure/repositories/rate_limiter.py`

#### 2. Уведомления о трансферах
**Проблема:** Сообщения о трансферах приходят с уведомлением, что может мешать.

**Задачи:**
- [ ] Сделать сообщения информативными (сумма, от/кому, баланс, ошибка)
- [ ] Отправлять без уведомления (`disable_notification=True`)
- [ ] Добавить настройку отключения уведомлений (`/settings`)

**Файлы:**
- `bot/handlers/transfer_handler.py`
- `core/models/user_model.py` (поле `notifications_enabled`)
- `bot/handlers/settings_handler.py` (новый)

#### 3. Observability
**Проблема:** Недостаточно мониторинга за работой бота в production.

**Направления:**
- [ ] **Логирование:** JSON format, correlation ID, контекстное логирование
- [ ] **Метрики:** Prometheus client, `/metrics` endpoint, Grafana dashboards
- [ ] **Трейсинг:** OpenTelemetry, экспорт в Jaeger/Tempo
- [ ] **Алертинг:** мониторинг доступности, алерты на ошибки и ресурсы

**Файлы:**
- `core/infrastructure/observability/` (новая директория)
- `bot/main.py` (инициализация)

**Зависимости:**
- `prometheus-client`, `opentelemetry-*`, `python-json-logger`

#### 4. Обработка события left_chat_member
**Проблема:** При удалении бота или пользователя из чата необходимо корректно деактивировать чат и сохранять метаданные.

**Задачи:**
- [ ] Добавить обработчик события `left_chat_member`
- [ ] При удалении бота из чата — помечать чат как неактивный (`is_active=False`)
- [ ] При удалении пользователя — обновлять статус `chat_user`
- [ ] Сохранять в `meta` данные о чате, из которого удалили бота/пользователя:
  - `chat_id`, `title`, `username`, `member_count`
  - `left_user_id`, `left_user_name`
  - `left_at` (timestamp)
  - `reason` (bot_removed / user_removed / user_left)

**Файлы:**
- `bot/handlers/left_chat_member_handler.py` (новый)
- `core/models/chat_model.py` (добавить поле `meta` для хранения JSON-данных)
- `core/application/deactivate_chat_use_case.py` (новый use case)

## BotGateway абстракция

Реализована абстракция над Telegram Bot API для тестируемости и эмуляции действий пользователей.

### Архитектура

```
core/ports/bot_gateway.py          # Интерфейс BotGateway
core/infrastructure/bot/
    ├── production_bot_gateway.py  # Production реализация (обёртка над telegram.Bot)
    └── fake_bot_gateway.py        # Fake реализация для тестов и load testing
```

### Интерфейс BotGateway

```python
class BotGateway(ABC):
    async def send_message(self, chat_id: int, text: str, **kwargs) -> dict
    async def set_message_reaction(self, chat_id: int, message_id: int, reaction: str | list, **kwargs) -> bool
    async def get_chat(self, chat_id: int) -> dict
    async def get_chat_member(self, chat_id: int, user_id: int) -> dict
    async def answer_callback_query(self, callback_query_id: str, text: str | None, **kwargs) -> bool
```

### Использование в handlers

```python
from core.container import Container
from core.ports.bot_gateway import BotGateway

container: Container = context.bot_data.get("container")
bot_gateway: BotGateway = container.get_bot_gateway()

await bot_gateway.send_message(chat_id=123, text="Hello")
await bot_gateway.set_message_reaction(123, 456, "👍")
```

### FakeBotGateway для тестов

```python
from core.infrastructure.bot.fake_bot_gateway import FakeBotGateway

gateway = FakeBotGateway(
    simulate_delay=False,      # Имитировать задержку сети
    delay_seconds=0.01,        # Задержка в секундах
    fail_probability=0.0,      # Вероятность ошибки
)

# Отслеживание вызовов
await gateway.send_message(123, "msg")
stats = gateway.get_stats()  # {"send_message": 1, "total_calls": 1, ...}
```

### Нагрузочное тестирование

Скрипт для проверки rate limiter и производительности:

```bash
# Базовый тест
python -m scripts.load_test --users 20 --requests-per-user 10

# Тест с rate limit
python -m scripts.load_test --users 50 --requests-per-user 20 --rate-limit 5

# Burst тест (всплеск трафика)
python -m scripts.load_test --scenario burst --rate-limit 100
```

### Тесты

Проект использует многоуровневое тестирование:

- **Unit тесты** (`tests/unit/`) — 53 теста, без БД и внешних зависимостей
- **Application тесты** (`tests/application/`) — 4 теста, Fake UoW
- **Integration тесты** (`tests/integration/`) — 13 тестов, реальный PostgreSQL через testcontainers

**Всего: 70 тестов**

```bash
# Все тесты
uv run pytest tests/ -v

# Только unit тесты (быстро, не требует Docker)
uv run pytest tests/unit -v

# Только integration тесты (требует Docker)
uv run pytest tests/integration -v -m integration

# Пропустить integration тесты
uv run pytest tests/ -v -m "not integration"
```

### Integration тесты (testcontainers)

Integration тесты используют **реальный PostgreSQL** в Docker контейнере через testcontainers.

**Требования:**
- Docker должен быть запущен
- Python пакет `testcontainers`

**Запуск integration тестов:**

```bash
# Только integration тесты
uv run pytest tests/integration -v -m integration

# Все тесты (unit + integration)
uv run pytest tests/ -v

# Пропустить integration тесты (только unit)
uv run pytest tests/ -v -m "not integration"
```

**Структура integration тестов:**

```
tests/integration/
├── repositories/
│   ├── test_user_repository.py         # Тесты UserRepository
│   └── test_rating_ledger_repository.py # Тесты DbRatingLedgerRepository
└── use_cases/                          # TODO: тесты use cases
```

**Fixtures:**

- `postgres_container` — сессионный fixture, запускает PostgreSQL контейнер
- `db_manager` — DatabaseManager с применёнными миграциями (alembic)
- `db_connection` — подключение из пула для тестов
- `user_repo`, `chat_repo`, `rating_ledger_repo` — репозитории для тестов

## Важные заметки

### Требования к группе

- Бот должен быть **администратором** группы
- Группа должна быть **супергруппой** (для поддержки реакций)
- Права бота: чтение сообщений, просмотр реакций

### Rate Limiting

In-memory rate limiter реализован в `core/infrastructure/repositories/rate_limiter.py`. В планах — замена на Redis.

### Логирование

- Логи пишутся в `var/log/`
- Утилиты: `utils/logger.py`, `utils/trace_logger.py`
