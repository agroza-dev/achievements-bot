import logging
from collections.abc import Callable

from core.application.transfers.transfer_parser import TransferParser
from core.application.transfers.transfer_result import TransferResult, TransferStatus
from core.application.transfers.transfer_service import TransferService
from core.domain.transfers.errors import RecipientNotFoundError
from core.domain.transfers.transfer_policy import TransferPolicy
from core.dto.transfer_dto import TransferCommandDTO
from core.dto.user_dto import UserDTO
from core.infrastructure.database import DbUnitOfWork
from core.infrastructure.repositories.chat_message_repository import DbChatMessageRepository
from core.infrastructure.repositories.rating_ledger_repository import DbRatingLedgerRepository
from core.infrastructure.repositories.rating_repository import DbRatingRepository
from core.infrastructure.repositories.user_repository import UserRepository

UowFactory = Callable[[], DbUnitOfWork]

logger = logging.getLogger(__name__)


async def _resolve_recipient_user(
        *,
    command: TransferCommandDTO,
    user_repo: UserRepository,
    message_repo: DbChatMessageRepository,
) -> UserDTO:
    if command.reply_to_message_id:
        message = await message_repo.get_by_tg_id(
            chat_id=command.chat_id,
            tg_message_id=command.reply_to_message_id,
        )
        if not message:
            raise RecipientNotFoundError("Не удалось найти reply сообщение")

        return await user_repo.get_by_internal_id(message.author_user_id)

    if not command.mentioned_usernames:
        raise RecipientNotFoundError("Не удалось обозначить получателя в dummy трансфере")


    if len(command.mentioned_usernames) > 1:
        raise RecipientNotFoundError("Указан больше одного получателя трансфера (не поддерживается)")

    user_name = command.mentioned_usernames[0].replace("@", '')
    logger.debug(f"Trying to resolve user {user_name}")
    user = await user_repo.get_by_username(
        chat_id=command.chat_id,
        username=user_name,
    )
    logger.debug(f"Resolved user {user}")
    if not user:
        raise RecipientNotFoundError(f"Не удалось найти пользователя с ником {user_name}")

    return user


class TransferPointsUseCase:
    def __init__(
        self,
        uow_factory: UowFactory,
        policy: TransferPolicy,
    ):
        self.uow_factory = uow_factory
        self.policy = policy

    async def execute(self, command: TransferCommandDTO) -> TransferResult:
        # 1. Парсим намерение на трансфер очков
        try:
            intent = TransferParser.parse(command.raw_text)
            logger.debug("Parsed intent: %s", intent)
            if not intent:
                logger.debug("Parser has not found transfer ident for message: %s", command.raw_text)
                return TransferResult(status=TransferStatus.NOT_FOUND)


            if intent.amount <= 0:
                logger.debug("Transfer amount has to be greater than 0")
                return TransferResult(status=TransferStatus.FORBIDDEN, message="Трансфер не должен быть нулевым")

            if intent.amount > self.policy.get_max_transfer_amount():
                logger.debug("Transfer amount has to be greater than 0")


            logger.debug("Start transfer for intent: %s", intent)
            async with self.uow_factory() as uow:
                user_repo: UserRepository = uow.get_repo(UserRepository)
                message_repo = uow.get_repo(DbChatMessageRepository)
                rating_repo = uow.get_repo(DbRatingRepository)
                ledger_repo = uow.get_repo(DbRatingLedgerRepository)

                recipient_user = await _resolve_recipient_user(
                    command=command,
                    user_repo=user_repo,
                    message_repo=message_repo,
                )
                logger.debug("Recipient user: %s", recipient_user)

                if recipient_user.id == command.initiator_user_id:
                    logger.debug("Transfer initiator user_id is same as initiator_user_id")
                    return TransferResult(status=TransferStatus.FORBIDDEN, message="Нельзя переводить самому себе")

                tax = self.policy.tax(intent.amount, intent.direction)
                # инициатор всегда платит
                initiator_action_cost = intent.amount + tax
                initiator_current_balance = await rating_repo.get_current(command.chat_id, command.initiator_user_id)

                if initiator_action_cost > initiator_current_balance:
                    logger.debug("Transfer initiator has not insufficient balance")
                    return TransferResult(status=TransferStatus.INSUFFICIENT_FUNDS)


                logger.debug("Try to transfer")
                # 3. Применяем трансфер
                transfer_service = TransferService(
                    rating_repo=rating_repo,
                    ledger_repo=ledger_repo,
                    policy=self.policy,
                )

                await transfer_service.apply(
                    chat_id=command.chat_id,
                    initiator_user_id=command.initiator_user_id,
                    recipient_user_id=recipient_user.id,
                    intent=intent,
                )
            return TransferResult(status=TransferStatus.SUCCESS)
        except RecipientNotFoundError:
            logger.error("Error for command %s", command, exc_info=True)
            return TransferResult(status=TransferStatus.QUIET_STOP)

        except Exception:
            logger.exception("Unexpected error during transfer for command %s", command, exc_info=True)
            raise
