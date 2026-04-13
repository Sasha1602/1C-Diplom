import asyncio
from datetime import datetime, timedelta, time  # Добавлен time
import aiomysql
import logging
from config import DB_CONFIG

db_pool = None

def set_db_pool(pool):
    global db_pool
    db_pool = pool

async def execute_query(query, params=None, fetch=False):
    async with db_pool.acquire() as conn:
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                if fetch:
                    return await cursor.fetchall()
                await conn.commit()
        except Exception as e:
            logging.error(f"Ошибка SQL: {query} | {e}")
            return None

# --- Функции для Квестов ---

async def get_quest_genres():
    query = "SELECT DISTINCT genre FROM quests"
    result = await execute_query(query, fetch=True)
    return [row[0] for row in result] if result else []

async def get_quests_by_genre(genre):
    query = "SELECT name, duration, price FROM quests WHERE genre = %s"
    return await execute_query(query, (genre,), fetch=True)

async def get_quest_details(quest_name):
    query = "SELECT duration, price FROM quests WHERE name = %s"
    result = await execute_query(query, (quest_name,), fetch=True)
    return result[0] if result else None

async def check_quest_availability(quest_name, date_str, time_str, duration_str):
    """
    Одиночная проверка (используется перед самой записью в БД для страховки)
    """
    try:
        if ":" not in time_str:
            time_str = f"{time_str}:00"
            
        date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        
        if isinstance(duration_str, timedelta):
            new_duration = duration_str
        else:
            parts = str(duration_str).split(':')
            new_duration = timedelta(hours=int(parts[0]), minutes=int(parts[1]))
            
        end_dt = start_dt + new_duration
        cleanup = timedelta(minutes=30)

        query = "SELECT time_start, time_end FROM bookings WHERE quest_name = %s AND date = %s"
        existing = await execute_query(query, (quest_name, date_obj), fetch=True)

        if not existing: 
            return True

        logging.info(f"Данные из БД: {existing}")
        for row in existing:
            if len(row) < 2:
                logging.error(f"Странная строка в БД: {row}")
                continue
            ex_start_delta, ex_end_delta = row[0], row[1]

        for ex_start_delta, ex_end_delta in existing:
            ex_start = datetime.combine(date_obj, (datetime.min + ex_start_delta).time())
            ex_end = datetime.combine(date_obj, (datetime.min + ex_end_delta).time())
            
            # Проверка пересечения с учетом перерыва в 30 минут
            if start_dt < (ex_end + cleanup) and end_dt > (ex_start - cleanup):
                return False
        return True
    except Exception as e:
        logging.error(f"Ошибка проверки доступности: {e}")
        return False

async def save_quest_booking(uid, client_name, quest_name, date_str, time_start):
    try:
        # 1. Получаем данные о квесте
        quest_data = await get_quest_details(quest_name)
        if not quest_data: 
            logging.error(f"Квест {quest_name} не найден")
            return False
        
        # 2. Парсим длительность (Duration)
        duration_raw = quest_data[0]
        if isinstance(duration_raw, str):
            parts = duration_raw.split(':')
            h_dur = int(parts[0]) if len(parts) > 0 else 0
            m_dur = int(parts[1]) if len(parts) > 1 else 0
            s_dur = int(parts[2]) if len(parts) > 2 else 0
            duration = timedelta(hours=h_dur, minutes=m_dur, seconds=s_dur)
        elif isinstance(duration_raw, timedelta):
            duration = duration_raw
        else:
            duration = timedelta(hours=int(duration_raw or 0))

        # 3. Парсим дату
        date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()

        # 4. Безопасно парсим время начала (time_start)
        time_parts = str(time_start).split(':')
        h_start = int(time_parts[0]) if len(time_parts) > 0 else 0
        m_start = int(time_parts[1]) if len(time_parts) > 1 else 0
        start_time_obj = time(h_start, m_start)
        
        # 5. Считаем время окончания
        start_dt = datetime.combine(date_obj, start_time_obj)
        end_dt = start_dt + duration
        
        # 6. Форматируем для MySQL
        t_start_sql = start_dt.strftime("%H:%M:%S")
        t_end_sql = end_dt.strftime("%H:%M:%S")

        query = """
            INSERT INTO bookings (client_name, quest_name, date, time_start, time_end, processed)
            VALUES (%s, %s, %s, %s, %s, 0)
        """
        params = (client_name, quest_name, date_obj, t_start_sql, t_end_sql)
        await execute_query(query, params)
        return True
        
    except Exception as e:
        logging.error(f"Ошибка сохранения: {e}")
        return False
# --- Функции Пользователей ---

async def register_user(uid, phone, nickname):
    query = """
        INSERT INTO Users (user_id, phone, nickname, registration_date) 
        VALUES (%s, %s, %s, NOW()) 
        ON DUPLICATE KEY UPDATE phone=%s, nickname=%s
    """
    await execute_query(query, (uid, phone, nickname, phone, nickname))

async def get_user_from_db(uid):
    query = "SELECT nickname, phone FROM Users WHERE user_id = %s"
    result = await execute_query(query, (uid,), fetch=True)
    return {"nickname": result[0][0], "phone": result[0][1]} if result else None

async def is_user_banned(uid):
    query = "SELECT is_banned FROM Users WHERE user_id = %s"
    result = await execute_query(query, (uid,), fetch=True)
    return result[0][0] if result else False

# --- Массовая проверка (Оптимизация) ---

async def get_booked_slots_bulk(quest_name, dates_list, all_times, duration_str):
    if not dates_list:
        return {}

    try:
        d_str = str(duration_str)
        if ':' in d_str:
            parts = d_str.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
        else:
            h = int(d_str) if d_str.isdigit() else 1
            m = 0
        new_quest_duration = timedelta(hours=h, minutes=m)
    except Exception as e:
        logging.error(f"Ошибка парсинга длительности {duration_str}: {e}")
        new_quest_duration = timedelta(hours=1)

    sql_dates = [datetime.strptime(d, "%d.%m.%Y").date() for d in dates_list]
    format_strings = ','.join(['%s'] * len(sql_dates))
    query = f"""
        SELECT date, time_start, time_end 
        FROM bookings 
        WHERE quest_name = %s AND date IN ({format_strings})
    """
    params = [quest_name] + sql_dates
    rows = await execute_query(query, params, fetch=True)
    
    cleanup_time = timedelta(minutes=30)
    booked_data = {}

    for d_str in dates_list:
        booked_data[d_str] = []
        current_date_obj = datetime.strptime(d_str, "%d.%m.%Y").date()
        day_rows = [r for r in rows if r[0] == current_date_obj] if rows else []

        for slot_time_str in all_times:
            slot_h, slot_m = map(int, slot_time_str.split(':'))
            new_start = datetime.combine(current_date_obj, time(slot_h, slot_m))
            new_end = new_start + new_quest_duration

            is_busy = False
            for _, b_start_delta, b_end_delta in day_rows:
                # b_start_delta и b_end_delta приходят как timedelta из aiomysql
                ex_start = datetime.combine(current_date_obj, (datetime.min + b_start_delta).time())
                ex_end = datetime.combine(current_date_obj, (datetime.min + b_end_delta).time())

                if ex_start.time() < time(8, 0): 
                    continue

                if new_start < (ex_end + cleanup_time) and new_end > (ex_start - cleanup_time):
                    is_busy = True
                    break
            
            if is_busy:
                booked_data[d_str].append(slot_time_str)
            
    return booked_data

# --- Функции для отмены бронирования ---

async def get_user_active_bookings(client_name):
    """Получает все будущие и не отмененные бронирования пользователя"""
    # Ищем брони от сегодняшнего дня, где processed не равно 2 (отмена)
    query = """
        SELECT id, quest_name, date, time_start 
        FROM bookings 
        WHERE client_name = %s AND date >= CURDATE() AND processed != 2
    """
    return await execute_query(query, (client_name,), fetch=True)

async def cancel_booking_in_db(booking_id):
    # ЛОГ: проверяем, что ID пришел и он правильного типа (int)
    logging.info(f"Вызов cancel_booking_in_db для ID: {booking_id} (тип: {type(booking_id)})")
    
    query = "UPDATE bookings SET processed = 2 WHERE id = %s"
    res = await execute_query(query, (booking_id,))
    
    # ЛОГ: проверяем, что вернула execute_query
    logging.info(f"Результат выполнения execute_query для отмены: {res}")
    return res

async def execute_query(query, params=None, fetch=False):
    async with db_pool.acquire() as conn:
        try:
            async with conn.cursor() as cursor:
                # ЛОГ: смотрим, какой запрос реально уходит в MySQL
                logging.info(f"SQL Execute: {query} | Params: {params}") 
                
                await cursor.execute(query, params)
                if fetch:
                    result = await cursor.fetchall()
                    logging.info(f"SQL Fetch Result: {len(result)} rows")
                    return result
                
                # Для UPDATE/INSERT возвращаем True явно
                logging.info("SQL Update/Insert - Success")
                return True 
        except Exception as e:
            # ЛОГ: ловим саму ошибку от MySQL
            logging.error(f"КРИТИЧЕСКАЯ ОШИБКА SQL: {e}")
            return None