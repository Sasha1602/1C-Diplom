from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from rules import RULES_PARTS
from database import get_user_active_bookings, cancel_booking_in_db
from bot_instance import bot
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from database import (
    execute_query,
    get_quest_genres,
    get_quests_by_genre,
    check_quest_availability,
    save_quest_booking,
    register_user,
    get_user_from_db,
    is_user_banned
)
from utils import validate_phone, get_min_max_dates
import logging

router = Router()

# Состояния регистрации
class Registration(StatesGroup):
    full_name = State() # Было nickname
    phone = State()

# Состояния бронирования квеста
class QuestBooking(StatesGroup):
    choosing_genre = State()
    choosing_quest = State()
    choosing_date = State()
    choosing_time = State()
    confirming_booking = State()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    logging.info(f" Пользователь {message.from_user.id} нажал /start")
    await state.clear()
    
    # Проверяем бан
    if await is_user_banned(message.from_user.id):
        await message.answer("🚫 Ваш доступ к боту заблокирован.")
        return

    user = await get_user_from_db(message.from_user.id)
    
    if not user:
        await message.answer("👋 Добро пожаловать! Для бронирования квеста необходимо зарегистрироваться.\n\nВведите ваше **ФИО**:")
        await state.set_state(Registration.full_name)
    else:
        logging.info(f" Пользователь {user['nickname']} авторизован.")
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Выбрать квест", callback_data="start_quest_booking")],
            [InlineKeyboardButton(text="📅 Мои бронирования", callback_data="my_bookings")], # НОВАЯ КНОПКА
            [InlineKeyboardButton(text="📜 Правила", callback_data="view_rules")]
        ])
        await message.answer(f"Рады видеть вас снова, {user['nickname']}! Что хотите сделать?", reply_markup=markup)

# --- БЛОК РЕГИСТРАЦИИ (ФИО + Кнопка телефона) ---

@router.message(Registration.full_name)
async def reg_full_name(message: Message, state: FSMContext):
    logging.info(f" Получено ФИО: {message.text} от ID: {message.from_user.id}")
    await state.update_data(full_name=message.text) # Сохраняем ФИО
    
    # Создаем клавиатуру с кнопкой запроса контакта
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        f"Приятно познакомиться, {message.text}! Теперь нажмите на кнопку ниже, чтобы поделиться номером телефона:",
        reply_markup=keyboard
    )
    await state.set_state(Registration.phone)

@router.message(Registration.phone, F.contact) # Ждем именно объект контакта
async def reg_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    data = await state.get_data()
    full_name = data.get('full_name')
    
    logging.info(f" Получен контакт: {phone} для {full_name}")
    
    try:
        # Используем существующую функцию, передавая ФИО вместо никнейма
        await register_user(message.from_user.id, phone, full_name)
        
        # Убираем кнопку запроса телефона
        await message.answer("✅ Регистрация завершена!", reply_markup=ReplyKeyboardRemove())
        
        await message.answer(
            f"Теперь вы можете забронировать игру.", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎭 Перейти к квестам", callback_data="start_quest_booking")]
            ])
        )
        await state.clear()
    except Exception as e:
        logging.error(f" Ошибка БД: {e}")
        await message.answer("Ошибка при сохранении. Попробуйте позже.", reply_markup=ReplyKeyboardRemove())

# --- БРОНИРОВАНИЕ КВЕСТОВ ---

@router.callback_query(F.data == "start_quest_booking")
async def start_booking(call: CallbackQuery, state: FSMContext):
    await state.clear()
    genres = await get_quest_genres()
    if not genres:
        await call.message.answer("К сожалению, список жанров пока пуст.")
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for genre in genres:
        markup.inline_keyboard.append([InlineKeyboardButton(text=f"📂 {genre}", callback_data=f"genre:{genre}")])
    
    await call.message.edit_text("Выберите жанр квеста:", reply_markup=markup)
    await state.set_state(QuestBooking.choosing_genre)

@router.callback_query(F.data.startswith("genre:"), QuestBooking.choosing_genre)
async def choose_quest(call: CallbackQuery, state: FSMContext):
    genre = call.data.split(":")[1]
    
    # ДОБАВЬ ЭТУ СТРОКУ, чтобы бот запомнил жанр для кнопки "Назад"
    await state.update_data(current_genre=genre) 
    
    quests = await get_quests_by_genre(genre)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for name, duration, price in quests:
        btn_text = f"{name} ({price}₽ | {str(duration)[:5]})"
        markup.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"quest:{name}:{duration}")])
    
    # ИСПРАВЛЕНИЕ ТУТ:
    # Вместо "start_quest_booking" (который ведет к жанрам)
    # мы отправляем пользователя в "main_menu" (нужно будет добавить такой хендлер) 
    # или просто на удаление сообщения и вызов старта.
    markup.inline_keyboard.append([InlineKeyboardButton(text="⬅ В главное меню", callback_data="to_main_menu")])
    
    await call.message.edit_text(f"Жанр: {genre}. Выберите квест:", reply_markup=markup)
    await state.set_state(QuestBooking.choosing_quest)

# ИСПРАВЛЕНО: Добавлен QuestBooking.choosing_time в фильтр состояний, 
# чтобы кнопка "Изменить дату" не вызывала ошибку "Update not handled"
@router.callback_query(
    F.data.startswith("quest:"), 
    StateFilter(QuestBooking.choosing_quest, QuestBooking.choosing_time)
)
async def choose_date(call: CallbackQuery, state: FSMContext):
    _, name, duration = call.data.split(":", 2)
    
    await state.update_data(quest_name=name, duration=duration)
    
    # Достаем сохраненный жанр
    user_data = await state.get_data()
    current_genre = user_data.get('current_genre')
    
    min_date, max_date = get_min_max_dates()
    all_times = ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]
    
    dates_to_check = []
    curr = min_date
    while curr <= max_date:
        dates_to_check.append(curr.strftime("%d.%m.%Y"))
        curr += timedelta(days=1)
    
    from database import get_booked_slots_bulk 
    booked_slots_map = await get_booked_slots_bulk(name, dates_to_check, all_times, duration)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    
    for date_str in dates_to_check:
        day_bookings = booked_slots_map.get(date_str, [])
        free_slots_count = len([t for t in all_times if t not in day_bookings])
        
        if free_slots_count > 0:
            markup.inline_keyboard.append([
                InlineKeyboardButton(text=f"📅 {date_str} (свободно: {free_slots_count})", 
                                     callback_data=f"date:{date_str}")
            ])
    
    # ИСПРАВЛЕНО: Кнопка "Назад" теперь ведет к списку квестов выбранного жанра
    markup.inline_keyboard.append([
        InlineKeyboardButton(text="⬅ В главное меню", callback_data="to_main_menu")
    ])

    await call.message.edit_text(f"🎭 Квест: {name}\nВыберите удобную дату:", reply_markup=markup)
    await state.set_state(QuestBooking.choosing_date)

@router.callback_query(F.data.startswith("date:"), QuestBooking.choosing_date)
async def choose_time(call: CallbackQuery, state: FSMContext):
    selected_date = call.data.split(":")[1]
    await state.update_data(booking_date=selected_date)
    
    data = await state.get_data()
    quest_name = data.get('quest_name')
    duration = data.get('duration')
    
    all_times = ["10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"]

    from database import get_booked_slots_bulk
    booked_slots_map = await get_booked_slots_bulk(quest_name, [selected_date], all_times, duration)
    day_bookings = booked_slots_map.get(selected_date, [])
    
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    
    row = []
    for t in all_times:
        if t not in day_bookings:
            row.append(InlineKeyboardButton(text=t, callback_data=f"time:{t}"))
        if len(row) == 2:
            markup.inline_keyboard.append(row)
            row = []
    if row: markup.inline_keyboard.append(row)
    
    # Кнопка, которая теперь будет срабатывать благодаря изменениям выше
    markup.inline_keyboard.append([
        InlineKeyboardButton(
            text="⬅ Изменить дату", 
            callback_data=f"quest:{quest_name}:{duration}"
        )
    ])

    await call.message.edit_text(f"📅 Дата: {selected_date}\nВыберите свободное время:", reply_markup=markup)
    await state.set_state(QuestBooking.choosing_time)

@router.callback_query(F.data.startswith("time:"), QuestBooking.choosing_time)
async def confirm_booking(call: CallbackQuery, state: FSMContext):
    selected_time = call.data.split(":")[1]
    data = await state.get_data()
    
    is_free = await check_quest_availability(data['quest_name'], data['booking_date'], selected_time, data['duration'])
    
    if not is_free:
        await call.answer("❌ Это время уже занято.", show_alert=True)
        return

    await state.update_data(booking_time=selected_time)
    
    text = (f"📝 Проверьте данные:\n\n"
            f"🎭 Квест: {data['quest_name']}\n"
            f"📅 Дата: {data['booking_date']}\n"
            f"⏰ Время: {selected_time}\n"
            f"⏳ Длительность: {str(data['duration'])[:5]}")

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_final")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="start_quest_booking")]
    ])

    await call.message.edit_text(text, reply_markup=markup)
    await state.set_state(QuestBooking.confirming_booking)

@router.callback_query(F.data == "confirm_final", QuestBooking.confirming_booking)
async def finish_booking(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await get_user_from_db(call.from_user.id)
    
    success = await save_quest_booking(
        uid=call.from_user.id,
        client_name=user['nickname'],
        quest_name=data['quest_name'],
        date_str=data['booking_date'],
        time_start=data['booking_time']
    )
    
    if success:
        # Текст успешного завершения
        await call.message.edit_text(f"🎉 Заявка принята, {user['nickname']}!\nЖдем вас {data['booking_date']} к {data['booking_time']}.")
        
        # СБРОС СОСТОЯНИЯ И ВЫВОД ГЛАВНОГО МЕНЮ
        await state.clear()
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Выбрать квест", callback_data="start_quest_booking")],
            [InlineKeyboardButton(text="📅 Мои бронирования", callback_data="my_bookings")], # НОВАЯ КНОПКА
            [InlineKeyboardButton(text="📜 Правила", callback_data="view_rules")]
        ])
        
        # Отправляем новое сообщение, которое будет "Главным меню"
        await call.message.answer(f"Чем еще могу помочь, {user['nickname']}?", reply_markup=markup)
        
    else:
        await call.message.answer("❌ Ошибка при сохранении брони. Попробуйте перезапустить бота /start")
        await state.clear()

# --- ОТЛАДКА ---
@router.message()
async def any_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    logging.info(f" Необработанное сообщение: {message.text} | Состояние: {current_state}")

@router.callback_query(F.data == "to_main_menu")
async def back_to_main(call: CallbackQuery, state: FSMContext):
    await state.clear() # Полностью очищаем состояние бронирования
    user = await get_user_from_db(call.from_user.id) # Получаем данные юзера
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Выбрать квест", callback_data="start_quest_booking")],
            [InlineKeyboardButton(text="📅 Мои бронирования", callback_data="my_bookings")], # НОВАЯ КНОПКА
            [InlineKeyboardButton(text="📜 Правила", callback_data="view_rules")]
        ])
    
    await call.message.edit_text(f"Рады видеть вас снова, {user['nickname']}! Что хотите сделать?", reply_markup=markup)

@router.callback_query(F.data == "view_rules")
async def show_rules_handler(callback: CallbackQuery):
    # Собираем все текстовые блоки из rules.py в одно сообщение
    full_rules_text = "\n".join(RULES_PARTS)
    
    # Кнопка возврата в меню (по желанию)
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ])
    
    # Отправляем правила пользователю
    await callback.message.answer(
        text=full_rules_text,
        parse_mode="HTML",
        reply_markup=back_keyboard # Можно убрать, если кнопка "Назад" пока не нужна
    )
    
    # Убираем индикатор загрузки ("часики") на нажатой кнопке
    await callback.answer()

# ==========================================
# 3. ОБРАБОТЧИК КНОПКИ "НАЗАД В МЕНЮ"
# ==========================================
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery):
    # Удаляем сообщение с правилами, чтобы не засорять чат
    await callback.message.delete()
    
    # Снова вызываем функцию старта (имитируем ввод /start)
    await cmd_start(callback.message)
    
    await callback.answer()

# --- Функции для работы с активными бронированиями и их отменой ---

async def get_user_active_bookings(nickname):
    """
    Получает список активных броней пользователя, которые еще не удалены (processed != 2)
    """
    # Выбираем ID, название квеста, дату и время начала
    query = "SELECT id, quest_name, date, time_start FROM bookings WHERE client_name = %s AND processed != 2"
    return await execute_query(query, (nickname,), fetch=True)

async def cancel_booking_in_db(booking_id):
    """
    Ставит статус processed = 2. 
    Этот статус служит сигналом для 1С, чтобы та удалила документ и запись из MySQL.
    """
    query = "UPDATE bookings SET processed = 2 WHERE id = %s"
    # execute_query вернет True, если UPDATE прошел успешно
    return await execute_query(query, (booking_id,))

@router.callback_query(F.data == "my_bookings")
async def show_my_bookings(call: CallbackQuery, state: FSMContext):
    user = await get_user_from_db(call.from_user.id)
    bookings = await get_user_active_bookings(user['nickname'])

    if not bookings:
        await call.message.edit_text(
            "У вас пока нет активных бронирований.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅ В главное меню", callback_data="to_main_menu")]
            ])
        )
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[])
    # Формируем кнопки для каждой брони
    for booking in bookings:
        b_id, q_name, b_date, b_time = booking
        # Преобразуем дату и время для красивого отображения, если нужно
        btn_text = f"❌ Отменить: {q_name} ({b_date} {b_time})"
        markup.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"cancel_book:{b_id}")])
    
    markup.inline_keyboard.append([InlineKeyboardButton(text="⬅ В главное меню", callback_data="to_main_menu")])

    await call.message.edit_text("Ваши активные бронирования. Нажмите на бронь, чтобы отменить её:", reply_markup=markup)

@router.callback_query(F.data.startswith("cancel_book:"))
async def process_cancel_booking(call: CallbackQuery, state: FSMContext):
    booking_id = int(call.data.split(":")[1])
    logging.info(f"Хендлер: отмена брони {booking_id}")
    
    # 1. Выполняем отмену в БД
    success = await cancel_booking_in_db(booking_id)
    
    if success:
        await call.answer("✅ Бронирование отменено", show_alert=False)
        
        # 2. СРАЗУ ОБНОВЛЯЕМ СПИСОК, чтобы кнопка исчезла
        user = await get_user_from_db(call.from_user.id)
        bookings = await get_user_active_bookings(user['nickname'])

        if not bookings:
            await call.message.edit_text(
                "У вас больше нет активных бронирований.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅ В главное меню", callback_data="to_main_menu")]
                ])
            )
            return

        # Заново строим клавиатуру без удаленной брони
        markup = InlineKeyboardMarkup(inline_keyboard=[])
        for b_id, q_name, b_date, b_time in bookings:
            btn_text = f"❌ Отменить: {q_name} ({b_date} {b_time})"
            markup.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"cancel_book:{b_id}")])
        
        markup.inline_keyboard.append([InlineKeyboardButton(text="⬅ В главное меню", callback_data="to_main_menu")])

        # Редактируем текущее сообщение (кнопка исчезнет визуально)
        await call.message.edit_text("Ваши активные бронирования:", reply_markup=markup)
        
    else:
        logging.error(f"Бот не получил подтверждения отмены для ID {booking_id}")
        await call.answer("❌ Ошибка базы данных. Попробуйте позже.", show_alert=True)