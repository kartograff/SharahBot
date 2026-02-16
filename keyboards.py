from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import database as db

def user_main_menu():
    """Главное меню пользователя (reply-кнопки)"""
    kb = [
        [KeyboardButton(text="✅ Записаться")],
        [KeyboardButton(text="📋 Мои записи")],
        [KeyboardButton(text="🚗 Мои автомобили")],
        [KeyboardButton(text="ℹ️ О нас")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def phone_request_keyboard():
    """Клавиатура с кнопкой отправки контакта"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def service_type_keyboard():
    """Список активных услуг (inline)"""
    services = db.get_active_services()
    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(text=s['name'], callback_data=f"service:{s['id']}")
    builder.adjust(1)
    return builder.as_markup()

def vehicle_type_keyboard():
    """Выбор типа автомобиля"""
    builder = InlineKeyboardBuilder()
    vehicles = [
        ("🚗 Легковой", "car"),
        ("🚙 Джип", "suv"),
        ("🚚 Грузовой", "truck")
    ]
    for text, callback in vehicles:
        builder.button(text=text, callback_data=f"newcar_vehicle:{callback}")
    builder.adjust(1)
    return builder.as_markup()

def tire_season_keyboard():
    """Выбор сезонности шин"""
    builder = InlineKeyboardBuilder()
    seasons = [
        ("☀️ Лето", "summer"),
        ("❄️ Зима", "winter"),
        ("🍂 Всесезон", "all-season")
    ]
    for text, callback in seasons:
        builder.button(text=text, callback_data=f"newcar_season:{callback}")
    builder.adjust(1)
    return builder.as_markup()

def skip_keyboard():
    """Кнопка пропуска шага"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭️ Пропустить", callback_data="skip")
    return builder.as_markup()

def quantity_keyboard():
    """Выбор количества шин (1, 2, 4)"""
    builder = InlineKeyboardBuilder()
    for i in [1, 2, 4]:
        builder.button(text=str(i), callback_data=f"quantity:{i}")
    builder.adjust(3)
    return builder.as_markup()

def calendar_keyboard(year: int = None, month: int = None):
    """Инлайн-календарь с прокруткой месяцев и отметкой недоступных дней ❌"""
    if year is None or month is None:
        now = datetime.now()
        year, month = now.year, now.month
    builder = InlineKeyboardBuilder()
    month_names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    header_text = f"{month_names[month-1]} {year}"
    builder.row(InlineKeyboardButton(text=header_text, callback_data="ignore"))
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days])
    first_day = datetime(year, month, 1).weekday()
    if month == 12:
        days_in_month = (datetime(year+1, 1, 1) - timedelta(days=1)).day
    else:
        days_in_month = (datetime(year, month+1, 1) - timedelta(days=1)).day
    current_day = 1
    today = datetime.now().date()
    schedule = db.get_work_schedule()  # получаем график работы

    for week in range(6):
        row_buttons = []
        for weekday in range(7):
            if week == 0 and weekday < first_day:
                row_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            elif current_day <= days_in_month:
                date_str = f"{year}-{month:02d}-{current_day:02d}"
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                is_past = date_obj < today
                # Проверяем, рабочий ли день по графику
                is_working = False
                for day in schedule:
                    if day['day_of_week'] == date_obj.weekday():
                        is_working = day['is_working'] == 1
                        break
                if is_past or not is_working:
                    text = f"❌ {current_day}"
                    callback_data = "ignore"
                else:
                    text = str(current_day)
                    callback_data = f"date:{date_str}"
                row_buttons.append(InlineKeyboardButton(text=text, callback_data=callback_data))
                current_day += 1
            else:
                row_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
        builder.row(*row_buttons)
        if current_day > days_in_month:
            break
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    builder.row(
        InlineKeyboardButton(text="◀", callback_data=f"cal:prev:{prev_year}:{prev_month}"),
        InlineKeyboardButton(text="Сегодня", callback_data="cal:today"),
        InlineKeyboardButton(text="▶", callback_data=f"cal:next:{next_year}:{next_month}")
    )
    return builder.as_markup()

def time_keyboard(date: str, all_times: list, booked: set):
    """
    Формирует клавиатуру выбора времени.
    Занятые слоты помечаются ❌, свободные ✅.
    """
    builder = InlineKeyboardBuilder()
    for t in all_times:
        if t in booked:
            builder.button(text=f"❌ {t}", callback_data="ignore")
        else:
            builder.button(text=f"✅ {t}", callback_data=f"time:{date}|{t}")
    builder.adjust(3)
    return builder.as_markup()

def confirm_keyboard(appointment_data: str):
    """Кнопки подтверждения/отмены записи"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"confirm:{appointment_data}")
    builder.button(text="❌ Отменить", callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()

def cars_keyboard(user_id):
    """Список автомобилей пользователя для выбора при записи"""
    cars = db.get_user_cars(user_id)
    builder = InlineKeyboardBuilder()
    for car in cars:
        text = f"{'⭐ ' if car['is_default'] else '🚗 '}{car['brand'] or ''} {car['model'] or ''} {car['tire_diameter']}\""
        builder.button(text=text, callback_data=f"car:{car['id']}")
    builder.button(text="➕ Добавить новый автомобиль", callback_data="car:add")
    builder.adjust(1)
    return builder.as_markup()

def my_cars_keyboard(cars):
    """Список автомобилей для просмотра в разделе 'Мои автомобили'"""
    builder = InlineKeyboardBuilder()
    for car in cars:
        text = f"{'⭐ ' if car['is_default'] else '🚗 '}{car['brand'] or ''} {car['model'] or ''} {car['tire_diameter']}\""
        builder.button(text=text, callback_data=f"mycar:{car['id']}")
    builder.button(text="➕ Добавить автомобиль", callback_data="mycar:add")
    builder.adjust(1)
    return builder.as_markup()

def car_actions_keyboard(car_id):
    """Действия с конкретным автомобилем (сделать по умолчанию, удалить, назад)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Сделать по умолчанию", callback_data=f"car_default:{car_id}")
    builder.button(text="❌ Удалить", callback_data=f"car_delete:{car_id}")
    builder.button(text="🔙 Назад", callback_data="mycars")
    builder.adjust(1)
    return builder.as_markup()

def my_appointments_keyboard(appointments):
    """Клавиатура со списком записей пользователя (отмена, отзыв)"""
    builder = InlineKeyboardBuilder()
    for app in appointments:
        if app['status'] in ('pending', 'confirmed'):
            dt = app['appointment_time'].strftime('%d.%m %H:%M')
            text = f"№{app['id']} {dt} - {app['service_name']} (отменить)"
            builder.button(text=text, callback_data=f"cancel_app:{app['id']}")
        elif app['status'] == 'completed':
            if not db.has_review(app['id']):
                dt = app['appointment_time'].strftime('%d.%m %H:%M')
                text = f"№{app['id']} {dt} - {app['service_name']} (отзыв)"
                builder.button(text=text, callback_data=f"review_app:{app['id']}")
    builder.adjust(1)
    return builder.as_markup()

def cancel_reason_keyboard():
    """Варианты причин отмены для быстрого выбора"""
    builder = InlineKeyboardBuilder()
    reasons = [
        "Не могу приехать",
        "Изменились планы",
        "Не подходит время",
        "Выбрал другой сервис",
        "Другое"
    ]
    for r in reasons:
        builder.button(text=r, callback_data=f"cancel_reason:{r}")
    builder.adjust(1)
    return builder.as_markup()

def payment_keyboard(appointment_id):
    """Кнопка оплаты"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить", callback_data=f"pay:{appointment_id}")
    return builder.as_markup()

def admin_menu():
    """Меню администратора в Telegram"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Записи на сегодня", callback_data="admin:today")
    builder.button(text="💰 Управление ценами", callback_data="admin:prices")
    builder.button(text="🚫 Нерабочее время", callback_data="admin:closed")
    builder.button(text="📊 Статистика", callback_data="admin:stats")
    builder.adjust(1)
    return builder.as_markup()

def admin_closed_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Просмотреть закрытые периоды", callback_data="admin:closed_list")
    builder.button(text="➕ Добавить выходной/праздник", callback_data="admin:closed_add")
    builder.button(text="🔙 Назад", callback_data="admin:back")
    builder.adjust(1)
    return builder.as_markup()

def closed_periods_list_keyboard(periods):
    builder = InlineKeyboardBuilder()
    for p in periods:
        if p['period_type'] == 'weekly':
            days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            day_name = days[p['day_of_week']] if p['day_of_week'] is not None else '?'
            text = f"{day_name} {p['start_time'] or 'весь день'}–{p['end_time'] or ''} {p['description']}"
        else:
            text = f"{p['specific_date']} {p['start_time'] or 'весь день'}–{p['end_time'] or ''} {p['description']}"
        builder.button(text=text, callback_data=f"closed_info:{p['id']}")
    builder.button(text="🔙 Назад", callback_data="admin:closed")
    builder.adjust(1)
    return builder.as_markup()

def closed_period_actions_keyboard(period_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить", callback_data=f"closed_del:{period_id}")
    builder.button(text="🔙 Назад", callback_data="admin:closed_list")
    builder.adjust(2)
    return builder.as_markup()

def admin_notify_keyboard(appointment_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"admin_confirm:{appointment_id}")
    builder.button(text="❌ Отменить", callback_data=f"admin_cancel:{appointment_id}")
    builder.adjust(2)
    return builder.as_markup()

def admin_appointment_keyboard(appointment_id):
    """Клавиатура для управления конкретной записью (для администратора)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"app_confirm:{appointment_id}")
    builder.button(text="👨‍🔧 Назначить мастера", callback_data=f"app_assign_master:{appointment_id}")
    builder.button(text="❌ Отменить", callback_data=f"app_cancel:{appointment_id}")
    builder.button(text="📝 Изменить статус", callback_data=f"app_status:{appointment_id}")
    builder.adjust(2)
    return builder.as_markup()

def master_selection_keyboard(masters, appointment_id):
    builder = InlineKeyboardBuilder()
    for m in masters:
        builder.button(text=m['name'], callback_data=f"select_master:{m['id']}:{appointment_id}")
    builder.button(text="🔙 Назад", callback_data=f"app_back:{appointment_id}")
    builder.adjust(1)
    return builder.as_markup()

def status_selection_keyboard(appointment_id):
    statuses = [
        ("🆕 Новый", "pending"),
        ("✅ Подтверждён", "confirmed"),
        ("🔧 В работе", "in_progress"),
        ("🎁 Готов к выдаче", "ready"),
        ("✔️ Выполнен", "completed"),
        ("❌ Отменён", "cancelled")
    ]
    builder = InlineKeyboardBuilder()
    for text, code in statuses:
        builder.button(text=text, callback_data=f"set_status:{code}:{appointment_id}")
    builder.button(text="🔙 Назад", callback_data=f"app_back:{appointment_id}")
    builder.adjust(2)
    return builder.as_markup()