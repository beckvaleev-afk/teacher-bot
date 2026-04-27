from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config

router = Router()

# ── Maintenance mode ──────────────────────────────────────
# Set to True to pause bot, False to enable
MAINTENANCE_MODE = False
MAINTENANCE_TEXT = (
    "🔧 *Texnik tanaffus*\n\n"
    "Savollar bazasi yangilanyapti.\n"
    "Ertaga qayta urinib ko'ring!\n\n"
    "Noqulaylik uchun uzr so'raymiz. 🙏"
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Mustaqil ish", callback_data="type:independent")],
        [InlineKeyboardButton(text="🔁 Qayta o'zlashtirish / NB Otroborotka", callback_data="type:retake")],
        [InlineKeyboardButton(text="➕ Qo'shimcha topshiriq", callback_data="type:additional")],
    ])


@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()

    # Maintenance mode check
    if MAINTENANCE_MODE:
        # Admin can still use the bot
        if msg.from_user.id == config.ADMIN_ID:
            await msg.answer(
                "⚠️ *Maintenance mode YOQIQ*\n"
                "Siz admin sifatida davom etishingiz mumkin.",
                parse_mode="Markdown"
            )
        else:
            return await msg.answer(MAINTENANCE_TEXT, parse_mode="Markdown")

    name = msg.from_user.first_name or "Talaba"
    text = (
        f"Assalomu alaykum, {name} 👋\n\n"
        f"Valiev Teacher Assistant Botga xush kelibsiz.\n"
        f"Siz bu bot orqali fanlardan vazifalarni topshirishingiz mumkin!\n\n"
        f"Quyidagi topshiriq turlaridan birini tanlang:"
    )
    await msg.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("maintenance"))
async def toggle_maintenance(msg: Message):
    """Admin only: toggle maintenance mode via command."""
    if msg.from_user.id != config.ADMIN_ID:
        return
    await msg.answer(
        "Maintenance rejimini o'zgartirish uchun:\n\n"
        "start.py da `MAINTENANCE_MODE = False/False` ni o'zgartiring."
    )
