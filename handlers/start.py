from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📘 Mustaqil ish", callback_data="type:independent")],
        [InlineKeyboardButton(text="🔁 Qayta o'zlashtirish / NB Otroborotka", callback_data="type:retake")],
        [InlineKeyboardButton(text="➕ Qo'shimcha topshiriq", callback_data="type:additional")],
    ])


@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    name = msg.from_user.first_name or "Talaba"
    text = (
        f"Assalomu alaykum, {name} 👋\n\n"
        f"Valiev Teacher Assistant Botga xush kelibsiz.\n"
        f"Siz bu bot orqali fanlardan vazifalarni topshirishingiz mumkin!\n\n"
        f"Quyidagi topshiriq turlaridan birini tanlang:"
    )
    await msg.answer(text, reply_markup=main_menu_keyboard())
