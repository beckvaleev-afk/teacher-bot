import csv
import io
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile,
)
from sqlalchemy import select, func, distinct

from database.db import get_session
from database.models import Submission
import config

router = Router()


def is_admin(msg: Message) -> bool:
    return msg.from_user.id == config.ADMIN_ID


def is_admin_cb(cb: CallbackQuery) -> bool:
    return cb.from_user.id == config.ADMIN_ID


# ── FSM for filters ───────────────────────────────────────
class AdminFilter(StatesGroup):
    waiting_group   = State()
    waiting_subject = State()
    waiting_date    = State()


# ── Main admin menu ───────────────────────────────────────
def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Barcha talabalar", callback_data="adm:all")],
        [InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="adm:stats")],
        [InlineKeyboardButton(text="👥 Guruh bo'yicha", callback_data="adm:by_group")],
        [InlineKeyboardButton(text="📚 Fan bo'yicha", callback_data="adm:by_subject")],
        [InlineKeyboardButton(text="📅 Kunlik hisobot", callback_data="adm:daily")],
        [InlineKeyboardButton(text="📆 Haftalik hisobot", callback_data="adm:weekly")],
        [InlineKeyboardButton(text="✅ O'tganlar", callback_data="adm:passed")],
        [InlineKeyboardButton(text="❌ O'tmaganlar", callback_data="adm:failed")],
        [InlineKeyboardButton(text="🏆 Baho bo'yicha", callback_data="adm:by_grade")],
        [InlineKeyboardButton(text="📥 CSV eksport", callback_data="adm:export")],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:menu")
    ]])


@router.message(Command("admin"))
async def admin_panel(msg: Message, state: FSMContext):
    await state.clear()
    if not is_admin(msg):
        return await msg.answer("❌ Sizda admin huquqlari yo'q.")
    await msg.answer("🔐 *Admin panel*", reply_markup=admin_menu_keyboard(), parse_mode="Markdown")


# ── Menu callback ─────────────────────────────────────────
@router.callback_query(F.data == "adm:menu")
async def back_to_menu(cb: CallbackQuery, state: FSMContext):
    if not is_admin_cb(cb): return
    await state.clear()
    await cb.message.edit_text("🔐 *Admin panel*", reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── All students ──────────────────────────────────────────
@router.callback_query(F.data == "adm:all")
async def show_all(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    async with get_session() as session:
        rows = (await session.execute(
            select(Submission).order_by(Submission.created_at.desc()).limit(30)
        )).scalars().all()

    if not rows:
        await cb.message.edit_text("📭 Hozircha ma'lumot yo'q.", reply_markup=back_keyboard())
        await cb.answer()
        return

    lines = ["📋 *Oxirgi 30 ta topshiriq:*\n"]
    for i, r in enumerate(rows, 1):
        icon = "✅" if r.passed == "Ha" else "❌"
        lines.append(
            f"{i}. {icon} *{r.full_name}*\n"
            f"   📚 {r.topic} | 🎓 {r.score}/10 | Baho: {r.grade}\n"
            f"   👥 {r.group} | 📅 {r.created_at.strftime('%d.%m.%Y %H:%M') if r.created_at else ''}\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n..."

    await cb.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── General stats ─────────────────────────────────────────
@router.callback_query(F.data == "adm:stats")
async def show_stats(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    async with get_session() as session:
        total   = (await session.execute(select(func.count(Submission.id)))).scalar() or 0
        passed  = (await session.execute(select(func.count(Submission.id)).where(Submission.passed == "Ha"))).scalar() or 0
        failed  = total - passed
        avg     = (await session.execute(select(func.avg(Submission.score)))).scalar()
        groups  = (await session.execute(select(func.count(distinct(Submission.group))))).scalar() or 0
        subjects = (await session.execute(select(func.count(distinct(Submission.topic))))).scalar() or 0

        # Grade breakdown
        g5 = (await session.execute(select(func.count(Submission.id)).where(Submission.grade == 5))).scalar() or 0
        g4 = (await session.execute(select(func.count(Submission.id)).where(Submission.grade == 4))).scalar() or 0
        g3 = (await session.execute(select(func.count(Submission.id)).where(Submission.grade == 3))).scalar() or 0
        g2 = (await session.execute(select(func.count(Submission.id)).where(Submission.grade == 2))).scalar() or 0

    pass_pct = round(passed / total * 100) if total else 0
    avg_str  = f"{avg:.1f}" if avg else "—"

    text = (
        "📊 *Umumiy statistika*\n\n"
        f"📝 Jami topshiriqlar: *{total}*\n"
        f"✅ O'tdi: *{passed}* ({pass_pct}%)\n"
        f"❌ O'tmadi: *{failed}*\n"
        f"⭐ O'rtacha ball: *{avg_str}/10*\n"
        f"👥 Guruhlar: *{groups}*\n"
        f"📚 Mavzular: *{subjects}*\n\n"
        "🎓 *Baholar taqsimoti:*\n"
        f"🏆 Baho 5: *{g5}* ta\n"
        f"🥈 Baho 4: *{g4}* ta\n"
        f"🥉 Baho 3: *{g3}* ta\n"
        f"❌ Baho 2: *{g2}* ta"
    )
    await cb.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── By group ──────────────────────────────────────────────
@router.callback_query(F.data == "adm:by_group")
async def show_by_group(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    async with get_session() as session:
        rows = (await session.execute(
            select(
                Submission.group,
                func.count(Submission.id).label("total"),
                func.sum((Submission.passed == "Ha").cast(int)).label("passed"),
                func.avg(Submission.score).label("avg_score"),
            ).group_by(Submission.group).order_by(Submission.group)
        )).all()

    if not rows:
        await cb.message.edit_text("📭 Ma'lumot yo'q.", reply_markup=back_keyboard())
        await cb.answer()
        return

    lines = ["👥 *Guruh bo'yicha statistika:*\n"]
    for r in rows:
        passed   = int(r.passed or 0)
        total    = int(r.total or 0)
        pct      = round(passed / total * 100) if total else 0
        avg      = f"{r.avg_score:.1f}" if r.avg_score else "—"
        lines.append(
            f"📌 *{r.group}*\n"
            f"   Jami: {total} | O'tdi: {passed} ({pct}%) | O'rtacha: {avg}\n"
        )

    await cb.message.edit_text("\n".join(lines), reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── By subject ────────────────────────────────────────────
@router.callback_query(F.data == "adm:by_subject")
async def show_by_subject(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    async with get_session() as session:
        rows = (await session.execute(
            select(
                Submission.assignment_type,
                func.count(Submission.id).label("total"),
                func.sum((Submission.passed == "Ha").cast(int)).label("passed"),
                func.avg(Submission.score).label("avg_score"),
            ).group_by(Submission.assignment_type).order_by(Submission.assignment_type)
        )).all()

    if not rows:
        await cb.message.edit_text("📭 Ma'lumot yo'q.", reply_markup=back_keyboard())
        await cb.answer()
        return

    lines = ["📚 *Topshiriq turi bo'yicha statistika:*\n"]
    for r in rows:
        passed = int(r.passed or 0)
        total  = int(r.total or 0)
        pct    = round(passed / total * 100) if total else 0
        avg    = f"{r.avg_score:.1f}" if r.avg_score else "—"
        lines.append(
            f"📌 *{r.assignment_type}*\n"
            f"   Jami: {total} | O'tdi: {passed} ({pct}%) | O'rtacha: {avg}\n"
        )

    await cb.message.edit_text("\n".join(lines), reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── Daily report ──────────────────────────────────────────
@router.callback_query(F.data == "adm:daily")
async def show_daily(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    async with get_session() as session:
        rows = (await session.execute(
            select(Submission)
            .where(Submission.created_at >= today)
            .order_by(Submission.created_at.desc())
        )).scalars().all()

    total  = len(rows)
    passed = sum(1 for r in rows if r.passed == "Ha")
    avg    = sum(r.score for r in rows if r.score) / total if total else 0

    lines = [
        f"📅 *Bugungi hisobot ({datetime.now().strftime('%d.%m.%Y')})*\n",
        f"📝 Jami: *{total}*",
        f"✅ O'tdi: *{passed}*",
        f"❌ O'tmadi: *{total - passed}*",
        f"⭐ O'rtacha: *{avg:.1f}/10*\n",
    ]

    if rows:
        lines.append("*So'nggi topshiriqlar:*")
        for r in rows[:10]:
            icon = "✅" if r.passed == "Ha" else "❌"
            lines.append(f"{icon} {r.full_name} — {r.score}/10 ({r.group})")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── Weekly report ─────────────────────────────────────────
@router.callback_query(F.data == "adm:weekly")
async def show_weekly(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    week_ago = datetime.utcnow() - timedelta(days=7)
    async with get_session() as session:
        rows = (await session.execute(
            select(Submission)
            .where(Submission.created_at >= week_ago)
            .order_by(Submission.created_at.desc())
        )).scalars().all()

    total  = len(rows)
    passed = sum(1 for r in rows if r.passed == "Ha")
    avg    = sum(r.score for r in rows if r.score) / total if total else 0
    pct    = round(passed / total * 100) if total else 0

    text = (
        f"📆 *Haftalik hisobot*\n"
        f"({(datetime.now()-timedelta(days=7)).strftime('%d.%m')} — {datetime.now().strftime('%d.%m.%Y')})\n\n"
        f"📝 Jami topshiriqlar: *{total}*\n"
        f"✅ O'tdi: *{passed}* ({pct}%)\n"
        f"❌ O'tmadi: *{total - passed}*\n"
        f"⭐ O'rtacha ball: *{avg:.1f}/10*"
    )
    await cb.message.edit_text(text, reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── Passed ────────────────────────────────────────────────
@router.callback_query(F.data == "adm:passed")
async def show_passed(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    async with get_session() as session:
        rows = (await session.execute(
            select(Submission)
            .where(Submission.passed == "Ha")
            .order_by(Submission.created_at.desc())
            .limit(30)
        )).scalars().all()

    lines = [f"✅ *O'tgan talabalar: {len(rows)} ta*\n"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. *{r.full_name}* — {r.score}/10 — Baho {r.grade} ({r.group})")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── Failed ────────────────────────────────────────────────
@router.callback_query(F.data == "adm:failed")
async def show_failed(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    async with get_session() as session:
        rows = (await session.execute(
            select(Submission)
            .where(Submission.passed == "Yo'q")
            .order_by(Submission.created_at.desc())
            .limit(30)
        )).scalars().all()

    lines = [f"❌ *O'tmagan talabalar: {len(rows)} ta*\n"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. *{r.full_name}* — {r.score}/10 ({r.group})")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── By grade ──────────────────────────────────────────────
@router.callback_query(F.data == "adm:by_grade")
async def show_by_grade(cb: CallbackQuery):
    if not is_admin_cb(cb): return

    grade_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Baho 5", callback_data="adm:grade:5")],
        [InlineKeyboardButton(text="🥈 Baho 4", callback_data="adm:grade:4")],
        [InlineKeyboardButton(text="🥉 Baho 3", callback_data="adm:grade:3")],
        [InlineKeyboardButton(text="❌ Baho 2", callback_data="adm:grade:2")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="adm:menu")],
    ])
    await cb.message.edit_text("🎓 Qaysi baho bo'yicha?", reply_markup=grade_kb)
    await cb.answer()


@router.callback_query(F.data.startswith("adm:grade:"))
async def show_grade_list(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    grade = int(cb.data.split(":")[-1])
    grade_icons = {5: "🏆", 4: "🥈", 3: "🥉", 2: "❌"}
    icon = grade_icons.get(grade, "")

    async with get_session() as session:
        rows = (await session.execute(
            select(Submission)
            .where(Submission.grade == grade)
            .order_by(Submission.created_at.desc())
            .limit(30)
        )).scalars().all()

    lines = [f"{icon} *Baho {grade} olgan talabalar: {len(rows)} ta*\n"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. *{r.full_name}* — {r.score}/10 ({r.group})")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_keyboard(), parse_mode="Markdown")
    await cb.answer()


# ── CSV export ────────────────────────────────────────────
@router.callback_query(F.data == "adm:export")
async def export_csv(cb: CallbackQuery):
    if not is_admin_cb(cb): return
    await cb.answer("CSV tayyorlanmoqda...")

    async with get_session() as session:
        rows = (await session.execute(
            select(Submission).order_by(Submission.created_at.desc())
        )).scalars().all()

    if not rows:
        await cb.message.answer("📭 Eksport qilish uchun ma'lumot yo'q.")
        return

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["ID", "Ism", "Kurs", "Guruh", "Topshiriq turi",
                "Mavzu", "Ball", "Baho", "Holat", "O'tdimi", "Vaqt"])
    for r in rows:
        w.writerow([
            r.id, r.full_name, r.course, r.group,
            r.assignment_type, r.topic,
            r.score, r.grade, r.status, r.passed,
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        ])

    buf.seek(0)
    filename = f"natijalar_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    await cb.message.answer_document(
        BufferedInputFile(buf.getvalue().encode("utf-8-sig"), filename=filename),
        caption=f"📥 {len(rows)} ta natija eksport qilindi."
    )


# ── Old commands ──────────────────────────────────────────
@router.message(Command("results"))
async def cmd_results(msg: Message):
    if not is_admin(msg): return await msg.answer("❌ Ruxsat yo'q.")
    await msg.answer("🔐 *Admin panel*", reply_markup=admin_menu_keyboard(), parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(msg: Message):
    if not is_admin(msg): return await msg.answer("❌ Ruxsat yo'q.")
    await msg.answer("🔐 *Admin panel*", reply_markup=admin_menu_keyboard(), parse_mode="Markdown")


@router.message(Command("export"))
async def cmd_export(msg: Message):
    if not is_admin(msg): return await msg.answer("❌ Ruxsat yo'q.")
    await msg.answer("🔐 *Admin panel*", reply_markup=admin_menu_keyboard(), parse_mode="Markdown")
