from datetime import datetime, timedelta
import asyncio
from aiogram import Bot

def parse_datetime(date_str, time_str):
    if time_str and len(time_str) == 2:
        time_str = time_str + ":00"
    dt_str = f"{date_str} {time_str}"
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

def is_admin(user_id: int, admin_ids: list) -> bool:
    from database import is_admin_db
    return user_id in admin_ids or is_admin_db(user_id)

async def notification_scheduler(bot: Bot):
    while True:
        await asyncio.sleep(60)
        import database as db

        # Уведомления за 1 час
        hour_notifications = db.get_pending_notifications()
        for row in hour_notifications:
            app_id, user_id, app_time = row['id'], row['user_id'], row['appointment_time']
            try:
                dt_str = app_time.strftime('%d.%m.%Y %H:%M') if hasattr(app_time, 'strftime') else app_time
                await bot.send_message(
                    user_id,
                    f"🔔 Напоминание: через час у вас запись в шиномонтаж «Шараш-монтаж».\n"
                    f"Время: {dt_str}"
                )
                db.mark_notified(app_id)
            except Exception as e:
                print(f"Ошибка уведомления за час (запись {app_id}): {e}")

        # Уведомления за 24 часа
        day_notifications = db.get_notifications_24h()
        for row in day_notifications:
            app_id, user_id, app_time = row['id'], row['user_id'], row['appointment_time']
            try:
                dt_str = app_time.strftime('%d.%m.%Y %H:%M') if hasattr(app_time, 'strftime') else app_time
                await bot.send_message(
                    user_id,
                    f"🔔 Напоминаем: завтра в {dt_str} у вас запись в шиномонтаж «Шараш-монтаж».\n"
                    f"Ждём вас!"
                )
                db.mark_notified_24h(app_id)
            except Exception as e:
                print(f"Ошибка уведомления за 24 часа (запись {app_id}): {e}")

        # Проверка запланированных сообщений
        scheduled = db.get_pending_scheduled_messages()
        for msg_id, message in scheduled:
            user_ids = db.get_all_users_ids()
            success_count = 0
            for uid in user_ids:
                try:
                    await bot.send_message(uid, message)
                    success_count += 1
                except Exception as e:
                    print(f"Ошибка отправки запланированного сообщения {msg_id} пользователю {uid}: {e}")
            db.mark_scheduled_message_sent(msg_id)
            print(f"Запланированное сообщение {msg_id} отправлено {success_count} пользователям")

async def notify_client_status_change(bot: Bot, appointment_id):
    import database as db
    app = db.get_appointment(appointment_id)
    if not app or not app['user_id']:
        return
    user_id = app['user_id']
    master = db.get_master_by_id(app['master_id']) if app['master_id'] else None
    master_text = f"Мастер: {master['name']}\n" if master else ""
    status_text = {
        "pending": "🆕 Ваша запись создана и ожидает подтверждения.",
        "confirmed": "✅ Ваша запись подтверждена!",
        "in_progress": "🔧 Мастер приступил к работе над вашим автомобилем.",
        "ready": "🎁 Ваш автомобиль готов к выдаче!",
        "completed": "✔️ Работы выполнены. Спасибо, что выбрали нас!",
        "cancelled": "❌ Ваша запись отменена."
    }.get(app['status'], f"Статус изменён на {app['status']}.")
    service = db.get_service(app['service_id']) if app['service_id'] else None
    service_name = service['name'] if service else "Услуга"
    message = (
        f"{status_text}\n"
        f"{master_text}"
        f"Услуга: {service_name}\n"
        f"Время: {app['appointment_time'].strftime('%d.%m.%Y %H:%M') if app['appointment_time'] else 'не указано'}"
    )
    try:
        await bot.send_message(user_id, message)
    except Exception as e:
        print(f"Ошибка отправки уведомления клиенту {user_id}: {e}")