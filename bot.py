import logging
import os
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('broadcast')

# Получаем токен бота из переменной окружения
# Это безопаснее, чем хранить токен прямо в коде
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    log.critical("Не найден токен бота. Установите переменную окружения BOT_TOKEN.")
    exit()

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Обработчик команды /start
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    Этот обработчик будет вызываться при отправке команды `/start` или `/help`.
    """
    await message.reply(
        "Привет!\nЯ простой эхо-бот на aiogram.\n"
        "Отправь мне любое сообщение, и я его повторю."
    )

# Обработчик для всех остальных текстовых сообщений (эхо)
@dp.message_handler(content_types=types.ContentType.TEXT)
async def echo_message(message: types.Message):
    """
    Этот обработчик будет повторять любое текстовое сообщение пользователя.
    """
    await message.answer(f"Ты написал: {message.text}")

# Обработчик для нетекстовых сообщений (для примера)
@dp.message_handler(content_types=types.ContentType.ANY)
async def unknown_message(message: types.Message):
    """
    Обрабатывает любые сообщения, кроме текста и команд выше.
    """
    await message.answer("Я умею работать только с текстовыми сообщениями.")

async def on_startup(dp):
    log.warning('Бот запущен...')
    await bot.send_message(ADMIN_ID, "Бот запущен!") # Замените ADMIN_ID на ваш ID

async def on_shutdown(dp):
    log.warning('Бот остановлен...')
    await bot.send_message(ADMIN_ID, "Бот остановлен!")
    await bot.close()

if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)