import csv
import io
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from sqlalchemy import select, func

from database.db import get_session
from database.models import Submission
import config

router = Router()


def is_admin(msg: Message) -> bool:
    return msg.from_user.id == config.ADMIN_ID


# ── /admin ────────────────────────────────────────────────
@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not is_admin(msg):
        return await msg.answer("❌ Sizda admin huquqlari yo'q.")
    await msg.answer(
        "🔐 *Admin panel*\n\n"
        "/results — Oxirgi 20 natija\n"
        "/stats   — Umumiy statistika\n"
        "/export  — CSV fayl yuklash\n",
        parse_mode="Markdown"
    )


# ── /results ─────────────────────────────────────────────
@router.message(Command("results"))
async def show_results(msg: Message):
    if not is_admin(msg):
        return await msg.answer("❌ Ruxsat yo'q.")

    async with get_session() as session:
        rows = (await session.execute(
            select(Submission)
            .order_by(Submission.created_at.desc())
            .limit(20)
        )).scalars().all()

    if not rows:
        return await msg.answer("📭 Hozircha natijalar yo'q.")

    lines = ["📋 *Oxirgi 20 ta natija:*\n"]
    for i, r in enumerate(rows, 1):
        status_icon = "✅" if r.passed == "Ha" else "❌"
        lines.append(
            f"{i}. {status_icon} *{r.full_name}*\n"
            f"   Kurs: {r.course} | Guruh: {r.group}\n"
            f"   Tur: {r.assignment_type}\n"
            f"   Ball: {r.score}/10 | Baho: {r.grade}\n"
            f"   {r.created_at.strftime('%d.%m.%Y %H:%M') if r.created_at else ''}\n"
        )

    await msg.answer("\n".join(lines), parse_mode="Markdown")


# ── /stats ────────────────────────────────────────────────
@router.message(Command("stats"))
async def show_stats(msg: Message):
    if not is_admin(msg):
        return await msg.answer("❌ Ruxsat yo'q.")

    async with get_session() as session:
        total = (await session.execute(
            select(func.count(Submission.id))
        )).scalar() or 0

        passed = (await session.execute(
            select(func.count(Submission.id))
            .where(Submission.passed == "Ha")
        )).scalar() or 0

        avg_score = (await session.execute(
            select(func.avg(Submission.score))
        )).scalar()

    failed    = total - passed
    avg_str   = f"{avg_score:.1f}" if avg_score else "—"
    pass_pct  = round((passed / total * 100)) if total else 0

    await msg.answer(
        "📊 *Umumiy statistika*\n\n"
        f"Jami topshiriqlar: *{total}*\n"
        f"O'tdi: *{passed}* ({pass_pct}%)\n"
        f"O'tmadi: *{failed}*\n"
        f"O'rtacha ball: *{avg_str}/10*",
        parse_mode="Markdown"
    )


# ── /export ───────────────────────────────────────────────
@router.message(Command("export"))
async def export_csv(msg: Message):
    if not is_admin(msg):
        return await msg.answer("❌ Ruxsat yo'q.")

    async with get_session() as session:
        rows = (await session.execute(
            select(Submission).order_by(Submission.created_at.desc())
        )).scalars().all()

    if not rows:
        return await msg.answer("📭 Eksport qilish uchun ma'lumot yo'q.")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Telegram ID", "Ism", "Kurs", "Guruh",
        "Topshiriq turi", "Mavzu", "Fayl URL",
        "Ball", "Baho", "Holat", "O'tdimi", "Vaqt"
    ])
    for r in rows:
        writer.writerow([
            r.id, r.telegram_id, r.full_name, r.course, r.group,
            r.assignment_type, r.topic, r.file_url or "",
            r.score, r.grade, r.status, r.passed,
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        ])

    buf.seek(0)
    filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    await msg.answer_document(
        BufferedInputFile(buf.getvalue().encode("utf-8-sig"), filename=filename),
        caption=f"📥 {len(rows)} ta natija eksport qilindi."
    )
