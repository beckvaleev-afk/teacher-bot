import asyncio
import json
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from sqlalchemy import select, func

from database.db import get_session
from database.models import Submission
from services.drive import log_to_sheets, get_telegram_file_path
from services.face import verify_face
from services.quiz import generate_questions
from services.grading import calculate_grade, format_result_message
import config

router = Router()

ALLOWED_EXTENSIONS  = {".pdf", ".docx", ".pptx"}
QUESTION_TIMEOUT    = 30
TOTAL_QUESTIONS     = 10
QUIZ_TOTAL_TIMEOUT  = 360   # 6 daqiqa
MAX_DAILY_ATTEMPTS    = 3     # kunlik limit
WAIT_MINUTES          = 15    # urinishlar orasidagi kutish (daqiqa)


class StudentFlow(StatesGroup):
    choosing_type    = State()
    entering_name    = State()
    entering_course  = State()
    entering_group   = State()
    entering_subject = State()
    entering_topic   = State()
    uploading_file   = State()
    face_verify      = State()
    taking_quiz      = State()


async def check_daily_limit(telegram_id: int) -> dict:
    """Returns count of today submissions and last submission time."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    async with get_session() as session:
        count_result = await session.execute(
            select(func.count(Submission.id)).where(
                Submission.telegram_id == telegram_id,
                Submission.created_at  >= today_start,
            )
        )
        count = count_result.scalar() or 0

        last_result = await session.execute(
            select(Submission.created_at).where(
                Submission.telegram_id == telegram_id,
                Submission.created_at  >= today_start,
            ).order_by(Submission.created_at.desc()).limit(1)
        )
        last_time = last_result.scalar()

    return {"count": count, "last_time": last_time}


def _face_retry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Qayta urinish", callback_data="face:retry")
    ]])


def _share_keyboard(share_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📤 Natijani ulashish", switch_inline_query=share_text)
    ]])


def _question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔘 A", callback_data="ans:0")],
        [InlineKeyboardButton(text="🔘 B", callback_data="ans:1")],
        [InlineKeyboardButton(text="🔘 C", callback_data="ans:2")],
        [InlineKeyboardButton(text="🔘 D", callback_data="ans:3")],
    ])


@router.callback_query(F.data.startswith("type:"))
async def chose_assignment_type(cb: CallbackQuery, state: FSMContext):
    info = await check_daily_limit(cb.from_user.id)
    count     = info["count"]
    last_time = info["last_time"]

    # Kunlik limit tekshiruvi
    if count >= MAX_DAILY_ATTEMPTS:
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer(
            "⛔ *Kunlik limitdan foydalanib bo'ldingiz!*\n\n"
            f"Siz bugun *{MAX_DAILY_ATTEMPTS} marta* topshirdingiz.\n"
            "Ertaga qayta urinib ko'ring. 🌅",
            parse_mode="Markdown",
        )
        await cb.answer()
        return

    # Urinishlar orasidagi kutish tekshiruvi (1 va 2-urinish uchun)
    if count >= 1 and last_time:
        from datetime import timezone
        now = datetime.utcnow()
        # Make both naive for comparison
        if last_time.tzinfo is not None:
            last_naive = last_time.replace(tzinfo=None)
        else:
            last_naive = last_time
        elapsed_minutes = (now - last_naive).total_seconds() / 60
        remaining = WAIT_MINUTES - elapsed_minutes
        if remaining > 0:
            mins = int(remaining)
            secs = int((remaining - mins) * 60)
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.answer(
                f"⏳ *Kutish vaqti tugmagan!*\n\n"
                f"Keyingi urinish uchun *{mins} daqiqa {secs} soniya* kutish kerak.\n\n"
                f"Sabr qiling! 🕐",
                parse_mode="Markdown",
            )
            await cb.answer()
            return

    atype_map = {
        "independent": "Mustaqil ish",
        "retake":      "Qayta o'zlashtirish",
        "additional":  "Qo'shimcha topshiriq",
    }
    atype = atype_map.get(cb.data.split(":")[1], cb.data.split(":")[1])
    await state.update_data(assignment_type=atype)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        f"✅ Tanlandi: *{atype}*\n\n"
        "Ism va familiyangizni kiriting:\n_(Masalan: Aliyev Ali)_",
        parse_mode="Markdown",
    )
    await state.set_state(StudentFlow.entering_name)
    await cb.answer()


@router.message(StudentFlow.entering_name)
async def got_name(msg: Message, state: FSMContext):
    name = msg.text.strip() if msg.text else ""
    if len(name.split()) < 2:
        return await msg.answer(
            "❗ Iltimos, *ism va familiyangizni* to'liq kiriting.\n_(Masalan: Aliyev Ali)_",
            parse_mode="Markdown",
        )
    await state.update_data(full_name=name)
    await msg.answer("Kurs raqamini kiriting:\n_(Masalan: 1, 2, 3 yoki 4)_", parse_mode="Markdown")
    await state.set_state(StudentFlow.entering_course)


@router.message(StudentFlow.entering_course)
async def got_course(msg: Message, state: FSMContext):
    course = msg.text.strip() if msg.text else ""
    if not course:
        return await msg.answer("❗ Kurs raqamini kiriting.")
    await state.update_data(course=course)
    await msg.answer("Guruh nomini kiriting:\n_(Masalan: CS-101, MM-22)_", parse_mode="Markdown")
    await state.set_state(StudentFlow.entering_group)


@router.message(StudentFlow.entering_group)
async def got_group(msg: Message, state: FSMContext):
    group = msg.text.strip() if msg.text else ""
    if not group:
        return await msg.answer("❗ Guruh nomini kiriting.")
    await state.update_data(group=group)
    await msg.answer("📚 Fan nomini kiriting:\n_(Masalan: Iqtisodiyot, Menejment)_", parse_mode="Markdown")
    await state.set_state(StudentFlow.entering_subject)


@router.message(StudentFlow.entering_subject)
async def got_subject(msg: Message, state: FSMContext):
    subject = msg.text.strip() if msg.text else ""
    if len(subject) < 2:
        return await msg.answer("❗ Fan nomini kiriting.")
    await state.update_data(subject=subject)
    await msg.answer("Topshiriq mavzusini kiriting:", parse_mode="Markdown")
    await state.set_state(StudentFlow.entering_topic)


@router.message(StudentFlow.entering_topic)
async def got_topic(msg: Message, state: FSMContext):
    topic = msg.text.strip() if msg.text else ""
    if len(topic) < 3:
        return await msg.answer("❗ Mavzu kamida 3 ta harfdan iborat bo'lishi kerak.")
    await state.update_data(topic=topic)
    await msg.answer(
        "📎 Faylingizni yuboring.\n\n"
        "Ruxsat etilgan formatlar: `.pdf`, `.docx`, `.pptx`\n"
        "📦 Fayl hajmi: maksimal *6 MB*",
        parse_mode="Markdown",
    )
    await state.set_state(StudentFlow.uploading_file)


@router.message(StudentFlow.uploading_file, F.document)
async def got_file(msg: Message, state: FSMContext):
    doc      = msg.document
    filename = doc.file_name or "file"
    ext      = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        return await msg.answer(
            f"❗ Faqat `.pdf`, `.docx`, `.pptx` formatlari qabul qilinadi.\n"
            f"Siz yubordingiz: `{ext}`",
            parse_mode="Markdown",
        )
    if doc.file_size and doc.file_size > 6 * 1024 * 1024:
        size_mb = doc.file_size / (1024 * 1024)
        return await msg.answer(
            f"❗ Fayl hajmi juda katta: *{size_mb:.1f} MB*\n"
            f"Maksimal: *6 MB*",
            parse_mode="Markdown",
        )

    wait = await msg.answer("⏳ Fayl qabul qilinyapti...")

    # Get Telegram file link — no upload needed
    try:
        file_link = await get_telegram_file_path(msg.bot, doc.file_id)
        await state.update_data(file_url=file_link, file_id=doc.file_id)
        print(f"[TELEGRAM] Fayl qabul qilindi: {filename}")
    except Exception as e:
        await state.update_data(file_url=f"tg://file/{doc.file_id}", file_id=doc.file_id)
        print(f"[TELEGRAM] Link xatosi: {e}")

    await wait.edit_text("✅ Fayl qabul qilindi!")
    await state.set_state(StudentFlow.face_verify)
    face_msg = await msg.answer(
        "📸 *Yuz tasdiqlash*\n\n"
        "Selfi rasmingizni yuboring:\n\n"
        "📱 *Telefon:* 📎 → Camera → rasm oling\n"
        "💻 *Kompyuter:* 📎 → Photo → webcam\n\n"
        "Talablar:\n"
        "• Yuzingiz to'liq ko'rinsin\n"
        "• Yaxshi yoritilgan joyda turing\n"
        "• Ko'zlaringizni oching\n"
        "• Faqat siz bo'ling",
        parse_mode="Markdown",
    )
    await state.update_data(face_request_msg_id=face_msg.message_id)


@router.message(StudentFlow.uploading_file)
async def file_wrong_type(msg: Message):
    await msg.answer(
        "❗ Iltimos, fayl yuboring (`.pdf`, `.docx` yoki `.pptx`).\n"
        "Fayl hajmi maksimal *6 MB*.",
        parse_mode="Markdown",
    )


@router.message(StudentFlow.face_verify, F.photo)
async def got_photo(msg: Message, state: FSMContext):
    # Check photo message_id is newer than file upload message
    data = await state.get_data()
    last_bot_msg_id = data.get("face_request_msg_id", 0)

    if msg.message_id <= last_bot_msg_id:
        return await msg.answer(
            "Rasm juda eski!\n\n"
            "Iltimos, hozir yangi selfi oling va yuboring.\n"
            "Telefon: 📎 → Camera\n"
            "Kompyuter: 📎 → Photo → webcam",
        )

    checking = await msg.answer("⏳ Yuz tekshirilmoqda...")
    try:
        photo     = msg.photo[-1]
        tg_file   = await msg.bot.get_file(photo.file_id)
        img_data  = await msg.bot.download_file(tg_file.file_path)
        img_bytes = img_data.read()
        result    = await verify_face(img_bytes)
    except Exception as e:
        await checking.edit_text(f"❌ Texnik xato: {e}\nQayta urinib ko'ring.")
        return

    if result["verified"]:
        await checking.edit_text("✅ Yuz tasdiqlandi!")
        # Save selfie Telegram link
        try:
            selfie_link = await get_telegram_file_path(msg.bot, msg.photo[-1].file_id)
            await state.update_data(selfie_url=selfie_link)
            print(f"[TELEGRAM] Selfi linki saqlandi")
        except Exception as e:
            print(f"[TELEGRAM] Selfi link xatosi: {e}")

        await msg.answer("🎯 Test boshlanyapti...")
        await state.set_state(StudentFlow.taking_quiz)
        await start_quiz(msg, state)
    else:
        reason = result.get("reason", "Noma'lum xato")
        await checking.edit_text(
            f"❌ *Yuz tasdiqlanmadi*\n\n{reason}\n\nQayta selfi yuboring:",
            reply_markup=_face_retry_keyboard(),
            parse_mode="Markdown",
        )


@router.callback_query(StudentFlow.face_verify, F.data == "face:retry")
async def face_retry(cb: CallbackQuery):
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "📸 Qayta selfi yuboring:\n\n"
        "📱 Telefon: 📎 → Camera\n"
        "💻 Kompyuter: 📎 → Photo → webcam"
    )
    await cb.answer()


@router.message(StudentFlow.face_verify)
async def face_wrong_input(msg: Message):
    await msg.answer(
        "📸 Iltimos, *selfi rasm* yuboring.\n\n"
        "📱 Telefon: 📎 → Camera\n"
        "💻 Kompyuter: 📎 → Photo → webcam",
        parse_mode="Markdown",
    )


async def start_quiz(msg: Message, state: FSMContext):
    data  = await state.get_data()
    topic = data.get("topic", "Umumiy")
    wait  = await msg.answer(f"⏳ *{topic}* mavzusida savollar tayyorlanmoqda...", parse_mode="Markdown")
    questions = await generate_questions(topic, notify_msg=msg)
    await wait.delete()
    await state.update_data(questions=questions, q_index=0, correct=0, wrong=0,
                             quiz_start_time=datetime.utcnow().isoformat())
    asyncio.create_task(_quiz_global_timeout(msg.chat.id, msg.bot, state))
    await send_question(msg, state)


async def _quiz_global_timeout(chat_id: int, bot, state: FSMContext):
    await asyncio.sleep(QUIZ_TOTAL_TIMEOUT)
    current_state = await state.get_state()
    if current_state == StudentFlow.taking_quiz:
        await state.update_data(q_index=TOTAL_QUESTIONS)
        await bot.send_message(
            chat_id,
            "⏰ *3 daqiqa vaqt tugadi!*\n\nSiz topshiriqni bajara olmadingiz.\nNatija: *Qoniqarsiz* ❌",
            parse_mode="Markdown",
        )
        class _FakeMsg:
            chat = type("C", (), {"id": chat_id})()
            def __init__(self): self.bot = bot
            async def answer(self, text, **kw): return await bot.send_message(chat_id, text, **kw)
        await finish_quiz(_FakeMsg(), state, timed_out=True)


async def send_question(msg: Message, state: FSMContext):
    data      = await state.get_data()
    idx       = data["q_index"]
    questions = data["questions"]
    if idx >= len(questions):
        await finish_quiz(msg, state)
        return
    q         = questions[idx]
    opts_text = "\n".join(q["options"])
    sent = await msg.answer(
        f"❓ *Savol {idx + 1}/{TOTAL_QUESTIONS}*\n\n"
        f"{q['question']}\n\n{opts_text}\n\n"
        f"⏱ Vaqt: {QUESTION_TIMEOUT} soniya",
        reply_markup=_question_keyboard(),
        parse_mode="Markdown",
    )
    await state.update_data(current_msg_id=sent.message_id)
    asyncio.create_task(_auto_advance(msg.chat.id, msg.bot, state, idx, sent.message_id))


async def _auto_advance(chat_id, bot, state, expected_idx, msg_id):
    await asyncio.sleep(QUESTION_TIMEOUT)
    data = await state.get_data()
    if data.get("q_index") != expected_idx:
        return
    await state.update_data(q_index=expected_idx + 1, wrong=data.get("wrong", 0) + 1)
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)
    except Exception:
        pass
    await bot.send_message(chat_id, "⏰ Vaqt tugadi! Keyingi savol...")

    class _FakeMsg:
        chat = type("C", (), {"id": chat_id})()
        def __init__(self): self.bot = bot
        async def answer(self, text, **kw): return await bot.send_message(chat_id, text, **kw)

    await send_question(_FakeMsg(), state)


@router.callback_query(StudentFlow.taking_quiz, F.data.startswith("ans:"))
async def got_answer(cb: CallbackQuery, state: FSMContext):
    data      = await state.get_data()
    idx       = data["q_index"]
    questions = data["questions"]
    if idx >= len(questions):
        await cb.answer()
        return
    chosen   = int(cb.data.split(":")[1])
    is_right = chosen == questions[idx]["correct"]
    await state.update_data(
        q_index = idx + 1,
        correct = data["correct"] + (1 if is_right else 0),
        wrong   = data["wrong"]   + (0 if is_right else 1),
    )
    try:
        await cb.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    icon = "✅" if is_right else "❌"
    await cb.message.answer(icon)
    await cb.answer()
    await send_question(cb.message, state)


async def finish_quiz(msg: Message, state: FSMContext, timed_out: bool = False):
    data    = await state.get_data()
    correct = 0 if timed_out else data.get("correct", 0)
    result  = calculate_grade(correct, TOTAL_QUESTIONS)
    student_name = data.get("full_name", "Talaba")

    await msg.answer(format_result_message(result, student_name), parse_mode="Markdown")

    if not result["passed"] or timed_out:
        await msg.answer("📚 Ertaga yaxshilab tayyorlanib, qayta urinib ko'ring! 💪")

    share_text = (
        f"Men @Iqtisod_Valiyev_AssistantBot da test topdirdim! "
        f"Fan: {data.get('subject', '')} | "
        f"Mavzu: {data.get('topic', '')} | "
        f"Natija: {correct}/{TOTAL_QUESTIONS} — Baho: {result['grade']} ({result['status']})"
    )
    await msg.answer(
        "Natijangizni do'stlaringiz bilan ulashing 👇",
        reply_markup=_share_keyboard(share_text),
    )

    # Save to DB
    try:
        async with get_session() as session:
            session.add(Submission(
                telegram_id     = msg.chat.id,
                full_name       = data.get("full_name", ""),
                course          = data.get("course", ""),
                group           = data.get("group", ""),
                assignment_type = data.get("assignment_type", ""),
                topic           = data.get("topic", ""),
                file_url        = data.get("file_url", ""),
                score           = result["score"],
                grade           = result["grade"],
                status          = result["status"],
                passed          = "Ha" if result["passed"] else "Yo'q",
            ))
        print(f"[DB] Saqlandi: {data.get('full_name')} — {result['score']}/10")
    except Exception as e:
        print(f"[DB] Xato: {e}")

    # Log to Sheets with both file and selfie links
    await log_to_sheets(data, result, file_url=data.get("file_url", ""))

    await msg.answer("⏳ Natijalar saqlanmoqda...\n✅ Saqlandi! Qayta topshirish uchun /start ni bosing.")
    await state.clear()
