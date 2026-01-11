import logging
import pprint

from telegram import Update
from telegram.ext import ContextTypes

from bot.ptb_models.reactions import ReactionData
from core.container import Container
from core.dto.bot_context import BotContextDTO

logger = logging.getLogger(__name__)


async def reaction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработать реакцию на сообщение."""
    ctx: BotContextDTO = context.bot_data.get("ctx")
    print(ctx)
    if not ctx:
        logger.error("Bot context not found in reaction handler")
        return

    try:
        # Получаем контейнер из application context
        container: Container = context.bot_data.get('container')
        if not container:
            raise RuntimeError("Container not initialized. Ensure container is set in bot_data during startup.")

        # Получаем данные о реакции из update
        reaction_data = ReactionData.from_update(update, context)

        # Преобразуем реакции в список строк (эмодзи)
        old_reactions = [r.emoji for r in reaction_data.old_reactions]
        new_reactions = [r.emoji for r in reaction_data.new_reactions]

        # Получаем use case из контейнера
        use_case = container.get_process_reaction_use_case()
        pprint.pprint(reaction_data)
        # Передаем обработку в use case
        await use_case.execute(
            ctx=ctx,
            tg_chat_id=reaction_data.chat_id,
            tg_message_id=reaction_data.message_id,
            old_reactions=old_reactions,
            new_reactions=new_reactions,
        )

    except Exception as e:
        logger.error(
            f"Error processing reaction: {e}",
            exc_info=True
        )
