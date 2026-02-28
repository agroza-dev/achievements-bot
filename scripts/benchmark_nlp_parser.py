"""
Бенчмарк производительности NLPTransferParser.

Замеряет скорость обработки сообщений разной длины и сложности.
"""
import time

from core.application.transfers.nlp_transfer_parser import NLPTransferParser

# Тестовые сообщения
TEST_MESSAGES = [
    # Короткие (regex-уровень)
    "+10",
    "-5",
    "+ 100",

    # Средние (NLP-уровень)
    "Вася, лови 10 очков",
    "Передай Саше 20 баллов",
    "Списать 5 у Пети",
    "@vasya забери 15 очков",
    "Подари Кате 50 очков",

    # Длинные (должны игнорироваться)
    "Это очень длинное сообщение которое точно больше пятидесяти символов и не должно обрабатываться",
    "Привет всем! У нас сегодня отличное настроение, но это не трансфер",
]


def benchmark(
    parser: NLPTransferParser,
    messages: list[str],
    iterations: int = 1000
) -> dict:
    """
    Замеряет среднее время обработки одного сообщения.

    Args:
        parser: Экземпляр парсера
        messages: Список тестовых сообщений
        iterations: Количество итераций для каждого сообщения

    Returns:
        Словарь с результатами
    """
    results = {}

    for msg in messages:
        start = time.perf_counter()

        for _ in range(iterations):
            parser.parse(msg)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        # Проверяем результат парсинга
        result = parser.parse(msg)
        parsed = result is not None

        results[msg] = {
            "avg_time_ms": round(avg_time_ms, 4),
            "parsed": parsed,
            "length": len(msg),
        }

    return results


def print_report(results: dict) -> None:
    """Выводит отчёт в консоль."""
    print("\n" + "=" * 80)
    print("БЕНЧМАРК NLPTransferParser")
    print("=" * 80)
    print(f"{'Сообщение':<50} {'Длина':<6} {'Время (мс)':<12} {'Распознан':<10}")
    print("-" * 80)

    total_parsed = 0
    total_time = 0

    for msg, stats in results.items():
        msg_display = msg[:47] + "..." if len(msg) > 50 else msg
        print(
            f"{msg_display:<50} "
            f"{stats['length']:<6} "
            f"{stats['avg_time_ms']:<12.4f} "
            f"{'Да' if stats['parsed'] else 'Нет':<10}"
        )
        if stats['parsed']:
            total_parsed += 1
            total_time += stats['avg_time_ms']

    print("-" * 80)
    print(f"Всего сообщений: {len(results)}")
    print(f"Распознано трансферов: {total_parsed}")
    print(f"Среднее время (распознанные): {total_time / total_parsed:.4f} мс" if total_parsed > 0 else "")
    print("=" * 80)


if __name__ == "__main__":
    parser = NLPTransferParser()

    # Прогрев (чтобы загрузка модели не попала в замеры)
    for msg in TEST_MESSAGES:
        parser.parse(msg)

    # Бенчмарк
    results = benchmark(parser, TEST_MESSAGES, iterations=500)

    # Отчёт
    print_report(results)
