# 🚀 Быстрый старт: Планировщик периодических бонусов

## ✅ Исправление ошибок

### Проблема 1: ValidationError
Была исправлена ошибка валидации Pydantic. Проблема была в создании временных настроек через `type("obj", ...)` вместо правильного `ChatPeriodicBonusSettings`.

### Проблема 2: InterfaceError (connection released)
Была исправлена ошибка с подключением к БД. Теперь задача планировщика сама получает подключение из пула в момент выполнения через `async with self.db_manager.pool.acquire()`.

### Файлы состояния
Теперь файлы планировщика хранятся в специальной папке:

```
var/scheduler/
└── scheduler_state.json      # Текущее состояние задач
```

**Старые файлы удалены:**
- `fastscheduler_state.json` ❌
- `fastscheduler_state_dead_letters.json` ❌

---

## 📊 Просмотр Dashboard

Dashboard позволяет мониторить задачи планировщика в реальном времени.

### Запуск Dashboard

```bash
# Вариант 1: Через Makefile
make dashboard

# Вариант 2: Напрямую
uv run python scripts/run_scheduler_dashboard.py
```

### Доступ к Dashboard

После запуска откройте в браузере:
- **UI Dashboard**: http://localhost:8000/scheduler/
- **API Docs**: http://localhost:8000/docs

### Что показывает Dashboard

1. **Jobs** - список всех задач:
   - Статус (scheduled, running, success, failed)
   - Следующий запуск
   - Количество выполнений
   - Cron-выражение

2. **History** - история выполнений:
   - Время запуска
   - Длительность выполнения
   - Ошибки (если были)

3. **Dead Letters** - упавшие задачи:
   - Текст ошибки
   - Количество попыток
   - Время последней ошибки

4. **Statistics** - статистика:
   - Всего выполнений
   - Всего ошибок
   - Время работы планировщика

---

## ⚙️ Настройка периодических бонусов

### Через SQL (быстро)

```sql
-- Включить еженедельные бонусы 100 очков для чата
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

### Проверка настроек

```sql
SELECT 
    tg_id,
    title,
    settings->'periodic_bonus'->>'enabled' as enabled,
    settings->'periodic_bonus'->>'schedule_type' as schedule,
    settings->'periodic_bonus'->>'amount' as amount
FROM chats
WHERE is_active = true;
```

---

## 🔄 Как это работает

### Архитектура (cron-задачи для каждого чата)

Для каждого чата с включенными бонусами создаётся **отдельная cron-задача**:

1. **При старте бота:**
   - Считываются настройки всех активных чатов
   - Для каждого чата с `periodic_bonus.enabled=true`:
     - Извлекается cron-выражение (или генерируется из schedule_type)
     - Создаётся cron-задача с указанным timezone
   - Задачи выполняются строго по расписанию

2. **При выполнении задачи:**
   - Создаётся новое подключение к БД
   - Получаются все активные пользователи чата
   - Каждому пользователю начисляется бонус
   - Создаётся запись в rating ledger

3. **Преимущества:**
   - ✅ Точное расписание для каждого чата
   - ✅ Нет проблем с event loop (новое подключение)
   - ✅ Изолированное выполнение (один чат = одна задача)
   - ✅ Правильная работа с timezone

---

## 🐛 Отладка

### Задачи не выполняются?

1. Проверьте, что бонусы включены:
```sql
SELECT tg_id, settings->'periodic_bonus'->>'enabled' FROM chats;
```

2. Проверьте, что задачи созданы:
   - Откройте Dashboard
   - Раздел "Jobs"
   - Должны быть задачи со статусом "scheduled"

3. Проверьте логи:
   - Ошибки видны в Dashboard → Dead Letters
   - Или в логах бота

### Задачи падают с ошибкой?

1. Откройте Dashboard → Dead Letters
2. Посмотрите текст ошибки
3. Проверьте настройки чата в БД

### Перезапуск планировщика

```bash
# Остановить бота
# Удалить файлы состояния
rm -f fastscheduler_state*.json

# Запустить бота заново
make run
```

---

## 📋 Cron-выражения

| Расписание | Cron | Описание |
|-----------|------|----------|
| Ежедневно в 12:00 | `0 12 * * *` | Каждый день |
| Еженедельно (Пн) | `0 12 * * 1` | Каждый понедельник |
| Ежемесячно (1 число) | `0 12 1 * *` | 1-го числа |
| Каждые 12 часов | `0 */12 * * *` | 2 раза в день |
| Каждый час | `0 * * * *` | В начале каждого часа |

---

## 🎯 Примеры использования

### Включить ежедневные бонусы

```sql
UPDATE chats SET settings = jsonb_set(
    settings, '{periodic_bonus,enabled}', 'true'
), settings = jsonb_set(
    settings, '{periodic_bonus,schedule_type}', '"daily"'
), settings = jsonb_set(
    settings, '{periodic_bonus,amount}', '50'
)
WHERE tg_id = -1001234567890;
```

### Изменить сумму бонуса

```sql
UPDATE chats SET settings = jsonb_set(
    settings, '{periodic_bonus,amount}', '200'
)
WHERE tg_id = -1001234567890;
```

### Отключить бонусы

```sql
UPDATE chats SET settings = jsonb_set(
    settings, '{periodic_bonus,enabled}', 'false'
)
WHERE tg_id = -1001234567890;
```

---

## 📞 Помощь

Если что-то не работает:
1. Проверьте логи бота
2. Откройте Dashboard → Dead Letters
3. Проверьте настройки в БД
4. Убедитесь, что планировщик запущен (Dashboard показывает задачи)
