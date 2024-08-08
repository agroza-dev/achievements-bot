import os
import asyncio
from achievements_bot import db
from achievements_bot import config


async def apply_migrations():
    migrations_dir = config.MIGRATIONS_DIR
    await db.execute(
        '''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY
            )
        '''
    )

    applied_migrations = set(row['version'] for row in await db.fetch_all("SELECT version FROM schema_migrations"))

    migrations = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])

    for migration in migrations:
        if migration in applied_migrations:
            print(f"Skipping already applied migration: {migration}")
            continue

        with open(os.path.join(migrations_dir, migration), 'r') as f:
            sql = f.read()
            await db.execute(sql)
            await db.execute("INSERT INTO schema_migrations (version) VALUES (?)", (migration,))
            print(f"Applied migration: {migration}")

    db.close_async_db()

if __name__ == "__main__":
    asyncio.run(apply_migrations())

