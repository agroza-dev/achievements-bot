# Архитектура периодических зачислений (Award System)

## Обзор

Система периодических зачислений построена по паттерну **Producer-Consumer** с использованием базы данных как очереди задач.

## Компоненты

```
┌─────────────────────────────────────────────┐
│  Producer (AwardProducer)                   │
│  ─────────────────────────────────────────  │
│  • Запускается по cron (пятница 18:00)      │
│  • Создаёт batch для каждого чата           │
│  • period_key = "2026-W09" (номер недели)   │
│  • Idempotency: UNIQUE(chat_id, period_key) │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  award_batches (БД)                         │
│  ─────────────────────────────────────────  │
│  id | chat_id | period_key | status |       │
│  cursor_user_id | created_at | done_at      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Worker (AwardWorker)                       │
│  ─────────────────────────────────────────  │
│  • Постоянный цикл (poll 30 сек)            │
│  • Берёт pending/processing batch           │
│  • Обрабатывает по 50 пользователей         │
│  • Обновляет cursor_user_id                 │
│  • Ledger: UNIQUE(user_id, period_key)      │
└─────────────────────────────────────────────┘
```

## Надёжность

### 1. Idempotency на уровне Ledger
```sql
UNIQUE(user_id, operation_type, operation_key)
```
- `operation_key = period_key` (например, "2026-W09")
- Гарантирует что пользователь получит зачисление только один раз за период
- При повторной попытке будет `ON CONFLICT DO NOTHING`

### 2. Resume через cursor
```sql
award_batches.cursor_user_id
```
- Хранит ID последнего обработанного пользователя
- При падении бота worker продолжит с этого места
- Batch остаётся в статусе `processing` до завершения

### 3. Crash-safe обработка
```
Сценарий падения:
1. Worker взял batch (status=processing)
2. Обработал 340 из 1000 пользователей
3. Бот упал

После рестарта:
- Worker находит processing batch
- Берёт пользователей с user_id > cursor_user_id
- Продолжает обработку
```

## Конфигурация

### Единое расписание (core/config.py)
```python
class PeriodicAwardConfig:
    DEFAULT_AMOUNT: int = 50           # Базовая сумма
    TIMEZONE: str = "Europe/Moscow"    # Часовой пояс
    CRON_EXPRESSION: str = "0 18 * * 5"  # Пятница 18:00
    BATCH_SIZE: int = 50               # Пользователей за проход
    WORKER_POLL_INTERVAL: int = 30     # Секунды между опросами
```

### Настройки чата (JSONB в БД)
```python
class ChatPeriodicAwardSettings:
    enabled: bool = True              # Включено ли зачисление
    amount: int | None = None         # Сумма (None = DEFAULT_AMOUNT)
```

## База данных

### award_batches
```sql
CREATE TABLE award_batches (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(id),
    period_key VARCHAR(20) NOT NULL,  -- "2026-W09"
    status VARCHAR(20) DEFAULT 'pending',  -- pending|processing|done
    cursor_user_id BIGINT,  -- ID последнего обработанного
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    UNIQUE(chat_id, period_key)  -- один batch на чат за период
);
```

### rating_ledger (обновлено)
```sql
ALTER TABLE rating_ledger 
ADD CONSTRAINT uq_rating_ledger_user_period 
UNIQUE(user_id, operation_type, operation_key);
```

## Жизненный цикл

### 1. Producer (пятница 18:00)
```python
# Получаем текущий период
period_key = "2026-W09"

# Для каждого активного чата
for chat in active_chats:
    if chat.award_enabled:
        # Создаём batch (или получаем существующий)
        batch = create_or_get_batch(chat_id, period_key)
```

### 2. Worker (постоянно)
```python
while True:
    # Ищем processing batch (recovery) или pending
    batch = get_next_batch()
    
    if not batch:
        sleep(30)
        continue
    
    # Берём пользователей (с учётом cursor)
    users = get_users(chat_id, cursor_user_id, limit=50)
    
    if not users:
        mark_done(batch)
        continue
    
    # Обрабатываем
    for user in users:
        award_to_user(user, period_key)
    
    # Обновляем cursor
    update_cursor(batch, last_user_id)
```

### 3. Зачисление пользователю
```python
async def award_to_user(user_id, period_key):
    # Пробуем создать запись в Ledger
    inserted = INSERT INTO rating_ledger 
               (..., operation_key=period_key)
               ON CONFLICT DO NOTHING
    
    if not inserted:
        return  # Уже было зачисление
    
    # Обновляем рейтинг
    new_balance = UPDATE ratings SET value += amount
```

## Мониторинг

### Статус batch
```sql
SELECT status, COUNT(*) 
FROM award_batches 
GROUP BY status;
```

### Незавершённые зачисления
```sql
SELECT * FROM award_batches 
WHERE status != 'done' 
ORDER BY created_at;
```

### Дубли за период
```sql
SELECT user_id, period_key, COUNT(*)
FROM rating_ledger
WHERE operation_type = 'award'
  AND operation_subtype = 'periodic_award'
GROUP BY user_id, period_key
HAVING COUNT(*) > 1;
```

## Тестирование

### Ручное создание batch
```python
async with db_manager.pool.acquire() as conn:
    repo = AwardBatchRepository(conn)
    batch = await repo.create_or_get_batch(
        chat_id=-1001234567890,
        period_key="2026-W09"
    )
```

### Проверка worker
```bash
# Запустить бота и смотреть логи
uv run python -m bot.main

# Логи worker:
"Award worker запущен"
"Начата обработка batch 1 для чата -1001234567890"
"Batch 1 завершён: все пользователи обработаны"
```

## Расширение

### Добавление нового типа задач
1. Создать handler в `core/infrastructure/scheduler/`
2. Зарегистрировать в `AwardScheduler`
3. Добавить cron или использовать тот же worker

### Масштабирование
- Worker можно запускать в нескольких инстансах
- БД гарантирует что один batch обрабатывается только одним worker
- При 1000+ чатах уменьшить `BATCH_SIZE` или `WORKER_POLL_INTERVAL`

## Миграция

```bash
# Применить миграцию
uv run alembic upgrade head

# Проверить
uv run alembic current
```
