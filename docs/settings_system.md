# Система настроек чатов

## Обзор

Система предоставляет универсальный механизм для хранения и управления настройками чатов и пользователей.
Настройки хранятся в JSONB полях в базе данных и валидируются через Pydantic схемы.

## Архитектура

```
core/domain/settings/          # Доменный слой - схемы настроек
├── base.py                    # Базовый класс SettingsBase
├── chat_settings.py           # Настройки чата (ChatSettings)
└── __init__.py

core/application/settings/     # Application слой - UseCase
├── get_chat_settings.py       # Получение настроек
├── update_chat_settings.py    # Обновление настроек
└── __init__.py

core/infrastructure/repositories/
└── chat_settings_repository.py  # Репозиторий для работы с БД
```

## Структура настроек чата

### Periodic Bonus (Периодические бонусы)

Настройки для автоматического начисления бонусов пользователям:

```python
class ChatPeriodicBonusSettings:
    enabled: bool = False                    # Включены ли бонусы
    schedule_type: Literal["daily", "weekly", "monthly"] = "weekly"
    cron_expression: str | None = None       # Кастомное cron-выражение
    amount: int = 50                         # Сумма бонуса
    timezone: str = "Europe/Moscow"          # Часовой пояс
```

**Примеры расписаний:**
- `daily` → `"0 12 * * *"` — каждый день в 12:00
- `weekly` → `"0 12 * * 1"` — каждый понедельник в 12:00
- `monthly` → `"0 12 1 * *"` — 1-го числа каждого месяца в 12:00

### Tax Settings (Настройки налога)

Настройки для налогообложения переводов:

```python
class ChatTaxSettings:
    enabled: bool = False           # Включен ли налог
    rate: float = 0.0              # Процент (0.0 - 1.0)
    collect_to_user_id: int | None = None  # ID для сбора налогов
```

## Использование

### Получение настроек чата

```python
from core.application.settings import GetChatSettingsUseCase
from core.infrastructure.repositories.chat_settings_repository import ChatSettingsRepository

# Создать репозиторий (требуется активное подключение)
settings_repo = ChatSettingsRepository(conn)

# Создать UseCase
get_settings = GetChatSettingsUseCase(settings_repo)

# Получить настройки
settings = await get_settings.execute(chat_id=123)

# Доступ к настройкам бонусов
bonus_settings = settings.periodic_bonus
if bonus_settings.enabled:
    print(f"Бонус: {bonus_settings.amount} очков")
    print(f"Расписание: {bonus_settings.get_cron_expression()}")
```

### Обновление настроек чата

```python
from core.application.settings import UpdateChatSettingsUseCase
from core.domain.settings import ChatSettings, ChatPeriodicBonusSettings

# Создать UseCase
update_settings = UpdateChatSettingsUseCase(settings_repo)

# Обновить настройки периодических бонусов
new_settings = settings.model_copy(
    update={
        "periodic_bonus": settings.periodic_bonus.model_copy(
            update={
                "enabled": True,
                "amount": 100,
                "schedule_type": "weekly",
            }
        )
    }
)

success = await update_settings.execute(
    chat_id=123,
    settings=new_settings,
)
```

### Прямая работа с репозиторием

```python
from core.domain.settings import ChatSettings

# Получить настройки
settings = await settings_repo.get_settings(chat_id=123)

# Обновить настройки
await settings_repo.update_settings(
    chat_id=123,
    settings=new_settings,
)
```

## Планировщик периодических бонусов

### Интеграция с FastScheduler

Планировщик автоматически:
1. Синхронизирует задачи с настройками чатов при старте
2. Создаёт cron-задачи для чатов с включенными бонусами
3. Удаляет задачи при отключении бонусов

### Dashboard для мониторинга

Для просмотра статуса задач и мониторинга используйте Dashboard:

```bash
# Запуск Dashboard
uv run python scripts/run_scheduler_dashboard.py
```

**Dashboard доступен по адресам:**
- 📊 UI: http://localhost:8000/scheduler/
- 📋 API docs: http://localhost:8000/docs

**Возможности Dashboard:**
- Просмотр всех запланированных задач
- Статус выполнения (успех/ошибка)
- История запусков с таймингами
- Dead letters (упавшие задачи)
- Пауза/возобновление/отмена задач
- Ручной запуск задач

### Автоматическое начисление

При выполнении задачи планировщика:
1. Получаются все активные пользователи чата
2. Каждому пользователю начисляется бонус
3. Создаётся запись в rating ledger с operation_type="bonus", operation_subtype="periodic"

## Примеры настройки через БД

### Включить ежедневные бонусы 50 очков

```sql
UPDATE chats
SET settings = jsonb_set(
    settings,
    '{periodic_bonus}',
    '{
        "enabled": true,
        "schedule_type": "daily",
        "amount": 50,
        "timezone": "Europe/Moscow"
    }'::jsonb
)
WHERE tg_id = -1001234567890;
```

### Включить еженедельные бонусы 100 очков

```sql
UPDATE chats
SET settings = jsonb_set(
    settings,
    '{periodic_bonus}',
    '{
        "enabled": true,
        "schedule_type": "weekly",
        "amount": 100,
        "timezone": "Europe/Moscow"
    }'::jsonb
)
WHERE tg_id = -1001234567890;
```

### Включить налог 10% на переводы

```sql
UPDATE chats
SET settings = jsonb_set(
    settings,
    '{tax}',
    '{
        "enabled": true,
        "rate": 0.1
    }'::jsonb
)
WHERE tg_id = -1001234567890;
```

### Сбросить все настройки

```sql
UPDATE chats
SET settings = '{}'::jsonb
WHERE tg_id = -1001234567890;
```

## Расширение системы

### Добавление новых настроек

1. Создать Pydantic схему в `core/domain/settings/chat_settings.py`:

```python
class ChatNewFeatureSettings(SettingsBase):
    enabled: bool = False
    some_parameter: int = 10
```

2. Добавить в `ChatSettings`:

```python
class ChatSettings(SettingsBase):
    periodic_bonus: ChatPeriodicBonusSettings = ...
    tax: ChatTaxSettings = ...
    new_feature: ChatNewFeatureSettings = Field(
        default_factory=ChatNewFeatureSettings
    )
```

3. Использовать в коде через `settings.new_feature`

## Миграции

При изменении структуры настроек:
- Pydantic `extra="ignore"` игнорирует неизвестные поля
- Старые поля сохраняются для обратной совместимости
- Новые поля получают значения по умолчанию

## Тестирование

Пример теста настроек:

```python
import pytest
from core.domain.settings import ChatSettings, ChatPeriodicBonusSettings

def test_default_settings():
    settings = ChatSettings.empty()
    assert settings.periodic_bonus.enabled is False
    assert settings.periodic_bonus.amount == 50

def test_custom_settings():
    settings = ChatSettings(
        periodic_bonus=ChatPeriodicBonusSettings(
            enabled=True,
            amount=100,
            schedule_type="daily",
        )
    )
    assert settings.periodic_bonus.get_cron_expression() == "0 12 * * *"
```

## Будущие расширения

- [ ] Настройки пользователей (`users.settings`)
- [ ] Веб-интерфейс для управления настройками
- [ ] Версионирование схем настроек
- [ ] Аудит изменений настроек
- [ ] Настраиваемые уведомления о начислениях
