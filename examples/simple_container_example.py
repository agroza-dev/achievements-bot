"""
Простой пример DI контейнера для понимания концепции

Этот файл показывает, как работает DI контейнер на простом примере.
"""

from typing import Callable


# ============================================
# ИМИТАЦИЯ РЕАЛЬНЫХ КЛАССОВ (упрощенные версии)
# ============================================

class DatabasePool:
    """Имитация пула подключений к БД"""
    def __init__(self):
        self.is_connected = True
        print("  [DB] Пул подключений создан")

class UnitOfWork:
    """Имитация Unit of Work"""
    def __init__(self, pool: DatabasePool):
        self.pool = pool
        print("  [UoW] UnitOfWork создан с пулом")
    
    def __enter__(self):
        print("  [UoW] Транзакция начата")
        return self
    
    def __exit__(self, *args):
        print("  [UoW] Транзакция завершена")


class MessagePolicy:
    """Политика для сообщений"""
    def __init__(self):
        self.name = "DefaultMessagePolicy"
        print(f"  [Policy] {self.name} создана")
    
    def can_process(self, message):
        return True


class ProcessMessageUseCase:
    """Use Case для обработки сообщений"""
    def __init__(self, uow_factory: Callable, policy: MessagePolicy):
        self.uow_factory = uow_factory
        self.policy = policy
        print(f"  [UseCase] ProcessMessageUseCase создан с policy={policy.name}")
    
    def execute(self, message: str):
        print(f"\n📨 Обработка сообщения: {message}")
        with self.uow_factory() as uow:
            if self.policy.can_process(message):
                print(f"✅ Сообщение обработано")


# ============================================
# БЕЗ DI (ТЕКУЩИЙ ПОДХОД - ПРОБЛЕМЫ)
# ============================================

print("=" * 60)
print("❌ БЕЗ DI КОНТЕЙНЕРА (как сейчас)")
print("=" * 60)

# Глобальный объект (проблема!)
global_db_pool = DatabasePool()

def handler_without_di(message: str):
    """Handler БЕЗ DI - создает зависимости напрямую"""
    print(f"\n🔹 Handler обрабатывает: {message}")
    
    # ❌ Проблема 1: Используем глобальный объект
    # ❌ Проблема 2: Создаем новые объекты каждый раз
    # ❌ Проблема 3: Дублирование кода в каждом handler
    
    uow_factory = lambda: UnitOfWork(global_db_pool)
    policy = MessagePolicy()  # Новый объект каждый раз!
    use_case = ProcessMessageUseCase(uow_factory, policy)
    
    use_case.execute(message)


# Использование (плохо)
handler_without_di("Привет!")
handler_without_di("Как дела?")
print("\n⚠️ Проблемы:")
print("  - MessagePolicy создается 2 раза (неэффективно)")
print("  - Используется глобальный db_pool (сложно тестировать)")
print("  - Дублирование логики создания")


# ============================================
# С DI КОНТЕЙНЕРОМ (РЕШЕНИЕ)
# ============================================

print("\n" + "=" * 60)
print("✅ С DI КОНТЕЙНЕРОМ (как должно быть)")
print("=" * 60)


class SimpleContainer:
    """Простой DI контейнер"""
    
    def __init__(self, db_pool: DatabasePool):
        self._db_pool = db_pool
        self._message_policy = None  # Будет создана один раз (singleton)
        print("\n[Container] Контейнер создан")
    
    def get_uow_factory(self) -> Callable:
        """Фабрика для UnitOfWork"""
        def factory():
            return UnitOfWork(self._db_pool)
        return factory
    
    def get_message_policy(self) -> MessagePolicy:
        """Получить политику (singleton - создается один раз)"""
        if self._message_policy is None:
            self._message_policy = MessagePolicy()
        return self._message_policy
    
    def get_process_message_use_case(self) -> ProcessMessageUseCase:
        """Создать use case с автоматической подстановкой зависимостей"""
        return ProcessMessageUseCase(
            uow_factory=self.get_uow_factory(),
            policy=self.get_message_policy(),
        )


# Создаем контейнер один раз (в main.py при старте приложения)
db_pool = DatabasePool()
container = SimpleContainer(db_pool)


def handler_with_di(message: str, container: SimpleContainer):
    """Handler С DI - получает зависимости из контейнера"""
    print(f"\n🔹 Handler обрабатывает: {message}")
    
    # ✅ Решение: Просто получаем use case из контейнера
    use_case = container.get_process_message_use_case()
    use_case.execute(message)


# Использование (хорошо)
handler_with_di("Привет!", container)
handler_with_di("Как дела?", container)

print("\n✅ Преимущества:")
print("  - MessagePolicy создана 1 раз (singleton)")
print("  - Контейнер можно легко подменить для тестов")
print("  - Нет дублирования кода")
print("  - Зависимости управляются централизованно")


# ============================================
# ДЕМОНСТРАЦИЯ: ПРЕИМУЩЕСТВА ДЛЯ ТЕСТОВ
# ============================================

print("\n" + "=" * 60)
print("🧪 ДЕМОНСТРАЦИЯ: Легкое тестирование")
print("=" * 60)


class MockDatabasePool:
    """Mock для тестов"""
    def __init__(self):
        self.is_connected = False
        print("  [Mock DB] Mock пул создан (для тестов)")


class TestMessagePolicy:
    """Тестовая политика"""
    def __init__(self):
        self.name = "TestMessagePolicy"
        print(f"  [Test Policy] {self.name} создана")
    
    def can_process(self, message):
        return message != "spam"


print("\n📝 Тест: Создаем тестовый контейнер с моками")
test_db_pool = MockDatabasePool()
test_container = SimpleContainer(test_db_pool)
# Переопределяем политику для тестов (можно добавить метод set_policy)
test_container._message_policy = TestMessagePolicy()

print("\n🧪 Запускаем тест")
handler_with_di("valid message", test_container)
handler_with_di("spam", test_container)  # Должно быть отклонено тестовой политикой

print("\n✅ С DI легко создавать тестовые контейнеры с моками!")
print("   БЕЗ DI пришлось бы мокировать глобальный объект - сложнее")


# ============================================
# ДЕМОНСТРАЦИЯ: Легкая замена реализации
# ============================================

print("\n" + "=" * 60)
print("🔄 ДЕМОНСТРАЦИЯ: Легкая замена реализации")
print("=" * 60)


class StrictMessagePolicy:
    """Строгая политика (новая реализация)"""
    def __init__(self):
        self.name = "StrictMessagePolicy"
        print(f"  [New Policy] {self.name} создана")
    
    def can_process(self, message):
        return len(message) > 10


print("\n📝 Меняем политику в контейнере (в одном месте!)")
production_container = SimpleContainer(DatabasePool())
production_container._message_policy = StrictMessagePolicy()

print("\n🔄 Используем с новой политикой")
handler_with_di("short", production_container)  # Отклонено (слишком короткое)
handler_with_di("very long message text", production_container)  # Принято

print("\n✅ Чтобы поменять политику БЕЗ DI - нужно править все handlers!")
print("   С DI - меняем только контейнер ✅")


# ============================================
# ИТОГОВОЕ СРАВНЕНИЕ
# ============================================

print("\n" + "=" * 60)
print("📊 ИТОГОВОЕ СРАВНЕНИЕ")
print("=" * 60)

comparison = """
┌─────────────────────────────────────────────────────────────┐
│ Критерий              │ БЕЗ DI        │ С DI               │
├─────────────────────────────────────────────────────────────┤
│ Тестируемость         │ ❌ Сложно     │ ✅ Легко           │
│ Дублирование кода     │ ❌ Много      │ ✅ Нет             │
│ Замена реализации     │ ❌ Везде      │ ✅ В одном месте   │
│ Производительность    │ ❌ Новые      │ ✅ Переиспользование│
│ Поддерживаемость      │ ⚠️ Средняя    │ ✅ Высокая         │
└─────────────────────────────────────────────────────────────┘
"""

print(comparison)
print("\n💡 Вывод: DI контейнер упрощает код и делает его более тестируемым!")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Запустите этот файл: python examples/simple_container_example.py")
    print("=" * 60)

