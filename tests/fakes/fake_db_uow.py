
from core.infrastructure.repositories.chat_repository import ChatRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.user_repository import UserRepository
from tests.fakes.fake_rating_ledger_repo import FakeRatingLedgerRepo


class FakeDbUnitOfWork:
    """Фейковый UnitOfWork для тестов."""

    def __init__(
        self,
        *,
        rating_ledger_repo: FakeRatingLedgerRepo,
        user_id_map: dict[int, int] | None = None,
        chat_id_map: dict[int, int] | None = None,
    ):
        self._rating_ledger_repo = rating_ledger_repo
        self._user_id_map = user_id_map or {}
        self._chat_id_map = chat_id_map or {}
        self._repos = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def get_repo(self, repo_cls):
        if repo_cls not in self._repos:
            if repo_cls == DbRatingLedgerRepository:
                self._repos[repo_cls] = self._rating_ledger_repo
            elif repo_cls == UserRepository:
                self._repos[repo_cls] = FakeUserRepository(self._user_id_map)
            elif repo_cls == ChatRepository:
                self._repos[repo_cls] = FakeChatRepository(self._chat_id_map)
            else:
                raise ValueError(f"Unknown repository: {repo_cls}")
        return self._repos[repo_cls]


class FakeUserRepository:
    """Фейковый UserRepository для тестов."""

    def __init__(self, user_id_map: dict[int, int] | None = None):
        self._user_id_map = user_id_map or {1: 1}

    async def get_id_by_tg_id(self, tg_user_id: int) -> int:
        return self._user_id_map.get(tg_user_id, 1)

    async def get_by_tg_id(self, tg_user_id: int):
        """Возвращает фейковый UserDTO для тестов."""
        return type("UserDTO", (), {
            "id": 1,
            "tg_id": tg_user_id,
            "username": "test_user",
            "first_name": "Test",
            "last_name": None,
            "is_bot": False,
            "timezone": "UTC",
            "created_at": None,
            "updated_at": None,
        })()


class FakeChatRepository:
    """Фейковый ChatRepository для тестов."""

    def __init__(self, chat_id_map: dict[int, int] | None = None):
        self._chat_id_map = chat_id_map or {1: type("ChatDTO", (), {"id": 1, "title": "Test Chat"})()}

    async def get_by_tg_id(self, tg_chat_id: int | None):
        if tg_chat_id is None:
            return type("ChatDTO", (), {"id": None, "title": None})()
        return self._chat_id_map.get(tg_chat_id, type("ChatDTO", (), {"id": 1, "title": "Test Chat"})())
