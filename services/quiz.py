"""
Quiz question generation using Google Gemini API.
Max 15 concurrent users — others wait with a message.
"""
import json
import re
import asyncio
import config

# ── Concurrency limiter ───────────────────────────────────
_semaphore = asyncio.Semaphore(15)   # max 15 at once
_active    = 0                        # current active count
_lock      = asyncio.Lock()


async def _get_active() -> int:
    async with _lock:
        return _active


async def _increment():
    global _active
    async with _lock:
        _active += 1


async def _decrement():
    global _active
    async with _lock:
        _active -= 1


# ── Fallback questions ────────────────────────────────────
FALLBACK_QUESTIONS = [
    {"question": "Bozor iqtisodiyotining asosiy belgisi nima?", "options": ["A) Davlat narx belgilaydi", "B) Talab va taklif narxni belgilaydi", "C) Monopoliya hukmronlik qiladi", "D) Import taqiqlangan"], "correct": 1},
    {"question": "YaIM nima?", "options": ["A) Yillik import miqdori", "B) Mamlakatda ishlab chiqarilgan tovar va xizmatlar qiymati", "C) Davlat byudjeti", "D) Eksport hajmi"], "correct": 1},
    {"question": "Inflyatsiya deganda nima tushuniladi?", "options": ["A) Narxlarning umumiy pasayishi", "B) Narxlarning umumiy o'sishi", "C) Ishsizlikning o'sishi", "D) Eksportning kamayishi"], "correct": 1},
    {"question": "Talab qonuniga ko'ra narx oshsa nima bo'ladi?", "options": ["A) Talab ortadi", "B) Talab o'zgarmaydi", "C) Talab kamayadi", "D) Taklif kamayadi"], "correct": 2},
    {"question": "Monopoliya nima?", "options": ["A) Ko'p sotuvchi bozori", "B) Bitta sotuvchi bozori", "C) Davlat bozori", "D) Xalqaro bozor"], "correct": 1},
    {"question": "Soliq nima maqsadda yig'iladi?", "options": ["A) Banklar foydasiga", "B) Davlat xarajatlarini qoplash uchun", "C) Import uchun", "D) Eksport uchun"], "correct": 1},
    {"question": "Ishsizlik koeffitsienti qanday hisoblanadi?", "options": ["A) Ishlamaganlar / Aholining hammasi", "B) Ishlamaganlar / Mehnat resurslari", "C) Ishlaganlar / Aholining hammasi", "D) Daromad / Xarajat"], "correct": 1},
    {"question": "Erkin savdo deganda nima tushuniladi?", "options": ["A) Bepul tovarlar", "B) Bojxona to'siqlarsiz savdo", "C) Davlat savdosi", "D) Mahalliy savdo"], "correct": 1},
    {"question": "Byudjet defitsiti nima?", "options": ["A) Daromad > Xarajat", "B) Daromad = Xarajat", "C) Xarajat > Daromad", "D) Eksport > Import"], "correct": 2},
    {"question": "Markaziy bank asosiy vazifasi nima?", "options": ["A) Soliq yig'ish", "B) Pul-kredit siyosatini boshqarish", "C) Import nazorati", "D) Narx belgilash"], "correct": 1},
]


async def generate_questions(topic: str, notify_msg=None) -> list:
    """
    Generate 10 MCQ questions.
    If 15 users already active, new user waits and sees waiting message.
    notify_msg: aiogram Message object to send waiting notification.
    """
    global _active

    # Check if full
    current = await _get_active()
    waiting_msg = None

    if current >= 15 and notify_msg:
        try:
            waiting_msg = await notify_msg.answer(
                "⏳ Hozirda foydalanuvchilar ko'p, kutib turing!\n\n"
                "Tez orada savollar tayyorlanadi..."
            )
        except Exception:
            pass

    # Wait for slot
    async with _semaphore:
        await _increment()
        try:
            # Delete waiting message if shown
            if waiting_msg:
                try:
                    await waiting_msg.delete()
                except Exception:
                    pass

            return await _fetch_questions(topic)
        finally:
            await _decrement()


async def _fetch_questions(topic: str) -> list:
    """Internal: actually call Gemini API."""
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY.startswith("PUT_"):
        print("[QUIZ] Gemini sozlanmagan — fallback.")
        return FALLBACK_QUESTIONS

    models = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash",
    ]

    for model in models:
        try:
            from google import genai
            client = genai.Client(api_key=config.GEMINI_API_KEY)

            prompt = (
                f'"{topic}" mavzusi bo\'yicha 10 ta test savoli tuzing.\n\n'
                f'Muhim qoidalar:\n'
                f'- Savollar FAQAT "{topic}" mavzusiga oid bo\'lsin\n'
                f'- Har bir savolda 4 ta variant (A, B, C, D)\n'
                f'- Faqat 1 ta to\'g\'ri javob bo\'lsin\n'
                f'- O\'zbek tilida bo\'lsin\n'
                f'- Talabaning bilimini haqiqiy sinashi kerak\n\n'
                f'Faqat JSON formatida javob bering, boshqa hech narsa yozmang:\n'
                f'[{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":0}}]'
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            raw = response.text.strip()

            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                raw = match.group()
            raw = re.sub(r'```json|```', '', raw).strip()

            questions = json.loads(raw)

            if isinstance(questions, list) and len(questions) >= 5:
                questions = questions[:10]
                print(f"[QUIZ] {model} — {len(questions)} savol: '{topic}'")
                return questions

        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(f"[QUIZ] {model} — limit, keyingisi...")
                continue
            elif "503" in err or "UNAVAILABLE" in err:
                print(f"[QUIZ] {model} — band, keyingisi...")
                continue
            else:
                print(f"[QUIZ] {model} xato: {e}")
                continue

    print("[QUIZ] Barcha modellar ishlamadi — fallback.")
    return FALLBACK_QUESTIONS
