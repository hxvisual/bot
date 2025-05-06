import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold # Helper для форматирования текста

from dotenv import load_dotenv

# Загружаем переменные окружения (включая токен) из файла .env
load_dotenv()

# Получаем токен бота из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.critical("Не найден BOT_TOKEN в переменных окружения!")
    sys.exit(1) # Выход, если токен не найден

# Инициализация бота и диспетчера
# Используем parse_mode=ParseMode.HTML для возможности форматирования сообщений
dp = Dispatcher()
bot = Bot(TOKEN)

# --- Обработчики команд и сообщений ---

# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Этот обработчик вызывается, когда пользователь отправляет команду /start
    """
    user_name = message.from_user.full_name
    logging.info(f"Пользователь {user_name} (ID: {message.from_user.id}) запустил бота.")
    await message.answer(f"Привет, {hbold(user_name)}! хуила!")
    await message.answer("Я простой эхо-бот на aiogram 3. Отправь мне сообщение, и я его повторю.")

# Обработчик для всех остальных текстовых сообщений (эхо)
@dp.message()
async def echo_handler(message: types.Message) -> None:
    """
    Этот обработчик будет повторять любое полученное текстовое сообщение.
    """
    try:
        # Отправляем копию полученного сообщения обратно пользователю
        # send_copy полезен для сохранения форматирования, стикеров и т.д.
        # await message.send_copy(chat_id=message.chat.id)

        # Или просто повторяем текст
        logging.info(f"Получено сообщение от {message.from_user.full_name}: {message.text}")
        await message.answer(f"Вы написали: {message.text}")

    except TypeError:
        # В случае, если сообщение не является текстом (например, стикер)
        await message.answer("Интересно! Но я умею повторять только текст.")
    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await message.answer("Произошла ошибка при обработке вашего сообщения.")


# --- Запуск бота ---

async def main() -> None:
    # Запускаем получение обновлений от Telegram
    # skip_updates=True пропускает накопленные сообщения, пока бот был оффлайн
    logging.info("Запуск бота...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    # Настройка логирования для вывода информации в консоль
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен вручную.")
    except Exception as e:
        logging.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)