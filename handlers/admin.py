from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import keyboards as kb
import database as db
from config import ADMIN_IDS
from utils import is_admin, notify_client_status_change

router = Router()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id, ADMIN_IDS):
        return
    await message.answer("Панель администратора:", reply_markup=kb.admin_menu())

@router.callback_query(F.data.startswith("admin:"))
async def admin_callbacks(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, ADMIN_IDS):
        await callback.answer("Нет доступа", show_alert=True)
        return
    action = callback.data.split(":")[1]
    if action == "today":
        await show_today_appointments(callback)
    elif action == "prices":
        await show_prices(callback)
    elif action == "closed":
        await admin_closed_menu(callback)
    elif action == "stats":
        await admin_stats(callback)
    elif action == "back":
        await callback.message.edit_text("Панель администратора:", reply_markup=kb.admin_menu())
    elif action == "closed_list":
        await show_closed_periods(callback)
    elif action == "closed_add":
        await add_closed_start(callback)
    await callback.answer()

# ... существующие функции ...

# --- Новые обработчики для управления записями ---
@router.callback_query(F.data.startswith("app_"))
async def admin_appointment_action(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, ADMIN_IDS):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = callback.data.split(":")
    action = parts[0].split("_")[1]  # confirm, assign_master, cancel, status, back
    appointment_id = int(parts[1])
    
    if action == "confirm":
        db.update_appointment_status(appointment_id, "confirmed")
        await callback.message.edit_text(f"✅ Запись {appointment_id} подтверждена.")
        await notify_client_status_change(callback.bot, appointment_id)
    elif action == "assign_master":
        masters = db.get_available_masters_for_service(appointment_id, None)
        if not masters:
            await callback.message.edit_text("Нет доступных мастеров.")
            return
        await callback.message.edit_text(
            "Выберите мастера:",
            reply_markup=kb.master_selection_keyboard(masters, appointment_id)
        )
    elif action == "cancel":
        db.update_appointment_status(appointment_id, "cancelled")
        await callback.message.edit_text(f"❌ Запись {appointment_id} отменена.")
        await notify_client_status_change(callback.bot, appointment_id)
    elif action == "status":
        await callback.message.edit_text(
            "Выберите новый статус:",
            reply_markup=kb.status_selection_keyboard(appointment_id)
        )
    elif action == "back":
        # Вернуться к основным действиям
        await callback.message.edit_text(
            f"Управление записью {appointment_id}:",
            reply_markup=kb.admin_appointment_keyboard(appointment_id)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("select_master:"))
async def select_master(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, ADMIN_IDS):
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, master_id, appointment_id = callback.data.split(":")
    master_id = int(master_id)
    appointment_id = int(appointment_id)
    db.assign_master_to_appointment(appointment_id, master_id)
    master = db.get_master_by_id(master_id)
    await callback.message.edit_text(f"✅ Мастер {master['name']} назначен на запись {appointment_id}.")
    # Уведомить клиента
    await notify_client_status_change(callback.bot, appointment_id)
    await callback.answer()

@router.callback_query(F.data.startswith("set_status:"))
async def set_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, ADMIN_IDS):
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, new_status, appointment_id = callback.data.split(":")
    appointment_id = int(appointment_id)
    db.update_appointment_status(appointment_id, new_status)
    # Уведомить клиента
    status_names = {
        "pending": "🆕 Новый",
        "confirmed": "✅ Подтверждён",
        "in_progress": "🔧 В работе",
        "ready": "🎁 Готов к выдаче",
        "completed": "✔️ Выполнен",
        "cancelled": "❌ Отменён"
    }
    await callback.message.edit_text(f"Статус изменён на {status_names.get(new_status, new_status)}.")
    await notify_client_status_change(callback.bot, appointment_id)
    await callback.answer()