from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import pg8000

import keyboards as kb
import database as db
from utils import parse_datetime
from config import ADMIN_IDS, PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DATABASE

router = Router()

class BookingStates(StatesGroup):
    phone = State()
    service = State()
    car = State()
    newcar_brand = State()
    newcar_model = State()
    newcar_year = State()
    newcar_vin = State()
    newcar_vehicle = State()
    newcar_width = State()
    newcar_profile = State()
    newcar_diameter = State()
    newcar_season = State()
    quantity = State()
    date = State()
    time = State()
    confirm = State()

class CancelStates(StatesGroup):
    reason = State()

class TransferStates(StatesGroup):
    choosing_date = State()
    choosing_time = State()

class ReviewStates(StatesGroup):
    rating = State()
    comment = State()

class PaymentStates(StatesGroup):
    waiting_for_card = State()

def get_db_connection():
    return pg8000.connect(
        host=PG_HOST,
        port=int(PG_PORT),
        user=PG_USER,
        password=PG_PASSWORD,
        database=PG_DATABASE
    )

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.full_name)
    await message.answer(
        "👋 Добро пожаловать в шиномонтаж «Шараш-монтаж»!\n\n"
        "Здесь вы можете записаться на удобное время, узнать статус своих заказов и управлять автомобилями.",
        reply_markup=kb.user_main_menu()
    )

@router.message(F.text == "✅ Записаться")
async def book_start(message: Message, state: FSMContext):
    await state.update_data(message_ids=[])
    user_id = message.from_user.id

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT phone FROM users WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    phone = row[0] if row else None

    if not phone:
        await state.set_state(BookingStates.phone)
        sent = await message.answer(
            "Для записи нам понадобится ваш номер телефона. Нажмите кнопку ниже.",
            reply_markup=kb.phone_request_keyboard()
        )
        data = await state.get_data()
        data['message_ids'].append(sent.message_id)
        await state.update_data(message_ids=data['message_ids'])
    else:
        await state.set_state(BookingStates.service)
        sent = await message.answer("Выберите вид работы:", reply_markup=kb.service_type_keyboard())
        data = await state.get_data()
        data['message_ids'].append(sent.message_id)
        await state.update_data(message_ids=data['message_ids'])

@router.message(BookingStates.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    user_id = message.from_user.id
    db.update_user_phone(user_id, phone)
    await message.answer("Спасибо! Теперь продолжим.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(BookingStates.service)
    sent = await message.answer("Выберите вид работы:", reply_markup=kb.service_type_keyboard())
    data = await state.get_data()
    data['message_ids'].append(sent.message_id)
    await state.update_data(message_ids=data['message_ids'])

@router.message(BookingStates.phone)
async def process_phone_invalid(message: Message, state: FSMContext):
    sent = await message.answer(
        "Пожалуйста, отправьте контакт, нажав на кнопку ниже.",
        reply_markup=kb.phone_request_keyboard()
    )
    data = await state.get_data()
    data['message_ids'].append(sent.message_id)
    await state.update_data(message_ids=data['message_ids'])

@router.callback_query(BookingStates.service, F.data.startswith("service:"))
async def process_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    service = db.get_service(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    await state.update_data(service_id=service_id)
    await state.set_state(BookingStates.car)
    user_id = callback.from_user.id
    cars = db.get_user_cars(user_id)
    if cars:
        await callback.message.edit_text("Выберите автомобиль:", reply_markup=kb.cars_keyboard(user_id))
    else:
        await state.set_state(BookingStates.newcar_vehicle)
        await callback.message.edit_text("У вас ещё нет сохранённых автомобилей. Выберите тип:", reply_markup=kb.vehicle_type_keyboard())
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.callback_query(BookingStates.car, F.data.startswith("car:"))
async def process_car(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    if action == "add":
        await state.set_state(BookingStates.newcar_vehicle)
        await callback.message.edit_text("Выберите тип нового автомобиля:", reply_markup=kb.vehicle_type_keyboard())
    else:
        car_id = int(action)
        car = db.get_car(car_id)
        if car:
            await state.update_data(car_id=car_id, vehicle_type=car['vehicle_type'],
                                   tire_width=car['tire_width'], tire_profile=car['tire_profile'],
                                   tire_diameter=car['tire_diameter'], tire_season=car['tire_season'])
            await state.set_state(BookingStates.quantity)
            await callback.message.edit_text("Выберите количество шин:", reply_markup=kb.quantity_keyboard())
        else:
            await callback.answer("Автомобиль не найден", show_alert=True)
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.callback_query(BookingStates.newcar_vehicle, F.data.startswith("newcar_vehicle:"))
async def process_newcar_vehicle(callback: CallbackQuery, state: FSMContext):
    vehicle = callback.data.split(":")[1]
    await state.update_data(vehicle_type=vehicle)
    await state.set_state(BookingStates.newcar_brand)
    await callback.message.edit_text("Введите марку автомобиля (или нажмите «Пропустить»):", reply_markup=kb.skip_keyboard())
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.message(BookingStates.newcar_brand)
async def process_newcar_brand(message: Message, state: FSMContext):
    brand = message.text.strip()
    await state.update_data(brand=brand)
    await state.set_state(BookingStates.newcar_model)
    sent = await message.answer("Введите модель автомобиля (или нажмите «Пропустить»):", reply_markup=kb.skip_keyboard())
    data = await state.get_data()
    data['message_ids'].append(sent.message_id)
    await state.update_data(message_ids=data['message_ids'])

@router.callback_query(BookingStates.newcar_brand, F.data == "skip")
async def skip_brand(callback: CallbackQuery, state: FSMContext):
    await state.update_data(brand=None)
    await state.set_state(BookingStates.newcar_model)
    await callback.message.edit_text("Введите модель автомобиля (или нажмите «Пропустить»):", reply_markup=kb.skip_keyboard())
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.message(BookingStates.newcar_model)
async def process_newcar_model(message: Message, state: FSMContext):
    model = message.text.strip()
    await state.update_data(model=model)
    await state.set_state(BookingStates.newcar_year)
    sent = await message.answer("Введите год выпуска (или нажмите «Пропустить»):", reply_markup=kb.skip_keyboard())
    data = await state.get_data()
    data['message_ids'].append(sent.message_id)
    await state.update_data(message_ids=data['message_ids'])

@router.callback_query(BookingStates.newcar_model, F.data == "skip")
async def skip_model(callback: CallbackQuery, state: FSMContext):
    await state.update_data(model=None)
    await state.set_state(BookingStates.newcar_year)
    await callback.message.edit_text("Введите год выпуска (или нажмите «Пропустить»):", reply_markup=kb.skip_keyboard())
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.message(BookingStates.newcar_year)
async def process_newcar_year(message: Message, state: FSMContext):
    try:
        year = int(message.text.strip())
        await state.update_data(year=year)
    except ValueError:
        await state.update_data(year=None)
    await state.set_state(BookingStates.newcar_vin)
    sent = await message.answer("Введите VIN номер (или нажмите «Пропустить»):", reply_markup=kb.skip_keyboard())
    data = await state.get_data()
    data['message_ids'].append(sent.message_id)
    await state.update_data(message_ids=data['message_ids'])

@router.callback_query(BookingStates.newcar_year, F.data == "skip")
async def skip_year(callback: CallbackQuery, state: FSMContext):
    await state.update_data(year=None)
    await state.set_state(BookingStates.newcar_vin)
    await callback.message.edit_text("Введите VIN номер (или нажмите «Пропустить»):", reply_markup=kb.skip_keyboard())
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.message(BookingStates.newcar_vin)
async def process_newcar_vin(message: Message, state: FSMContext):
    vin = message.text.strip()
    await state.update_data(vin=vin)
    data = await state.get_data()
    user_id = message.from_user.id
    cars = db.get_user_cars(user_id)
    is_default = len(cars) == 0
    car_id = db.add_car(
        user_id,
        data.get('brand'),
        data.get('model'),
        data.get('year'),
        data.get('vin'),
        data['vehicle_type'],
        data.get('tire_width'),
        data.get('tire_profile'),
        data.get('tire_diameter'),
        data['tire_season'],
        is_default
    )
    await state.update_data(car_id=car_id)
    await state.set_state(BookingStates.quantity)
    await message.answer("Автомобиль сохранён. Выберите количество шин:", reply_markup=kb.quantity_keyboard())
    data = await state.get_data()
    data['message_ids'].append(message.message_id)
    await state.update_data(message_ids=data['message_ids'])

@router.callback_query(BookingStates.newcar_vin, F.data == "skip")
async def skip_vin(callback: CallbackQuery, state: FSMContext):
    await state.update_data(vin=None)
    data = await state.get_data()
    user_id = callback.from_user.id
    cars = db.get_user_cars(user_id)
    is_default = len(cars) == 0
    car_id = db.add_car(
        user_id,
        data.get('brand'),
        data.get('model'),
        data.get('year'),
        None,
        data['vehicle_type'],
        data.get('tire_width'),
        data.get('tire_profile'),
        data.get('tire_diameter'),
        data['tire_season'],
        is_default
    )
    await state.update_data(car_id=car_id)
    await state.set_state(BookingStates.quantity)
    await callback.message.edit_text("Автомобиль сохранён. Выберите количество шин:", reply_markup=kb.quantity_keyboard())
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.callback_query(BookingStates.quantity, F.data.startswith("quantity:"))
async def process_quantity(callback: CallbackQuery, state: FSMContext):
    quantity = int(callback.data.split(":")[1])
    await state.update_data(quantity=quantity)
    await state.set_state(BookingStates.date)
    await callback.message.edit_text("Выберите дату:", reply_markup=kb.calendar_keyboard())
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.callback_query(F.data.startswith("cal:"))
async def calendar_navigation(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    action = parts[1]
    if action == "ignore":
        await callback.answer()
        return
    elif action == "today":
        new_markup = kb.calendar_keyboard()
    elif action == "prev":
        year, month = int(parts[2]), int(parts[3])
        new_markup = kb.calendar_keyboard(year, month)
    elif action == "next":
        year, month = int(parts[2]), int(parts[3])
        new_markup = kb.calendar_keyboard(year, month)
    else:
        await callback.answer()
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=new_markup)
    except Exception as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()

@router.callback_query(BookingStates.date, F.data.startswith("date:"))
async def process_date(callback: CallbackQuery, state: FSMContext):
    date = callback.data.split(":")[1]
    from datetime import datetime
    today = datetime.now().date()
    try:
        selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        await callback.answer("Неверный формат даты", show_alert=True)
        return
    if selected_date < today:
        await callback.message.edit_text(
            "❌ Нельзя записаться на прошедшую дату. Выберите сегодняшний или будущий день.",
            reply_markup=kb.calendar_keyboard()
        )
        await callback.answer()
        return
    await state.update_data(date=date)
    await state.set_state(BookingStates.time)

    all_times = db.get_all_time_slots_for_date(date)
    booked = db.get_booked_slots(date)

    if selected_date == today:
        now_time = datetime.now().time()
        all_times = [t for t in all_times if datetime.strptime(t, "%H:%M").time() > now_time]

    await callback.message.edit_text("Выберите свободное время:",
                                      reply_markup=kb.time_keyboard(date, all_times, booked))
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.callback_query(BookingStates.time, F.data.startswith("time:"))
async def process_time(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split(":")[1]
    date_str, time_str = data_parts.split("|")
    await state.update_data(date=date_str, time=time_str)
    data_state = await state.get_data()
    appointment_time = parse_datetime(date_str, time_str)
    await state.update_data(appointment_time=appointment_time)

    service = db.get_service(data_state['service_id'])
    if service['price_fixed'] is not None:
        price = service['price_fixed']
    else:
        price = service['price_per_tire'] * data_state['quantity']

    summary = (
        f"📋 Проверьте данные записи:\n\n"
        f"🔧 Услуга: {service['name']}\n"
        f"🚗 Автомобиль: {data_state.get('brand', '')} {data_state.get('model', '')} {data_state['tire_diameter']}\"\n"
        f"🔢 Количество шин: {data_state['quantity']}\n"
        f"📅 Дата и время: {date_str} {time_str}\n"
        f"💰 Стоимость: {price} руб.\n\n"
        f"Всё верно?"
    )
    await state.set_state(BookingStates.confirm)
    await callback.message.edit_text(summary, reply_markup=kb.confirm_keyboard("dummy"))
    data = await state.get_data()
    if callback.message.message_id not in data['message_ids']:
        data['message_ids'].append(callback.message.message_id)
        await state.update_data(message_ids=data['message_ids'])
    await callback.answer()

@router.callback_query(BookingStates.confirm, F.data == "confirm:dummy")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    from datetime import datetime
    now = datetime.now()
    selected_datetime = data['appointment_time']
    if selected_datetime < now:
        await callback.message.edit_text(
            "❌ Выбранное время уже прошло. Пожалуйста, выберите другой слот.",
            reply_markup=kb.calendar_keyboard()
        )
        await state.set_state(BookingStates.date)
        await callback.answer()
        return

    booked = db.get_booked_slots(data['date'])
    if data['time'] in booked:
        await callback.message.edit_text(
            "❌ К сожалению, выбранное время уже занято. Пожалуйста, выберите другой слот.",
            reply_markup=kb.calendar_keyboard()
        )
        await state.set_state(BookingStates.date)
        await callback.answer()
        return

    appointment_id = db.create_appointment(
        user_id=user_id,
        service_id=data['service_id'],
        car_id=data['car_id'],
        quantity=data['quantity'],
        appointment_time=data['appointment_time']
    )

    await callback.message.answer(
        f"✅ Вы успешно записаны!\n"
        f"Номер вашей записи: {appointment_id}\n"
        f"Мы ждём вас {data['date']} в {data['time']}."
    )

    for msg_id in data.get('message_ids', []):
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
        except:
            pass

    admins = ADMIN_IDS + [a['user_id'] for a in db.get_all_admins()]
    for admin_id in admins:
        try:
            await callback.bot.send_message(
                admin_id,
                f"🔔 Новая запись №{appointment_id} от пользователя @{callback.from_user.username}\n"
                f"на {data['date']} {data['time']}"
            )
        except:
            pass

    await state.clear()

@router.callback_query(F.data == "cancel_booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    for msg_id in data.get('message_ids', []):
        try:
            await callback.bot.delete_message(chat_id=callback.message.chat.id, message_id=msg_id)
        except:
            pass
    await state.clear()
    await callback.message.answer("❌ Запись отменена.", reply_markup=kb.user_main_menu())

@router.message(F.text == "📋 Мои записи")
async def my_appointments(message: Message):
    user_id = message.from_user.id
    appointments = db.get_user_appointments(user_id)
    if not appointments:
        await message.answer("У вас пока нет записей.")
        return
    text = "Ваши записи:\n\n"
    for app in appointments:
        status_emoji = {
            "pending": "⏳ ожидает",
            "confirmed": "✅ подтверждена",
            "completed": "✔️ выполнена",
            "cancelled": "❌ отменена"
        }.get(app['status'], "неизвестно")
        dt = app['appointment_time'].strftime('%d.%m.%Y %H:%M')
        text += f"№{app['id']} — {app['service_name']} на {dt} — {status_emoji}\n"
    await message.answer(text, reply_markup=kb.my_appointments_keyboard(appointments))

@router.callback_query(F.data.startswith("cancel_app:"))
async def cancel_appointment_start(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    app = db.get_appointment(appointment_id)
    if not app or app['user_id'] != user_id:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    if app['status'] not in ('pending', 'confirmed'):
        await callback.answer("Эту запись уже нельзя отменить", show_alert=True)
        return
    await state.update_data(appointment_id=appointment_id)
    await state.set_state(CancelStates.reason)
    await callback.message.edit_text("Пожалуйста, укажите причину отмены (можно отправить одним сообщением):", 
                                      reply_markup=kb.cancel_reason_keyboard())

@router.message(CancelStates.reason)
async def cancel_appointment_reason(message: Message, state: FSMContext):
    reason = message.text.strip()
    data = await state.get_data()
    appointment_id = data['appointment_id']
    user_id = message.from_user.id
    if db.cancel_appointment(appointment_id, user_id, reason):
        await message.answer("✅ Запись отменена. Причина сохранена.")
    else:
        await message.answer("❌ Не удалось отменить запись.")
    await state.clear()

@router.callback_query(CancelStates.reason, F.data.startswith("cancel_reason:"))
async def cancel_appointment_reason_callback(callback: CallbackQuery, state: FSMContext):
    reason = callback.data.split(":")[1]
    data = await state.get_data()
    appointment_id = data['appointment_id']
    user_id = callback.from_user.id
    if db.cancel_appointment(appointment_id, user_id, reason):
        await callback.message.edit_text("✅ Запись отменена. Причина сохранена.")
    else:
        await callback.message.edit_text("❌ Не удалось отменить запись.")
    await state.clear()

@router.callback_query(F.data.startswith("transfer_app:"))
async def transfer_appointment_start(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    app = db.get_appointment(appointment_id)
    if not app or app['user_id'] != user_id:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    if app['status'] not in ('pending', 'confirmed'):
        await callback.answer("Эту запись уже нельзя перенести", show_alert=True)
        return
    await state.update_data(appointment_id=appointment_id)
    await state.set_state(TransferStates.choosing_date)
    await callback.message.edit_text("Выберите новую дату:", reply_markup=kb.calendar_keyboard())

@router.callback_query(TransferStates.choosing_date, F.data.startswith("date:"))
async def transfer_process_date(callback: CallbackQuery, state: FSMContext):
    date = callback.data.split(":")[1]
    await state.update_data(new_date=date)
    await state.set_state(TransferStates.choosing_time)
    booked = db.get_booked_slots(date)
    all_times = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
        "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
        "18:00", "18:30", "19:00"
    ]
    available_times = [t for t in all_times if t not in booked and db.is_time_slot_available(date, t)]
    if not available_times:
        await callback.message.edit_text("На эту дату нет свободных слотов. Выберите другую.", 
                                          reply_markup=kb.calendar_keyboard())
        await state.set_state(TransferStates.choosing_date)
        await callback.answer()
        return
    await callback.message.edit_text("Выберите новое время:", 
                                      reply_markup=kb.time_keyboard(date, available_times))
    await callback.answer()

@router.callback_query(TransferStates.choosing_time, F.data.startswith("time:"))
async def transfer_process_time(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split(":")[1]
    new_date, new_time = data_parts.split("|")
    data = await state.get_data()
    appointment_id = data['appointment_id']
    new_datetime = parse_datetime(new_date, new_time)
    db.transfer_appointment(appointment_id, new_datetime)
    await callback.message.edit_text("✅ Запись успешно перенесена.")
    await state.clear()

@router.message(F.text == "🚗 Мои автомобили")
async def my_cars(message: Message):
    user_id = message.from_user.id
    cars = db.get_user_cars(user_id)
    if not cars:
        await message.answer("У вас пока нет сохранённых автомобилей.")
        return
    await message.answer("Ваши автомобили:", reply_markup=kb.my_cars_keyboard(cars))

@router.callback_query(F.data.startswith("mycar:"))
async def car_action(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    if action == "add":
        await callback.message.edit_text("Выберите тип нового автомобиля:", reply_markup=kb.vehicle_type_keyboard())
        await callback.answer()
        return
    car_id = int(action)
    car = db.get_car(car_id)
    if not car:
        await callback.answer("Автомобиль не найден", show_alert=True)
        return
    text = f"Автомобиль: {car['brand'] or ''} {car['model'] or ''} {car['year'] or ''}\n"
    text += f"Тип: {car['vehicle_type']}, шины: {car['tire_width'] or ''}/{car['tire_profile'] or ''} R{car['tire_diameter'] or ''}, {car['tire_season'] or ''}\n"
    if car['vin']:
        text += f"VIN: {car['vin']}\n"
    if car['is_default']:
        text += "(по умолчанию)"
    await callback.message.edit_text(text, reply_markup=kb.car_actions_keyboard(car_id))
    await callback.answer()

@router.callback_query(F.data.startswith("car_default:"))
async def set_default_car(callback: CallbackQuery):
    car_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    if db.set_default_car(car_id, user_id):
        await callback.answer("✅ Автомобиль установлен по умолчанию")
    else:
        await callback.answer("❌ Ошибка", show_alert=True)
    cars = db.get_user_cars(user_id)
    await callback.message.edit_text("Ваши автомобили:", reply_markup=kb.my_cars_keyboard(cars))

@router.callback_query(F.data.startswith("car_delete:"))
async def delete_car(callback: CallbackQuery):
    car_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    if db.delete_car(car_id, user_id):
        await callback.answer("✅ Автомобиль удалён")
    else:
        await callback.answer("❌ Не удалось удалить", show_alert=True)
    cars = db.get_user_cars(user_id)
    if cars:
        await callback.message.edit_text("Ваши автомобили:", reply_markup=kb.my_cars_keyboard(cars))
    else:
        await callback.message.edit_text("У вас нет сохранённых автомобилей.")

@router.callback_query(F.data == "mycars")
async def back_to_cars(callback: CallbackQuery):
    user_id = callback.from_user.id
    cars = db.get_user_cars(user_id)
    if cars:
        await callback.message.edit_text("Ваши автомобили:", reply_markup=kb.my_cars_keyboard(cars))
    else:
        await callback.message.edit_text("У вас нет сохранённых автомобилей.")
    await callback.answer()

@router.callback_query(F.data.startswith("review_app:"))
async def review_start(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    app = db.get_appointment(appointment_id)
    if not app or app['user_id'] != user_id:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    if app['status'] != 'completed':
        await callback.answer("Отзыв можно оставить только после выполнения услуги", show_alert=True)
        return
    if db.has_review(appointment_id):
        await callback.answer("Вы уже оставили отзыв на эту запись", show_alert=True)
        return
    await state.update_data(appointment_id=appointment_id)
    await state.set_state(ReviewStates.rating)
    await callback.message.edit_text("Оцените качество услуги от 1 до 5 (отправьте цифру):")

@router.message(ReviewStates.rating)
async def review_rating(message: Message, state: FSMContext):
    try:
        rating = int(message.text.strip())
        if rating < 1 or rating > 5:
            raise ValueError
    except:
        await message.answer("Пожалуйста, введите число от 1 до 5.")
        return
    await state.update_data(rating=rating)
    await state.set_state(ReviewStates.comment)
    await message.answer("Оставьте комментарий (или отправьте /skip, чтобы пропустить):")

@router.message(ReviewStates.comment)
async def review_comment(message: Message, state: FSMContext):
    if message.text.strip() == "/skip":
        comment = ""
    else:
        comment = message.text.strip()
    data = await state.get_data()
    user_id = message.from_user.id
    db.add_review(user_id, data['appointment_id'], data['rating'], comment)
    await message.answer("✅ Спасибо за ваш отзыв!")
    await state.clear()

@router.callback_query(F.data.startswith("pay:"))
async def start_payment(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split(":")[1])
    await state.set_state(PaymentStates.waiting_for_card)
    await state.update_data(appointment_id=appointment_id)
    cards = db.get_active_cards()
    if cards:
        text = "Выберите карту для оплаты или введите свой номер карты:\n\n"
        for card in cards:
            text += f"💳 {card['card_number']}"
            if card['card_holder']:
                text += f" ({card['card_holder']})"
            if card['bank_name']:
                text += f" - {card['bank_name']}"
            text += "\n"
        await callback.message.answer(text)
    await callback.message.answer("Введите номер вашей карты (16 цифр):")
    await callback.answer()

@router.message(PaymentStates.waiting_for_card)
async def process_card_number(message: Message, state: FSMContext):
    card = message.text.strip()
    if not card.isdigit() or len(card) != 16:
        await message.answer("Номер карты должен состоять из 16 цифр. Попробуйте ещё раз.")
        return
    user_id = message.from_user.id
    data = await state.get_data()
    appointment_id = data['appointment_id']
    db.save_payment(user_id, appointment_id, card)
    await message.answer("✅ Номер карты сохранён. Оплата будет проведена в ближайшее время.")
    await state.clear()

@router.message(F.text == "ℹ️ О нас")
async def about(message: Message):
    await message.answer(
        "«Шараш-монтаж» — это быстрый и качественный шиномонтаж.\n"
        "📍 Адрес: ул. Шинная, д. 1\n"
        "📞 Телефон: +7 (999) 123-45-67\n"
        "⏰ Режим работы: ежедневно 09:00–20:00"
    )

@router.message()
async def fallback_handler(message: Message):
    await message.answer(
        "👋 Добро пожаловать в шиномонтаж «Шараш-монтаж»!\n\n"
        "Используйте кнопки меню для навигации.",
        reply_markup=kb.user_main_menu()
    )