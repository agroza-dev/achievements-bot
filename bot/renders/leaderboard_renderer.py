from core.dto.leaderboard_row_dto import LeaderboardRowDTO


def render_leaderboard(rows: list[LeaderboardRowDTO]) -> str:
    """
    Рендеринг таблицы лидеров.

    Формат:
    🏆 Таблица лидеров
    1. @username — 1000
    2. @user2 — 950
    3. @user3 — 800
    """
    if not rows:
        return "🏆 Таблица лидеров\n\nПока нет участников."

    lines = ["🏆 Таблица лидеров", ""]

    for i, row in enumerate(rows, 1):
        username = row.user.username
        user_display = f"{username}" if username else row.user.first_name or "Пользователь"

        lines.append(f"{i}. {user_display} — {row.rating}")

    return "\n".join(lines)
