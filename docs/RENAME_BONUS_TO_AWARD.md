# 🔄 Переименование: bonus → award

## 📋 Обзор

Изменена терминология с "бонус" (`bonus`) на "зачисление" (`award`) для более точного отражения функциональности.

### Почему это важно

**`bonus`** (бонус) — ассоциируется с чем-то额外ным, необязательным  
**`award`** (зачисление/награда) — более общий термин, который покрывает:
- ✅ Периодические зачисления (еженедельно/ежемесячно) для поддержания активности
- ✅ Разовые зачисления (баг-баунти, ивенты, достижения)
- ✅ Любые другие системные зачисления

---

## 📁 Изменённые файлы

### Переименованные файлы
| Было | Стало |
|------|-------|
| `periodic_bonus_service.py` | `periodic_award_service.py` |
| `bonus_scheduler.py` | `award_scheduler.py` |

### Обновлённые файлы
- `core/config.py` — `PeriodicBonusConfig` → `PeriodicAwardConfig`
- `core/domain/settings/chat_settings.py` — `ChatPeriodicBonusSettings` → `ChatPeriodicAwardSettings`
- `core/application/rating_ledger/rating_ledger_service.py` — `record_periodic_bonus()` → `record_periodic_award()`
- `core/infrastructure/repositories/chat_repository.py` — `list_with_periodic_bonus_enabled()` → `list_with_periodic_award_enabled()`
- `bot/main.py` — `BonusScheduler` → `AwardScheduler`
- `tests/unit/domain/settings/test_chat_settings.py` — обновлены тесты

---

## 🔧 Изменения в настройках

### JSON структура settings

**Было:**
```json
{
  "periodic_bonus": {
    "enabled": true,
    "schedule_type": "weekly",
    "amount": 100,
    "timezone": "Europe/Moscow"
  }
}
```

**Стало:**
```json
{
  "periodic_award": {
    "enabled": true,
    "schedule_type": "weekly",
    "amount": 100,
    "timezone": "Europe/Moscow",
    "comment": "weekly activity"  // ← Новое поле для комментариев
  }
}
```

---

## 🗄️ Миграция БД

### Применение миграции

```bash
make migrate
```

Или вручную:
```bash
uv run alembic upgrade head
```

### Откат миграции

```bash
uv run alembic downgrade -1
```

---

## 📊 Изменения в rating ledger

### Типы операций

**Было:**
```python
operation_type="bonus"
operation_subtype="periodic"
```

**Стало:**
```python
operation_type="award"
operation_subtype="periodic_award"
```

---

## 💡 Примеры использования

### Настройка еженедельных зачислений

```sql
UPDATE chats
SET settings = jsonb_set(
    settings,
    '{periodic_award}',
    '{
        "enabled": true,
        "schedule_type": "weekly",
        "amount": 100,
        "timezone": "Europe/Moscow",
        "comment": "weekly activity"
    }'::jsonb
)
WHERE tg_id = -1001234567890;
```

### Настройка зачисления за баг-баунти (разовое)

```sql
UPDATE chats
SET settings = jsonb_set(
    settings,
    '{periodic_award}',
    '{
        "enabled": true,
        "schedule_type": "monthly",
        "amount": 500,
        "timezone": "Europe/Moscow",
        "comment": "bug bounty program"
    }'::jsonb
)
WHERE tg_id = -1001234567890;
```

---

## ✅ Тесты

Все тесты обновлены и проходят:

```bash
uv run pytest tests/unit/domain/settings/test_chat_settings.py -v
# 25 passed in 0.05s ✅
```

---

## 📝 Чеклист для разработчиков

- [ ] Применить миграцию `005_rename_periodic_bonus_to_award`
- [ ] Обновить документацию проекта
- [ ] Проверить логи после деплоя
- [ ] Обновить админ-панель (если есть)

---

## 🔄 Обратная совместимость

Миграция автоматически переименовывает `periodic_bonus` → `periodic_award` в существующих записях.

**Важно:** После применения миграции старые ключи `periodic_bonus` больше не работают!
