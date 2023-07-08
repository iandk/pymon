async def send_telegram_message(message, chat_id, bot_token):
    try:
        bot = TelegramBot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
