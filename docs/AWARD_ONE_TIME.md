# 🎁 Разовые зачисления (One-Time Awards)

## 📋 Обзор

Скрипт для разовых зачислений очков пользователям без настройки через `chats.settings`.

**Использование:**
- ✅ Баг-баунти (вознаграждение за найденные баги)
- ✅ Ивенты (разовые мероприятия)
- ✅ Достижения (ручное поощрение)
- ✅ Компенсации
- ✅ Любые другие разовые зачисления

---

## 🚀 Использование

### Одиночное зачисление

```bash
# Зачислить 500 очков пользователю за баг-баунти
uv run python scripts/award_one_time.py \
    --chat-id -1001234567890 \
    --user-id 123456789 \
    --amount 500 \
    --comment "Баг-баунти за уязвимость XSS"
```

### Массовое зачисление из JSON

```bash
# Зачислить очки нескольким пользователям
uv run python scripts/award_one_time.py --bulk awards.json
```

**Формат `awards.json`:**
```json
[
  {
    "chat_id": -1001234567890,
    "user_id": 123456789,
    "amount": 500,
    "comment": "Баг-баунти за XSS"
  },
  {
    "chat_id": -1001234567890,
    "user_id": 987654321,
    "amount": 300,
    "comment": "Баг-баунти за SQLi"
  },
  {
    "chat_id": -1001234567890,
    "user_id": 456789123,
    "amount": 100,
    "comment": "Ивент 2026-03-01"
  }
]
```

---

## 📖 Аргументы

### Одиночное зачисление

| Аргумент | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `--chat-id` | int | ✅ | Telegram ID чата |
| `--user-id` | int | ✅ | Telegram ID пользователя |
| `--amount` | int | ❌ (по умолчанию: 50) | Сумма зачисления |
| `--comment` | str | ❌ (по умолчанию: "one_time_award") | Комментарий |

### Массовое зачисление

| Аргумент | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `--bulk` | str | ✅ | Путь к JSON файлу |

---

## 📊 Примеры

### Пример 1: Баг-баунти

```bash
uv run python scripts/award_one_time.py \
    --chat-id -1001234567890 \
    --user-id 123456789 \
    --amount 1000 \
    --comment "Критическая уязвимость (CVE-2026-XXXX)"
```

### Пример 2: Ивент

```bash
uv run python scripts/award_one_time.py \
    --chat-id -1001234567890 \
    --user-id 123456789 \
    --amount 200 \
    --comment "Победитель викторины 2026-03-01"
```

### Пример 3: Массовое зачисление за ивент

**Файл `event_2026_03_01.json`:**
```json
[
  {"chat_id": -1001234567890, "user_id": 111, "amount": 100, "comment": "Ивент 2026-03-01"},
  {"chat_id": -1001234567890, "user_id": 222, "amount": 100, "comment": "Ивент 2026-03-01"},
  {"chat_id": -1001234567890, "user_id": 333, "amount": 150, "comment": "Ивент 2026-03-01 (1 место)"}
]
```

```bash
uv run python scripts/award_one_time.py --bulk event_2026_03_01.json
```

### Пример 4: Компенсация

```bash
uv run python scripts/award_one_time.py \
    --chat-id -1001234567890 \
    --user-id 123456789 \
    --amount 50 \
    --comment "Компенсация за ложное срабатывание"
```

---

## 🔍 Проверка результатов

### Просмотр зачислений в БД

```sql
-- Последние разовые зачисления
SELECT
    rl.created_at,
    c.tg_id as chat_tg_id,
    u.tg_id as user_tg_id,
    rl.amount,
    rl.balance_after,
    rl.meta->>'comment' as comment
FROM rating_ledger rl
JOIN chats c ON rl.chat_id = c.id
JOIN users u ON rl.user_id = u.id
WHERE rl.operation_type = 'award'
  AND rl.operation_subtype = 'one_time_award'
ORDER BY rl.created_at DESC
LIMIT 10;
```

### Просмотр всех зачислений пользователя

```sql
SELECT
    rl.created_at,
    rl.operation_type,
    rl.operation_subtype,
    rl.amount,
    rl.balance_after,
    rl.meta->>'comment' as comment
FROM rating_ledger rl
WHERE rl.user_id = (SELECT id FROM users WHERE tg_id = 123456789)
  AND rl.operation_type = 'award'
ORDER BY rl.created_at DESC;
```

---

## 📁 Типы зачислений

| Тип | operation_type | operation_subtype | source_type |
|-----|----------------|-------------------|-------------|
| **Периодическое** | `award` | `periodic_award` | `system` |
| **Разовое** | `award` | `one_time_award` | `manual` |
| **Приветственное** | `bonus` | `welcome` | `system` |

---

## ⚠️ Важные заметки

1. **Скрипт создаёт пользователей и chat_users записи**, если они не существуют
2. **Требуется активное подключение к БД** (использует настройки из `.env`)
3. **Комментарий сохраняется в `rating_ledger.meta`** для аудита
4. **Можно отменить через SQL** (при необходимости):
   ```sql
   DELETE FROM rating_ledger
   WHERE operation_type = 'award'
     AND operation_subtype = 'one_time_award'
     AND meta->>'comment' = 'Неверное зачисление';
   ```

---

## 🛠️ Для разработчиков

### Добавление новых типов зачислений

1. Добавьте метод в `RatingLedgerService`:
```python
async def record_event_award(self, ..., event_name: str):
    entry = RatingLedgerEntryDTO(
        ...
        operation_type="award",
        operation_subtype="event_award",
        meta={"event_name": event_name},
    )
```

2. Обновите документацию

---

## 📞 Помощь

```bash
uv run python scripts/award_one_time.py --help
```
