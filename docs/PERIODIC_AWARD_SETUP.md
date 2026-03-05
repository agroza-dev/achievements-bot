# Настройка периодических зачислений

## Быстрый старт

### 1. Применить миграцию БД
```bash
uv run alembic upgrade head
```

### 2. Проверить конфигурацию

По умолчанию зачисления включены для всех чатов.
Базовая сумма: **50 очков**.

Расписание: **каждую пятницу в 18:00 (Moscow time)**.

### 3. Запустить бота
```bash
uv run python -m bot.main
```

Worker автоматически запустится и начнёт обработку.

---

## Конфигурация

### Изменить расписание (для всех чатов)

В `core/config.py`:
```python
class PeriodicAwardConfig:
    CRON_EXPRESSION: str = "0 18 * * 5"  # Пятница 18:00
    TIMEZONE: str = "Europe/Moscow"
```

Cron формат: `минута час день месяц день_недели`
- `0 18 * * 5` = пятница, 18:00
- `0 12 * * 1-5` = пн-пт, 12:00
- `0 9 1 * *` = 1-е число месяца, 9:00

### Изменить базовую сумму

В `core/config.py`:
```python
class PeriodicAwardConfig:
    DEFAULT_AMOUNT: int = 50  # Очков
```

### Настроить для конкретного чата

Через бота установить настройки чата:
```python
# В settings чата:
{
  "periodic_award": {
    "enabled": true,    # Включить/отключить
    "amount": 100       # Индивидуальная сумма (None = базовая)
  }
}
```

---

## Мониторинг

### Проверить статус batch
```sql
SELECT 
    chat_id, 
    period_key, 
    status, 
    cursor_user_id,
    created_at,
    completed_at
FROM award_batches
ORDER BY created_at DESC
LIMIT 10;
```

### Найти зависшие batch
```sql
SELECT * 
FROM award_batches 
WHERE status != 'done' 
  AND created_at < NOW() - INTERVAL '1 hour';
```

### Проверить зачисления за период
```sql
SELECT 
    chat_id, 
    COUNT(*) as count,
    SUM(amount) as total
FROM rating_ledger
WHERE operation_type = 'award'
  AND operation_subtype = 'periodic_award'
  AND operation_key = '2026-W09'  -- Нужный период
GROUP BY chat_id;
```

---

## Troubleshooting

### Worker не обрабатывает batch

1. Проверить логи:
```
"Award worker запущен"
"Начата обработка batch..."
```

2. Проверить есть ли pending batch:
```sql
SELECT * FROM award_batches WHERE status = 'pending';
```

3. Проверить есть ли пользователи в чате:
```sql
SELECT COUNT(*) FROM chat_users 
WHERE chat_id = -1001234567890 AND is_active = true;
```

### Дубли зачислений

Проверить дубли:
```sql
SELECT user_id, period_key, COUNT(*)
FROM rating_ledger
WHERE operation_type = 'award'
  AND operation_subtype = 'periodic_award'
GROUP BY user_id, period_key
HAVING COUNT(*) > 1;
```

Если дубли есть — значит не работает UNIQUE constraint.

### Batch завис в processing

1. Найти зависший batch:
```sql
SELECT * FROM award_batches 
WHERE status = 'processing' 
  AND created_at < NOW() - INTERVAL '1 hour';
```

2. Вернуть в pending:
```sql
UPDATE award_batches 
SET status = 'pending', cursor_user_id = NULL
WHERE id = <batch_id>;
```

3. Перезапустить бота — worker подхватит batch.

---

## Тестирование

### Создать тестовый batch вручную
```python
import asyncio
from core.infrastructure.database import DatabaseManager
from core.infrastructure.repositories.award_batch_repository import AwardBatchRepository

async def test():
    db = DatabaseManager()
    await db.init_pool()
    
    async with db.pool.acquire() as conn:
        repo = AwardBatchRepository(conn)
        batch = await repo.create_or_get_batch(
            chat_id=-1001234567890,  # Ваш тестовый чат
            period_key="2026-W09"
        )
        print(f"Batch создан: {batch.id}, status={batch.status}")

asyncio.run(test())
```

### Проверить зачисление
```sql
-- Последний batch
SELECT * FROM award_batches ORDER BY created_at DESC LIMIT 1;

-- Зачисления за период
SELECT user_id, amount, balance_after, created_at
FROM rating_ledger
WHERE operation_type = 'award'
  AND operation_subtype = 'periodic_award'
  AND operation_key = '2026-W09'
ORDER BY created_at;
```

---

## Архитектура

Подробная документация: [PERIODIC_AWARD_ARCHITECTURE.md](PERIODIC_AWARD_ARCHITECTURE.md)

### Ключевые принципы

1. **Idempotency**: Ledger с UNIQUE(user_id, operation_type, operation_key)
2. **Resume**: cursor_user_id для продолжения после падения
3. **Crash-safe**: batch не удаляется пока не завершён
4. **Масштабируемость**: worker можно запускать в нескольких инстансах
