# 🚀 Запуск приложения

## 📋 Обзор

Приложение состоит из трёх компонентов:

1. **Telegram Bot** — polling для обработки сообщений
2. **Scheduler** — планировщик периодических зачислений
3. **Dashboard** — FastAPI веб-интерфейс для мониторинга

---

## 🎯 Варианты запуска

### Вариант 1: Бот + Dashboard (единый процесс) ⭐ Рекомендуется

**Для:** Разработки и staging

```bash
make run-with-dashboard
```

**Что происходит:**
- ✅ Запускается Telegram bot (polling)
- ✅ Запускается Scheduler
- ✅ Запускается FastAPI Dashboard на `http://localhost:8000`
- ✅ Все компоненты в одном процессе
- ✅ Общий pool подключений к БД

**Endpoints:**
- Dashboard: http://localhost:8000/scheduler/
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

**Файл:** `scripts/run_bot_with_dashboard.py`

---

### Вариант 2: Только бот

**Для:** Production (когда Dashboard не нужен)

```bash
make run
```

**Что происходит:**
- ✅ Запускается Telegram bot (polling)
- ✅ Запускается Scheduler
- ❌ Dashboard не запускается

**Файл:** `bot/main.py`

---

### Вариант 3: Отдельный Dashboard

**Для:** Отладки или когда Dashboard нужен отдельно от бота

```bash
# В одном терминале
make run

# В другом терминале
make dashboard
```

**Что происходит:**
- ✅ Бот работает в одном процессе
- ✅ Dashboard работает в другом процессе на `http://localhost:8000`
- ⚠️ Два отдельных подключения к БД

**Файл:** `scripts/run_scheduler_dashboard.py`

---

## 📊 Архитектура

### Вариант 1: Единый процесс (рекомендуется)

```
┌─────────────────────────────────────┐
│     scripts/run_bot_with_dashboard.py│
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │ Telegram Bot │  │  FastAPI    │ │
│  │   (polling)  │  │  :8000      │ │
│  └──────────────┘  └─────────────┘ │
│           │                │        │
│  ┌────────────────────────────────┐ │
│  │  Scheduler (один на всех)      │ │
│  └────────────────────────────────┘ │
│                    │                │
│  ┌────────────────────────────────┐ │
│  │  DB Pool (один на всех)        │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
            │
     ┌──────────────┐
     │  PostgreSQL  │
     └──────────────┘
```

**Преимущества:**
- ✅ Один процесс — проще управлять
- ✅ Общие ресурсы (Scheduler, DB pool)
- ✅ Консистентность данных
- ✅ Проще деплой

---

### Вариант 3: Раздельные процессы

```
┌─────────────────┐     ┌──────────────────┐
│  bot/main.py    │     │  run_scheduler_  │
│  (Telegram Bot) │     │  dashboard.py    │
│                 │     │  (FastAPI :8000) │
└─────────────────┘     └──────────────────┘
        │                        │
        └────────────┬───────────┘
                     │
              ┌──────────────┐
              │  PostgreSQL  │
              └──────────────┘
```

**Преимущества:**
- ✅ Изоляция (упал dashboard — бот работает)
- ✅ Можно масштабировать отдельно
- ✅ Безопасность (dashboard во внутренней сети)

**Недостатки:**
- ❌ Два процесса
- ❌ Дублирование подключений к БД

---

## 🏭 Production

### Рекомендуемая архитектура для production

```
┌─────────────────┐
│  Telegram Bot   │
│  (только бот)   │
│  make run       │
└─────────────────┘
        │
┌─────────────────┐
│  Scheduler +    │
│  Dashboard      │
│  (внутренняя    │
│   сеть :8000)   │
│  make dashboard │
└─────────────────┘
        │
┌─────────────────┐
│  PostgreSQL     │
└─────────────────┘
```

### Docker Compose (пример)

```yaml
version: '3.8'

services:
  bot:
    build: .
    command: make run
    environment:
      - APP_CONFIG__BOT_TOKEN=xxx
      - APP_CONFIG__DB_HOST=db
    depends_on:
      - db
    restart: unless-stopped

  dashboard:
    build: .
    command: make dashboard
    environment:
      - APP_CONFIG__DB_HOST=db
    depends_on:
      - db
    ports:
      - "127.0.0.1:8000:8000"  # Только localhost!
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=achievements
      - POSTGRES_USER=xxx
      - POSTGRES_PASSWORD=xxx
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## 🔧 Команды

| Команда | Описание | Для кого |
|---------|----------|----------|
| `make run` | Только бот | Production |
| `make run-with-dashboard` | Бот + Dashboard | Разработка ⭐ |
| `make dashboard` | Только Dashboard | Отладка |
| `make award ...` | Разовое зачисление | Администрирование |

---

## 📁 Файлы запуска

| Файл | Назначение |
|------|-----------|
| `bot/main.py` | Основной файл бота |
| `scripts/run_bot_with_dashboard.py` | Бот + Dashboard (единый процесс) |
| `scripts/run_scheduler_dashboard.py` | Только Dashboard (отдельный процесс) |
| `scripts/award_one_time.py` | Разовые зачисления |

---

## 🚀 Быстрый старт

### Разработка

```bash
# 1. Клонировать репозиторий
git clone <repo>
cd achievementsbot

# 2. Установить зависимости
uv sync

# 3. Настроить .env
cp .env.template .env
# Отредактировать .env

# 4. Запустить миграции
make migrate

# 5. Запустить бота с Dashboard
make run-with-dashboard
```

### Production

```bash
# 1. Настроить окружение
export APP_CONFIG__BOT_TOKEN=xxx
export APP_CONFIG__DB_HOST=xxx

# 2. Запустить бота
make run

# 3. (Опционально) Запустить Dashboard во внутренней сети
make dashboard
```

---

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

**Ответ:**
```json
{
  "status": "ok",
  "scheduler_running": true
}
```

### Dashboard

Откройте в браузере:
- http://localhost:8000/scheduler/

### API Docs

Откройте в браузере:
- http://localhost:8000/docs

---

## ⚠️ Важные заметки

1. **Dashboard не должен быть в интернете!**
   - В production запускайте на `127.0.0.1:8000`
   - Используйте reverse proxy (nginx) для доступа
   - Или запускайте в отдельной внутренней сети

2. **Один Scheduler на приложение**
   - Не запускайте несколько процессов с Scheduler
   - Иначе задачи выполнятся несколько раз!

3. **База данных**
   - Убедитесь, что pool подключений не переполнен
   - В production настройте `APP_CONFIG__DB_POOL_MAX_SIZE`

---

## 📞 Помощь

```bash
# Показать все команды
make help

# Помощь по скриптам
uv run python scripts/run_bot_with_dashboard.py --help
uv run python scripts/award_one_time.py --help
```
