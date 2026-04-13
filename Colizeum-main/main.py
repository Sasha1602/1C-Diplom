import asyncio
import logging
from aiogram import Dispatcher
from aiomysql import create_pool
from bot_instance import bot
from bot_handlers_FIXED import router
from config import DB_CONFIG, TOKEN
from database import set_db_pool

async def main():
    # 1. Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # 2. Создаем пул соединений к MySQL
    try:
        pool = await create_pool(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            db=DB_CONFIG['db'],
            autocommit=True, # Важно для автоматического сохранения данных
            minsize=1,
            maxsize=10
        )
        # Передаем созданный пул в модуль database.py
        set_db_pool(pool)
        logging.info("Успешное подключение к базе данных MySQL")
    except Exception as e:
        logging.error(f"Критическая ошибка при подключении к БД: {e}")
        return

    # 3. Инициализация диспетчера
    dp = Dispatcher()
    dp.include_router(router)

    # 4. Запуск бота
    try:
        await dp.start_polling(bot)
    finally:
        # Закрываем пул при выключении бота
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())