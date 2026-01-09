migrate:
	uv run alembic upgrade head

check-migrations:
	uv run alembic revision --autogenerate -m "check"