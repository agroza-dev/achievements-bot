

❌ scheduler (когда запускать)

✅ orchestration (что именно нужно обработать)

✅ execution (как безопасно обработать каждого пользователя)

fastscheduler решает только пункт №1 — он НЕ должен отвечать за надёжность выполнения.

Надёжность нужно строить на уровне БД и use-case.

🧠 Главная идея (коротко)
Не делай:

"раз в неделю пройтись по всем пользователям"

Сделай:

"раз в неделю создать batch-задачу, которую можно безопасно продолжать"

То есть scheduler только создаёт работу, а не выполняет её целиком.

✅ Правильная архитектура
1️⃣ Scheduler → создаёт Weekly Job
Раз в неделю:

WeeklyBonusScheduler
        ↓
create bonus_batch
В БД:

bonus_batches
-------------
id
chat_id
created_at
status        -- pending | processing | done
cursor_user_id  -- где остановились
Это ключ.

👉 Теперь задача стала возобновляемой.

2️⃣ Worker обрабатывает batch кусками
Отдельный worker (может быть тот же бот):

while True:
    batch = repo.get_unfinished_batch()

    users = repo.get_users_after(
        chat_id=batch.chat_id,
        after_id=batch.cursor_user_id,
        limit=100
    )

    for user in users:
        grant_bonus(batch, user)

    repo.update_cursor(batch, last_user_id)
3️⃣ Idempotency — решается Ledger’ом (у тебя он уже есть 👍)
Самое важное:

⚠️ начисление НЕ должно зависеть от того, запускался ли код раньше.

Добавь уникальность операции:

rating_ledger
-------------
id
user_id
operation_type   -- weekly_bonus
operation_key    -- batch_id
amount
UNIQUE(user_id, operation_type, operation_key)
Теперь:

INSERT INTO ledger (...)
ON CONFLICT DO NOTHING
Если бот упал → повторный запуск безопасен.

🔥 Что происходит при падении сервера
Сценарий:

обработали 340 пользователей

бот умер

restart

Worker:

batch.status = processing
cursor_user_id = 340
Он просто продолжит.

НИКАКИХ дублей.

🧩 Почему нельзя просто scheduler loop
Плохой вариант:

for chat in chats:
    for user in users:
        add_bonus()
Проблемы:

❌ нет checkpoint

❌ нельзя продолжить

❌ двойные начисления

❌ невозможно масштабировать

❌ long-running job (очень опасно)

✅ Transactional начисление (очень важно)
Начисление должно быть атомарным:

async def grant_bonus(batch, user):
    async with db.transaction():

        inserted = ledger_repo.insert_bonus(
            user_id=user.id,
            batch_id=batch.id
        )

        if not inserted:
            return  # уже начисляли

        rating_repo.increment(user.id, BONUS_AMOUNT)
Ledger = источник истины.

🚀 Дополнительный уровень надёжности (совет)
Добавь lock batch’а:

UPDATE bonus_batches
SET status='processing'
WHERE id = ?
AND status='pending'
RETURNING *
Это даст:

✅ только один worker обрабатывает batch
✅ можно запускать несколько инстансов бота

📦 Итоговая схема
fastscheduler
     ↓
creates batch row
     ↓
Worker loop
     ↓
process users in chunks
     ↓
ledger guarantees idempotency
     ↓
cursor guarantees resume
⭐ Золотое правило фоновых задач
Scheduler должен быть тупым.

Надёжность должна жить в:

database state

idempotent operations

resumable progress

💡 Бонус (очень рекомендую)
Ты фактически строишь mini job system.

Если дальше планируются:

weekly бонусы

monthly reset

пересчёт рейтинга

миграции данных

👉 сделай универсальную таблицу:

background_jobs
job_type
payload JSONB
cursor
status
И один worker.

Это резко упрощает жизнь через 3–6 месяцев.

Если хочешь — дальше можем сделать production-уровневый вариант, который используют в больших ботах:

👉 Inbox / Outbox + job leasing pattern
(это уже почти как Celery, но без Celery и идеально для Telegram-бота).


Вы сказали:
Давай еще раз. Мы одной джобой создаем в базе "задачи, которые нужно выполнить". А другой джобой разбираем очtредь и помeчаем обработанные как done.

Умный человек сказал:
Да 👍 — ты сейчас сформулировал правильную модель, только её важно чуть-чуть уточнить, чтобы она реально давала надёжность, а не просто «две джобы».

Я опишу чёткую схему, которая используется в production-ботах и фоновых системах.

✅ Общая идея (в одном предложении)
Одна задача планирует работу (producer),
другая — безопасно выполняет маленькие атомарные задачи (worker).

🧩 Архитектура
Weekly Scheduler (раз в неделю)
        ↓
создаёт task'и в БД
        ↓
Task Queue (таблица)
        ↓
Worker loop (постоянно)
        ↓
обрабатывает → done
1️⃣ Таблица очереди задач
Это главное место всей системы.

chat_tasks
----------
id
task_type        -- weekly_bonus
chat_id
user_id
payload JSONB
status           -- pending | processing | done | failed
attempts
available_at     -- когда можно брать
locked_at
worker_id
created_at
👉 Каждая строка = один пользователь = одно начисление.

Это ключевой момент.

НЕ:

обработать чат

А:

обработать пользователя.

2️⃣ Первая job — Producer (scheduler)
Раз в неделю:

async def create_weekly_bonus_tasks():
    chats = chat_repo.get_enabled()

    for chat in chats:
        users = user_repo.get_chat_users(chat.id)

        for user in users:
            task_repo.enqueue(
                task_type="weekly_bonus",
                chat_id=chat.id,
                user_id=user.id,
            )
⚠️ Она ничего не начисляет.

Она только создаёт работу.

💥 Важно — idempotency producer'а
Добавь уникальный ключ:

UNIQUE(task_type, chat_id, user_id, period_key)
где:

period_key = "2026-W09"
👉 если scheduler случайно запустится 2 раза — дублей не будет.

3️⃣ Вторая job — Worker
Это НЕ cron.

Это бесконечный loop:

while True:
    tasks = repo.claim_tasks(limit=50)

    for task in tasks:
        process(task)
Claim (самая важная часть)
UPDATE chat_tasks
SET status='processing',
    locked_at=NOW(),
    worker_id=:worker
WHERE id IN (
    SELECT id
    FROM chat_tasks
    WHERE status='pending'
      AND available_at <= NOW()
    ORDER BY id
    LIMIT 50
    FOR UPDATE SKIP LOCKED
)
RETURNING *
🔥 Это даёт:

несколько воркеров

отсутствие гонок

crash safety

4️⃣ Обработка задачи
async def process(task):
    try:
        await grant_bonus(task.user_id)

        repo.mark_done(task.id)

    except Exception:
        repo.retry(task.id)
5️⃣ Idempotency начисления (ОБЯЗАТЕЛЬНО)
Даже очередь не спасает без этого.

Ledger:

rating_ledger
--------------
user_id
operation_type = 'weekly_bonus'
operation_key  = period_key
UNIQUE(user_id, operation_type, operation_key)
INSERT ... ON CONFLICT DO NOTHING
🧨 Что происходит при падении бота
Сценарий:

worker взял 50 задач

обработал 17

сервер умер

После рестарта:

status = processing
locked_at = old
Recovery job:

UPDATE chat_tasks
SET status='pending',
    worker_id=NULL
WHERE status='processing'
AND locked_at < NOW() - INTERVAL '5 minutes'
👉 задачи возвращаются в очередь.

🧠 Почему это лучше batch cursor
Ты раньше видел вариант с cursor_user_id.

Он хороший, но:

Batch cursor    Task queue
одна длинная транзакция мелкие атомарные
сложно параллелить  легко масштабировать
падение = большой retry падение = потеря максимум 1 задачи
хуже observability  видно прогресс
⭐ Реально важное наблюдение
Ты фактически строишь:

Postgres-based job queue

И это идеально для Telegram бота.

Celery / Redis тут вообще не нужны.

🔥 Минимальный production набор
Нужно всего 3 процесса:

1. WeeklyScheduler   → создаёт tasks
2. Worker            → выполняет tasks
3. Recovery cleaner  → возвращает зависшие
🚀 Следующий шаг (очень советую)
Я могу показать тебе очень мощный паттерн, который резко упростит код:

👉 Generic Task Engine
(одна таблица + registry handlers как в telegram dispatcher)

Ты буквально получишь BackgroundDispatcher.

Хочешь — разберём?


Вы сказали:
Давай посмотрим

Умный человек сказал:
Окей 🙂
Сейчас покажу тебе тот самый момент, где фоновые задачи перестают быть “костылём” и превращаются в нормальную подсистему, очень похожую по духу на Telegram Dispatcher.

Ты уже почти к этому пришёл.

🧠 Идея: Background Dispatcher
Вместо:

weekly bonus job

cleanup job

recalculation job

migration job

мы делаем:

👉 один универсальный движок задач
+
👉 регистратор handlers

Ровно как:

telegram update → handler
только:

background task → handler
🧩 1. Таблица задач (универсальная)
background_tasks
----------------
id BIGSERIAL PK
task_type TEXT NOT NULL
payload JSONB NOT NULL

status TEXT NOT NULL DEFAULT 'pending'
attempts INT DEFAULT 0

available_at TIMESTAMP NOT NULL DEFAULT now()
locked_at TIMESTAMP
worker_id TEXT

created_at TIMESTAMP NOT NULL DEFAULT now()
Почему JSON payload — это нормально
Потому что task — это команда, а не сущность.

Пример:

{
  "chat_id": 10,
  "user_id": 55,
  "period": "2026-W09"
}
🧩 2. Task Handler интерфейс
class TaskHandler(Protocol):
    async def handle(self, task: BackgroundTask) -> None:
        ...
🧩 3. Registry (магия начинается тут)
class TaskRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, task_type: str, handler: TaskHandler):
        self._handlers[task_type] = handler

    def get(self, task_type: str) -> TaskHandler:
        return self._handlers[task_type]
Регистрация (как telegram handlers)
registry.register(
    "weekly_bonus",
    WeeklyBonusHandler(...)
)

registry.register(
    "recalculate_rating",
    RecalculateRatingHandler(...)
)
🧩 4. Worker = Background Dispatcher
Вот сердце системы:

class BackgroundWorker:

    async def run(self):
        while True:
            tasks = await repo.claim_tasks(limit=20)

            for task in tasks:
                handler = registry.get(task.task_type)

                try:
                    await handler.handle(task)
                    await repo.mark_done(task.id)

                except Exception:
                    await repo.retry(task.id)
🔥 Всё.

Ты только что сделал mini-Celery без Celery.

🧩 5. Weekly scheduler теперь тупой
async def weekly_scheduler():
    for chat in chats:
        for user in users:

            await task_repo.enqueue(
                task_type="weekly_bonus",
                payload={
                    "chat_id": chat.id,
                    "user_id": user.id,
                    "period": current_week(),
                }
            )
Scheduler ничего не знает о бизнес-логике.

🧩 6. Handler — чистый use-case
class WeeklyBonusHandler:

    async def handle(self, task: BackgroundTask):

        user_id = task.payload["user_id"]
        period = task.payload["period"]

        async with db.transaction():

            inserted = ledger.add_weekly_bonus(
                user_id=user_id,
                period=period
            )

            if not inserted:
                return

            rating.increment(user_id, 10)
✅ Что ты получил
💪 Надёжность
crash safe

restart safe

retry safe

idempotent

⚡ Масштабирование
Запускаешь:

worker x1
worker x5
worker x20
— всё работает без изменений.

👀 Observability
Можно сразу видеть:

SELECT task_type, status, count(*)
FROM background_tasks
GROUP BY 1,2;
🧼 Чистая архитектура
Теперь:

handler = use-case

worker = infrastructure

scheduler = orchestration

DDD прям радуется 🙂

🔥 Самый мощный бонус (что обычно осознают позже)
Ты теперь можешь делать:

✅ delayed tasks
✅ retries с backoff
✅ fan-out jobs
✅ chain jobs
✅ event-driven background processing

без новых технологий.

🚨 Но есть один ОЧЕНЬ важный next step
Сейчас система уже production-ready.

Но есть улучшение, которое делает её почти неубиваемой:

👉 lease / heartbeat pattern
(как Postgres queue в GitLab и Stripe)

Это решает проблему:

worker умер во время выполнения handler.

И делает recovery автоматическим.





