# Миграция с PicklePersistence на PostgreSQLPersistence

## Обзор

Эта миграция заменяет хранение данных персистентности бота из небезопасного `persistence.pkl` в надёжное PostgreSQL-хранилище.

## Проблемы старого подхода (PicklePersistence)

1. **Безопасность**: Pickle выполняет произвольный код при десериализации
2. **Хрупкость**: При рефакторинге кода pickle-файлы становятся нечитаемыми
3. **Отсутствие версионирования**: Нет механизма миграции данных
4. **Бинарный формат**: Нельзя прочитать вручную, сложно дебажить
5. **Конкурентный доступ**: Возможны гонки и повреждения файла

## Преимущества нового подхода (PostgreSQLPersistence)

1. **Безопасность**: Нет выполнения произвольного кода
2. **Надёжность**: ACID-транзакции, целостность данных
3. **Конкурентный доступ**: PostgreSQL обрабатывает параллельные запросы
4. **Версионирование**: Миграции через Alembic
5. **Читаемость**: JSON-формат в БД, можно смотреть напрямую

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram Bot Application                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               PostgreSQLPersistence                         │
│  (реализация BasePersistence)                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         PostgreSQLBotPersistenceRepository                  │
│  (репозиторий для работы с БД)                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Database                            │
│  Таблица: bot_persistence                                   │
│  - id (BIGINT PRIMARY KEY)                                  │
│  - chat_id (BIGINT)                                         │
│  - user_id (BIGINT)                                         │
│  - bot_data (JSONB)                                         │
│  - chat_data (JSONB)                                        │
│  - user_data (JSONB)                                        │
│  - updated_at (TIMESTAMPTZ)                                 │
└─────────────────────────────────────────────────────────────┘
```

## Установленные файлы

### Модели и репозитории
- `core/models/bot_persistence_model.py` — SQLAlchemy модель таблицы
- `core/ports/repositories/bot_persistence_repository.py` — интерфейс репозитория
- `core/infrastructure/repositories/bot_persistence_repository.py` — реализация репозитория
- `core/infrastructure/repositories/postgresql_persistence.py` — реализация BasePersistence

### Миграции
- `alembic/versions/e521f296cb89_add_bot_persistence_table.py` — миграция для создания таблицы

### Скрипты
- `scripts/migrate_persistence.py` — скрипт для переноса данных из pickle в БД

### Изменения
- `bot/main.py` — замена PicklePersistence на PostgreSQLPersistence
- `alembic/env.py` — добавлена модель для autogenerate


```bash
uv run scripts/migrate_persistence.py
```

Скрипт:
1. Загружает данные из `persistence.pkl`
2. Создаёт таблицу `bot_persistence` (если не существует)
3. Переносит данные в PostgreSQL
4. Создаёт резервную копию pickle-файла с суффиксом `.backup_<timestamp>`

### Ручная миграция (если скрипт не работает)

```bash
# 1. Примените миграцию Alembic
uv run alembic upgrade head

# 2. Запустите бота — данные создадутся заново
# Старые данные из pickle не будут перенесены
```

## Применение миграции

```bash
# Применить все миграции
uv run alembic upgrade head

# Проверить текущую ревизию
uv run alembic current

# Откатиться на ревизию назад
uv run alembic downgrade -1
```

## Проверка работы

1. **Проверьте существование таблицы:**
```sql
SELECT * FROM bot_persistence LIMIT 10;
```

2. **Запустите бота:**
```bash
python -m bot.main
```

3. **Проверьте логи:**
- Должно быть сообщение "Persistence data flushed" при остановке
- Не должно быть ошибок при загрузке/сохранении данных

## Структура данных

### bot_data
Глобальные данные бота + специальные ключи:
- `__callback_data__` — данные callback-кэша
- `__conversations__` — состояния ConversationHandler

### chat_data
Данные по чатам (ключ: chat_id):
- Пользовательские данные чата
- Состояния FSM для чата

### user_data
Данные по пользователям (ключ: user_id):
- Пользовательские состояния FSM
- Временные данные пользователя

## Откат миграции

Если нужно вернуться к PicklePersistence:

```bash
# 1. Откатите миграцию БД
uv run alembic downgrade 4e00fdd8041a

# 2. Восстановите pickle-файл из бэкапа
cp var/db/persistence.pkl.backup_YYYYMMDD_HHMMSS var/db/persistence.pkl

# 3. Откатите изменения в коде (git checkout)
git checkout HEAD -- bot/main.py core/config.py
```

## Производительность

### Пул подключений
- `pool_min_size: 1` — минимальное количество подключений
- `pool_max_size: 10` — максимальное количество подключений
- Одно дополнительное подключение для persistence достаточно

### Интервал обновления
- `update_interval: 60` — обновление каждые 60 секунд
- Данные также сохраняются при каждом изменении (on_flush=False)

## Безопасность

1. **Не храните чувствительные данные** в bot_data/chat_data/user_data
2. **Ограничьте доступ** к таблице `bot_persistence` на уровне БД
3. **Регулярно делайте бэкапы** базы данных

## Troubleshooting

### Ошибка "Database pool not initialized"
- Проверьте, что `DatabaseManager.init_pool()` вызван до создания persistence

### Ошибка "relation bot_persistence does not exist"
- Примените миграцию: `uv run alembic upgrade head`

### Данные не сохраняются
- Проверьте логи на наличие ошибок
- Убедитесь, что `flush()` вызывается при остановке бота

### Конфликты при вставке (UNIQUE violation)
- Проверьте логику разделения chat_data и user_data
- Убедитесь, что WHERE-условия в ON CONFLICT работают корректно
