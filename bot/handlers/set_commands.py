from telegram import BotCommand, BotCommandScopeChat
from telegram.ext import Application


async def set_user_specific_commands(app: Application, user_id: int) -> None:
    bot = app.bot


    commands = [
        BotCommand(command="start", description="Запустить/Перезапустить бота"),
    ]

    await bot.set_my_commands(
        commands=commands,
        scope=BotCommandScopeChat(chat_id=user_id)
    )


async def set_commands(app: Application) -> None:
    users = [
        763524027,  #madBorodach
        435317713,  #agroza.dev
    ]

    for user in users:
        await set_user_specific_commands(app, user)
