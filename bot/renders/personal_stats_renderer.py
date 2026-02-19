from core.dto.personal_stats_dto import PersonalStatsDTO


def render_personal_stats(dto: PersonalStatsDTO) -> str:
    lines: list[str] = ["📊 *Твоя статистика*", f"💰 Баланс: *{dto.balance}*", ""]

    if not dto.entries:
        lines.append("Пока нет операций.")
        return "\n".join(lines)

    for entry in dto.entries:
        sign = "➕" if entry.amount > 0 else "➖"
        amount = abs(entry.amount)

        date = entry.created_at.strftime("%d.%m %H:%M")

        lines.append(
            f"{date} {sign} {amount}"
        )

    return "\n".join(lines)
