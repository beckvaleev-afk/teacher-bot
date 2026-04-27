"""
Quiz question generation using Google Gemini API.
Fallback: University level questions (Bachelor 3-4 year).
"""
import json
import re
import asyncio
import config

# ── Semaphore: max 15 concurrent users ───────────────────
_semaphore = asyncio.Semaphore(15)
_active    = 0
_lock      = asyncio.Lock()

async def _increment():
    global _active
    async with _lock: _active += 1

async def _decrement():
    global _active
    async with _lock: _active -= 1

async def _get_active():
    async with _lock: return _active


# ── Fallback questions — Bachelor 3-4 year level ─────────
FALLBACK_QUESTIONS = [
    # Iqtisodiyot asoslari
    {
        "question": "Giffen tovari uchun talab egri chizig'i qanday ko'rinishga ega bo'ladi?",
        "options": ["A) Pastga qarab egilgan (oddiy)", "B) Yuqoriga qarab egilgan", "C) Gorizontal to'g'ri chiziq", "D) Vertikal to'g'ri chiziq"],
        "correct": 1
    },
    {
        "question": "Agar iste'molchi daromadi 20% oshsa va tovar talabi 10% kamaysa, bu tovar qanday tovar hisoblanadi?",
        "options": ["A) Normal tovar", "B) Giffen tovari", "C) Inferior (past sifatli) tovar", "D) Veblen tovari"],
        "correct": 2
    },
    {
        "question": "Laffer egri chizig'i qaysi ikki o'zgaruvchi o'rtasidagi bog'liqlikni ko'rsatadi?",
        "options": ["A) Inflyatsiya va ishsizlik", "B) Soliq stavkasi va soliq tushumlari", "C) YaIM o'sishi va import", "D) Foiz stavkasi va investitsiyalar"],
        "correct": 1
    },
    {
        "question": "Elastiklik koeffitsienti mutlaq qiymati 1 dan katta bo'lsa talab qanday bo'ladi?",
        "options": ["A) Noelastik", "B) Birlik elastikli", "C) Elastik", "D) Absolyut elastik"],
        "correct": 2
    },
    # Mikroiqtisodiyot
    {
        "question": "Monopolistik raqobat bozorida uzoq muddatda iqtisodiy foyda qanday bo'ladi?",
        "options": ["A) Musbat", "B) Manfiy", "C) Nolga teng", "D) O'zgaruvchan"],
        "correct": 2
    },
    {
        "question": "Cournot oligopoliyasida firmalar nimani muvozanat parametri sifatida qabul qiladi?",
        "options": ["A) Narx", "B) Raqib firmaning ishlab chiqarish hajmi", "C) Bozor ulushi", "D) Texnologiya"],
        "correct": 1
    },
    {
        "question": "Bertrand oligopoliyasida muvozanat natijasi qanday bo'ladi?",
        "options": ["A) Monopoliya narxi", "B) Kartel narxi", "C) Raqobat narxi (MC=P)", "D) Cournot narxi"],
        "correct": 2
    },
    {
        "question": "Ishlab chiqarishning qisqa muddatli davrida qaysi xarajatlar o'zgarmas qoladi?",
        "options": ["A) O'zgaruvchan xarajatlar", "B) Umumiy xarajatlar", "C) Doimiy xarajatlar", "D) Cheginal xarajatlar"],
        "correct": 2
    },
    # Makroiqtisodiyot
    {
        "question": "IS-LM modelida pul massasi oshirilsa qanday o'zgarish sodir bo'ladi?",
        "options": ["A) IS egri chizig'i o'ngga siljiydi", "B) LM egri chizig'i o'ngga siljiydi", "C) IS egri chizig'i chapga siljiydi", "D) LM egri chizig'i chapga siljiydi"],
        "correct": 1
    },
    {
        "question": "Keyns multiplikatori formulasi qaysi?",
        "options": ["A) 1/(1-MPC)", "B) 1/MPC", "C) MPC/(1-MPC)", "D) 1/(1+MPC)"],
        "correct": 0
    },
    {
        "question": "Filips egri chizig'i qisqa muddatda qaysi ikki o'zgaruvchi o'rtasidagi teskari bog'liqlikni ko'rsatadi?",
        "options": ["A) YaIM o'sishi va inflyatsiya", "B) Inflyatsiya va ishsizlik", "C) Foiz stavkasi va investitsiya", "D) Eksport va import"],
        "correct": 1
    },
    {
        "question": "Solow o'sish modelida barqaror holatda (steady state) kapital to'planishi qanday bo'ladi?",
        "options": ["A) Ijobiy o'sishda davom etadi", "B) Investitsiya amortizatsiyaga teng", "C) Kapital kamayib boradi", "D) Texnologik o'sishga bog'liq emas"],
        "correct": 1
    },
    # Moliya va bank
    {
        "question": "Duration (Dyuratsiya) obligatsiya uchun nimani o'lchaydi?",
        "options": ["A) Obligatsiya muddati", "B) Foiz stavkasi o'zgarishiga narx sezgirligi", "C) To'lov qobiliyatini", "D) Kupon daromadini"],
        "correct": 1
    },
    {
        "question": "CAPM modelida beta koeffitsienti nimani ifodalaydi?",
        "options": ["A) Umumiy risk", "B) Diversifikatsiyalanmagan (bozor) riski", "C) Firma spetsifik riski", "D) Likvidlik riski"],
        "correct": 1
    },
    {
        "question": "Modigliani-Miller teoremasi bo'yicha mukammal bozorda kapital strukturasi firmaning qiymatiga qanday ta'sir qiladi?",
        "options": ["A) Qarz ulushi ko'pganda qiymat oshadi", "B) Ta'sir qilmaydi", "C) Kapital ulushi ko'pganda qiymat oshadi", "D) Har doim optimal tuzilma mavjud"],
        "correct": 1
    },
    {
        "question": "Yield to Maturity (YTM) obligatsiya uchun qaysi parametrni ifodalaydi?",
        "options": ["A) Yillik kupon to'lovi", "B) Nominal qiymatga nisbatan daromad", "C) Obligatsiyani sotib olgandan to'laguncha kutilgan yillik daromad stavkasi", "D) Bozor narxiga nisbatan kupon foizi"],
        "correct": 2
    },
    # Xalqaro iqtisodiyot
    {
        "question": "Heckscher-Ohlin teoremasi bo'yicha mamlakat qaysi tovarni eksport qiladi?",
        "options": ["A) Eng ko'p talab qilinadigan tovar", "B) Nisbatan mo'l omil ko'p ishlatilgan tovar", "C) Eng arzon ishlab chiqariladigan tovar", "D) Texnologik jihatdan ilg'or tovar"],
        "correct": 1
    },
    {
        "question": "J-egri chizig'i effekti devalvatsiyadan keyin savdo balansining qanday o'zgarishini tushuntiradi?",
        "options": ["A) Darhol yaxshilanadi", "B) Avval yomonlashadi keyin yaxshilanadi", "C) O'zgarmaydi", "D) Doimiy yomonlashadi"],
        "correct": 1
    },
    {
        "question": "Stolper-Samuelson teoremasi tarif joriy etilganda qaysi omilga ta'sirini ifodalaydi?",
        "options": ["A) Kapital egalariga foyda beradi", "B) Import bilan raqobatlashuvchi sektorda ko'p ishlatiladigan omil egasi foyda ko'radi", "C) Barcha omil egalari foyda ko'radi", "D) Faqat iste'molchilarga foyda beradi"],
        "correct": 1
    },
    {
        "question": "Mundell-Fleming modeli qanday sharoitda qo'llaniladi?",
        "options": ["A) Yopiq iqtisodiyot, qattiq valyuta kursi", "B) Ochiq iqtisodiyot, erkin kapital harakati", "C) Faqat rivojlangan mamlakatlar uchun", "D) Yopiq iqtisodiyot, erkin valyuta kursi"],
        "correct": 1
    },
]


async def generate_questions(topic: str, notify_msg=None) -> list:
    """
    Generate 10 MCQ questions about the topic using Gemini.
    Falls back to university-level economics questions if API unavailable.
    """
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY.startswith("PUT_"):
        print("[QUIZ] Gemini sozlanmagan — fallback.")
        return _get_fallback(topic)

    current = await _get_active()
    waiting_msg = None

    if current >= 15 and notify_msg:
        try:
            waiting_msg = await notify_msg.answer(
                "⏳ Hozirda foydalanuvchilar ko'p, kutib turing!\n"
                "Tez orada savollar tayyorlanadi..."
            )
        except Exception:
            pass

    async with _semaphore:
        await _increment()
        try:
            if waiting_msg:
                try: await waiting_msg.delete()
                except Exception: pass
            return await _fetch_from_gemini(topic)
        finally:
            await _decrement()


async def _fetch_from_gemini(topic: str) -> list:
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
                f'"{topic}" mavzusi bo\'yicha Bakalavr 3-4 kurs darajasida '
                f'10 ta murakkab test savoli tuzing.\n\n'
                f'Qoidalar:\n'
                f'- Savollar FAQAT "{topic}" mavzusiga oid bo\'lsin\n'
                f'- Savollar chuqur bilim va tahliliy fikrlashni talab qilsin\n'
                f'- Har bir savolda 4 ta variant (A, B, C, D)\n'
                f'- Faqat 1 ta to\'g\'ri javob\n'
                f'- O\'zbek tilida\n\n'
                f'Faqat JSON formatida:\n'
                f'[{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":0}}]'
            )

            response = client.models.generate_content(model=model, contents=prompt)
            raw = response.text.strip()

            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match: raw = match.group()
            raw = re.sub(r'```json|```', '', raw).strip()

            questions = json.loads(raw)
            if isinstance(questions, list) and len(questions) >= 5:
                print(f"[QUIZ] {model} — {len(questions[:10])} savol: '{topic}'")
                return questions[:10]

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
    return _get_fallback(topic)


def _get_fallback(topic: str) -> list:
    """Return 10 random questions from fallback bank."""
    import random
    questions = FALLBACK_QUESTIONS.copy()
    random.shuffle(questions)
    return questions[:10]
