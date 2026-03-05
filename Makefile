migrate:
	uv run alembic upgrade head

check-migrations:
	uv run alembic revision --autogenerate -m "check"

# Запуск бота
run:
	uv run python -m bot.main

# Запуск бота с встроенным Dashboard (рекомендуется для разработки)
run-with-dashboard:
	uv run python scripts/run_bot_with_dashboard.py

# Запуск Dashboard планировщика (отдельный процесс)
dashboard:
	uv run python scripts/run_scheduler_dashboard.py

# Разовое зачисление (award)
# Пример: make award chat-id=-1001234567890 user-id=123456789 amount=500 comment="Баг-баунти"
award:
	uv run python scripts/award_one_time.py --chat-id $(chat-id) --user-id $(user-id) --amount $(amount) --comment "$(comment)"

# Массовое зачисление из JSON
# Пример: make award-bulk file=awards.json
award-bulk:
	uv run python scripts/award_one_time.py --bulk $(file)

# Запуск тестов
test:
	uv run pytest tests/

# Запуск тестов с покрытием
test-cov:
	uv run pytest --cov=core --cov-report=term-missing tests/

# Линтер
lint:
	uv run ruff check .

# Авто-фикс линтера
lint-fix:
	uv run ruff check --fix .
