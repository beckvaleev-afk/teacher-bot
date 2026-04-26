def calculate_grade(correct: int, total: int = 10) -> dict:
    if correct >= 9:
        grade      = 5
        status     = "A'lo (Excellent)"
        grade_emoji = "🏆"
        passed     = True
    elif correct >= 7:
        grade      = 4
        status     = "Yaxshi (Good)"
        grade_emoji = "🥈"
        passed     = True
    elif correct == 6:
        grade      = 3
        status     = "Qoniqarli (Satisfactory)"
        grade_emoji = "🥉"
        passed     = True
    else:
        grade      = 2
        status     = "Qoniqarsiz (Failed)"
        grade_emoji = "❌"
        passed     = False

    percentage = round((correct / total) * 100)

    # Result emoji based on percentage
    if percentage == 100:
        result_emoji = "🌟"
    elif percentage >= 90:
        result_emoji = "⭐"
    elif percentage >= 70:
        result_emoji = "👍"
    elif percentage >= 60:
        result_emoji = "📋"
    else:
        result_emoji = "📚"

    return {
        "score":        correct,
        "total":        total,
        "percentage":   percentage,
        "grade":        grade,
        "status":       status,
        "emoji":        grade_emoji,
        "result_emoji": result_emoji,
        "passed":       passed,
    }


def format_result_message(result: dict, student_name: str) -> str:
    emoji       = result["emoji"]
    res_emoji   = result["result_emoji"]
    score       = result["score"]
    total       = result["total"]
    pct         = result["percentage"]
    grade       = result["grade"]
    status      = result["status"]

    lines = [
        f"🏆 *Natija — {student_name}*",
        "",
        f"To'g'ri javoblar: *{score}/{total}* ({pct}%) {res_emoji}",
        f"Baho: *{grade}* — {status}",
        "",
    ]
    if result["passed"]:
        lines.append("✅ Topshiriq muvaffaqiyatli topshirildi!")
    else:
        lines.append("❌ Topshiriq qabul qilinmadi.")
        lines.append("Iltimos, mavzuni takrorlab, qayta topshiring.")
    return "\n".join(lines)
