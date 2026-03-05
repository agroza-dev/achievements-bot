# Архитектура настроек чатов

## Обзор

Настройки чатов вынесены из JSONB поля в отдельную нормализованную таблицу с историей изменений.

## Структура БД

### chat_settings

```sql
CREATE TABLE chat_settings (
    chat_id BIGINT PRIMARY KEY REFERENCES chats(id),
    
    -- Periodic award настройки
    periodic_award_enabled BOOLEAN DEFAULT true,
    periodic_award_amount INT,  -- NULL = использовать дефолт из конфига
    
    -- Tax настройки
    tax_enabled BOOLEAN DEFAULT false,
    tax_rate NUMERIC(5, 2) DEFAULT 0.00,  -- 0.00 - 99.99 (проценты)
    
    -- Мета-поля
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by_user_id BIGINT REFERENCES users(id)
);
```

### chat_settings_history

```sql
CREATE TABLE chat_settings_history (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(id),
    setting_name VARCHAR(64),  -- Например: "periodic_award_enabled"
    old_value JSONB,
    new_value JSONB,
    changed_by_user_id BIGINT REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Преимущества

### 1. Валидация на уровне БД
```sql
-- CHECK constraint для tax_rate (опционально)
ALTER TABLE chat_settings
ADD CONSTRAINT chk_tax_rate CHECK (tax_rate >= 0 AND tax_rate <= 100);
```

### 2. История изменений
```python
# Получаем историю
history = await settings_repo.get_history(chat_id=123, limit=10)

# Каждая запись содержит:
# - setting_name: "periodic_award_amount"
# - old_value: {"value": 50}
# - new_value: {"value": 100}
# - changed_by_user_id: 456
# - changed_at: 2026-03-02 12:00:00
```

### 3. Аудит
```sql
-- Кто и когда изменил настройки
SELECT 
    h.setting_name,
    h.old_value,
    h.new_value,
    u.username as changed_by,
    h.changed_at
FROM chat_settings_history h
LEFT JOIN users u ON h.changed_by_user_id = u.id
WHERE h.chat_id = 123
ORDER BY h.changed_at DESC;
```

### 4. Быстрые запросы
```sql
-- Найти все чаты с налогом > 10%
SELECT chat_id, tax_rate
FROM chat_settings
WHERE tax_rate > 10;

-- Индексы уже созданы:
-- idx_chat_settings_updated_at
-- idx_chat_settings_history_chat_id
-- idx_chat_settings_history_changed_at
-- idx_chat_settings_history_setting
```

## Использование

### Получить настройки

```python
from core.infrastructure.repositories.chat_settings_repository_v2 import ChatSettingsRepositoryV2

async with db_manager.pool.acquire() as conn:
    settings_repo = ChatSettingsRepositoryV2(conn)
    
    # Получить или создать (создаст с дефолтами если нет)
    settings = await settings_repo.get_or_create_settings(chat_id=123)
    
    print(f"Periodic award enabled: {settings.periodic_award_enabled}")
    print(f"Periodic award amount: {settings.periodic_award_amount}")  # None = дефолт
    print(f"Tax enabled: {settings.tax_enabled}")
    print(f"Tax rate: {settings.tax_rate}")  # 0.0 - 99.99
```

### Обновить настройки

```python
# Обновить одно поле
await settings_repo.update_settings(
    chat_id=123,
    periodic_award_enabled=False,
)

# Обновить несколько полей
await settings_repo.update_settings(
    chat_id=123,
    periodic_award_amount=100,
    tax_enabled=True,
    tax_rate=15.0,  # 15%
    updated_by_user_id=456,  # Кто изменил
)

# История запишется автоматически!
```

### Получить историю

```python
# Получить последние 50 изменений
history = await settings_repo.get_history(
    chat_id=123,
    limit=50,
    offset=0,
)

for entry in history:
    print(f"{entry.changed_at}: {entry.setting_name}")
    print(f"  {entry.old_value} -> {entry.new_value}")
    print(f"  Changed by user: {entry.changed_by_user_id}")
```

## Добавление новых настроек

### 1. Добавить колонку в миграцию

```python
# alembic/versions/007_add_notification_settings.py
def upgrade():
    op.add_column(
        "chat_settings",
        sa.Column("notifications_enabled", sa.Boolean, server_default="true"),
    )
    op.add_column(
        "chat_settings",
        sa.Column("notifications_min_rating", sa.Integer, server_default="100"),
    )
```

### 2. Обновить DTO

```python
# core/dto/chat_settings_dto.py
@dataclass(slots=True)
class ChatSettingsDTO:
    chat_id: int
    periodic_award_enabled: bool = True
    periodic_award_amount: int | None = None
    tax_enabled: bool = False
    tax_rate: float = 0.0
    notifications_enabled: bool = True  # NEW!
    notifications_min_rating: int = 100  # NEW!
    # ...
```

### 3. Обновить репозиторий

```python
# core/infrastructure/repositories/chat_settings_repository_v2.py
async def update_settings(self, chat_id: int, **kwargs: Any):
    allowed_fields = {
        'periodic_award_enabled',
        'periodic_award_amount',
        'tax_enabled',
        'tax_rate',
        'notifications_enabled',  # NEW!
        'notifications_min_rating',  # NEW!
        'updated_by_user_id',
    }
    # ...
```

### 4. Миграция данных (опционально)

```python
# Заполнить дефолтами для существующих чатов
op.execute("""
    UPDATE chat_settings
    SET 
        notifications_enabled = true,
        notifications_min_rating = 100
    WHERE notifications_enabled IS NULL
""")
```

## Миграция со старой версии

### Автоматическая миграция данных

Миграция `006` автоматически переносит данные из старого JSONB поля:

```sql
-- Из
chats.settings = {
  "periodic_award": {"enabled": true, "amount": 50},
  "tax": {"enabled": false, "rate": 0.1}
}

-- В
chat_settings:
  periodic_award_enabled = true
  periodic_award_amount = 50
  tax_enabled = false
  tax_rate = 0.1
```

### Откат

Если нужно откатиться:

```bash
uv run alembic downgrade -1
```

Миграция:
1. Вернёт поле `chats.settings`
2. Перенесёт данные из `chat_settings` обратно в JSONB
3. Удалит новые таблицы

## Производительность

### Индексы

```sql
-- Для быстрых запросов по updated_at
CREATE INDEX idx_chat_settings_updated_at ON chat_settings (updated_at);

-- Для истории
CREATE INDEX idx_chat_settings_history_chat_id ON chat_settings_history (chat_id);
CREATE INDEX idx_chat_settings_history_changed_at ON chat_settings_history (changed_at);
CREATE INDEX idx_chat_settings_history_setting ON chat_settings_history (setting_name);
```

### ТРИГГЕР для updated_at

```sql
-- Автоматически обновляет updated_at при изменении
CREATE TRIGGER update_chat_settings_updated_at
    BEFORE UPDATE ON chat_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## Best Practices

### 1. Всегда указывайте updated_by_user_id

```python
await settings_repo.update_settings(
    chat_id=123,
    periodic_award_enabled=True,
    updated_by_user_id=user_id,  # Обязательно для аудита!
)
```

### 2. Используйте get_or_create_settings

```python
# Вместо проверки существует ли
settings = await settings_repo.get_settings(chat_id)
if not settings:
    # Создавать...

# Используйте:
settings = await settings_repo.get_or_create_settings(chat_id)
```

### 3. Логируйте изменения в бизнес-логике

```python
# История запишется автоматически, но можно добавить контекст
logger.info(
    f"Настройки чата {chat_id} изменены пользователем {user_id}: "
    f"periodic_award_enabled={new_value}"
)
```

### 4. Кэшируйте настройки

Для часто используемых настроек добавьте кэш:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def get_cached_settings(chat_id: int):
    return await settings_repo.get_settings(chat_id)
```

## Мониторинг

### Запросы для мониторинга

```sql
-- Количество чатов с включенными зачислениями
SELECT COUNT(*) FROM chat_settings WHERE periodic_award_enabled = true;

-- Средний налог
SELECT AVG(tax_rate) FROM chat_settings WHERE tax_enabled = true;

-- Последние изменения
SELECT 
    c.title as chat_title,
    h.setting_name,
    h.new_value,
    h.changed_at
FROM chat_settings_history h
JOIN chats c ON h.chat_id = c.id
ORDER BY h.changed_at DESC
LIMIT 10;
```

---

**Статус**: ✅ Production Ready  
**Версия**: v1  
**Миграция**: 006
