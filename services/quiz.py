"""
Quiz question generation using 3 Gemini API keys.
10 questions: 5 high + 3 medium + 2 hard (all topic-specific).
Fallback: Economics university-level questions same distribution.
"""
import json
import re
import asyncio
import random
import os

# ── 3 API Keys ────────────────────────────────────────────
GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY",   ""),
    os.getenv("GEMINI_API_KEY_2", ""),
    os.getenv("GEMINI_API_KEY_3", ""),
]

# ── Semaphore: max 15 concurrent ─────────────────────────
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


# ══════════════════════════════════════════════════════════
#  FALLBACK — O'RTA DARAJA (3 ta ishlatiladi)
# ══════════════════════════════════════════════════════════
FALLBACK_MEDIUM = [
    {
        "question": "Talab elastikligi koeffitsienti -1.5 bo'lsa, narx 10% oshirilganda talab qancha o'zgaradi?",
        "options": ["A) 10% kamayadi", "B) 15% kamayadi", "C) 15% ortadi", "D) 1.5% kamayadi"],
        "correct": 1
    },
    {
        "question": "Multiplikator effekti bo'yicha MPC=0.8 bo'lsa, davlat xarajati 100 mln ga oshirilganda YaIM qancha o'zgaradi?",
        "options": ["A) 100 mln", "B) 400 mln", "C) 500 mln", "D) 800 mln"],
        "correct": 2
    },
    {
        "question": "Foiz stavkasi oshganda investitsiyalar bilan bog'liq IS egri chizig'i qanday siljiydi?",
        "options": ["A) O'ngga siljiydi", "B) Chapga siljiydi", "C) Siljimaydi, harakat IS bo'ylab bo'ladi", "D) Yuqoriga siljiydi"],
        "correct": 2
    },
    {
        "question": "Savdo balansi defitsiti bo'lganda milliy valyuta kursi qanday o'zgaradi (erkin kurs rejimida)?",
        "options": ["A) Kuchayadi", "B) O'zgarmaydi", "C) Zaiflashadi", "D) Barqarorlashadi"],
        "correct": 2
    },
    {
        "question": "Bankning majburiy zahira normasi 10% bo'lsa, pul multiplikatori qancha?",
        "options": ["A) 1", "B) 5", "C) 10", "D) 20"],
        "correct": 2
    },
    {
        "question": "Qaysi holat stagflatsiyani ifodalaydi?",
        "options": ["A) Yuqori o'sish + past inflyatsiya", "B) Past o'sish + yuqori inflyatsiya", "C) Yuqori o'sish + yuqori inflyatsiya", "D) Past o'sish + past inflyatsiya"],
        "correct": 1
    },
    {
        "question": "Xarajatlar yondashuvi bo'yicha YaIM qanday hisoblanadi?",
        "options": ["A) C + I + G + NX", "B) C + S + T", "C) W + R + P + I", "D) GDP - amortizatsiya"],
        "correct": 0
    },
    {
        "question": "Markaziy bank ochiq bozor operatsiyalarida davlat obligatsiyalarini sotib olsa nima bo'ladi?",
        "options": ["A) Pul massasi kamayadi", "B) Pul massasi ko'payadi", "C) Foiz stavkasi oshadi", "D) Inflyatsiya kamayadi"],
        "correct": 1
    },
]

# ══════════════════════════════════════════════════════════
#  FALLBACK — YUQORI DARAJA (5 ta ishlatiladi)
# ══════════════════════════════════════════════════════════
FALLBACK_HIGH = [
    {
        "question": "Mundell-Fleming modelida kichik ochiq iqtisodiyotda qattiq valyuta kursida fiskal siyosatning samaradorligi qanday?",
        "options": ["A) Juda yuqori", "B) Nolga teng (to'liq siqib chiqarish)", "C) O'rtacha", "D) Pul siyosatiga teng"],
        "correct": 1
    },
    {
        "question": "Ricardian ekvivalentlik teoremasi qaysi holatni bashorat qiladi?",
        "options": ["A) Byudjet defitsiti inflyatsiyani oshiradi", "B) Davlat qarzlari xususiy jamg'armaga ta'sir qilmaydi", "C) Soliq kamaytirish iste'molni ko'paytiradi", "D) Davlat xarajatlari multiplikator orqali ishlaydi"],
        "correct": 1
    },
    {
        "question": "Arrow-Debreu modelida umumiy muvozanat uchun qanday shart zarur?",
        "options": ["A) Monopoliya mavjud bo'lmasligi", "B) Barcha bozorlar bir vaqtda tozalanishi", "C) Davlat aralashuvi", "D) Faqat tovar bozorlari muvozanati"],
        "correct": 1
    },
    {
        "question": "Optimal valyuta zonasi (Mundell) mezonlari qaysilar?",
        "options": ["A) Bir xil inflyatsiya va foiz stavkasi", "B) Omillar harakatchanligi, simmetrik shoklar, byudjet mexanizmi", "C) Bir xil soliq tizimi", "D) Umumiy Markaziy bank va bir xil narxlar"],
        "correct": 1
    },
    {
        "question": "Solow modelida texnologik o'sish (g) bo'lmasa uzoq muddatda aholi boshiga kapital nima bo'ladi?",
        "options": ["A) Cheksiz o'sadi", "B) Nolga tushadi", "C) Barqaror holatga keladi (steady state)", "D) Tsiklik o'zgaradi"],
        "correct": 2
    },
    {
        "question": "Tobin q koeffitsienti 1 dan katta bo'lsa firma qanday qaror qabul qiladi?",
        "options": ["A) Investitsiyani kamaytiradi", "B) Investitsiyani oshiradi", "C) Kapital sotadi", "D) Dividend to'lashni to'xtatadi"],
        "correct": 1
    },
    {
        "question": "Nash muvozanatida har bir o'yinchi nima qiladi?",
        "options": ["A) Raqib strategiyasini o'zgartiradi", "B) Raqib strategiyasiga eng yaxshi javob beradi va o'zgartirish foydali emas", "C) Hamkorlik qiladi", "D) Dominant strategiyani tanlaydi"],
        "correct": 1
    },
    {
        "question": "Ramsey-Cass-Koopmans modelida iste'molchi optimalligi qaysi shartga asoslanadi?",
        "options": ["A) MPC doimiy", "B) Euler tenglamasi: iste'mol o'sish sur'ati foiz stavkasi va vaqt imtiyoz stavkasiga bog'liq", "C) Barcha daromad iste'mol qilinadi", "D) Jamg'arma nolga teng"],
        "correct": 1
    },
]

# ══════════════════════════════════════════════════════════
#  FALLBACK — QIYIN DARAJA (2 ta ishlatiladi)
# ══════════════════════════════════════════════════════════
FALLBACK_HARD = [
    {
        "question": "Diamond-Dybvig modeli bank panikasini qanday tushuntiradi va yechim sifatida nimani taklif qiladi?",
        "options": [
            "A) Banklar yetarli kapital ushlamaydi; yechim — kapital talablari",
            "B) Ko'p muvozanat mavjud; depozitlarni sug'urtalash panikagarchi muvozanatni yo'q qiladi",
            "C) Markaziy bank foiz stavkasini oshirishi kerak",
            "D) Banklar o'rtasida raqobat kuchaytirilishi kerak"
        ],
        "correct": 1
    },
    {
        "question": "Kaldor-Hiks samaradorligi Pareto samaradorligidan qanday farq qiladi?",
        "options": [
            "A) Kaldor-Hiks faqat ishlab chiqarish samaradorligini o'lchaydi",
            "B) Kaldor-Hiks g'oliblar mag'lublarni nazariy kompensatsiya qila olishi shartini qo'yadi, haqiqiy kompensatsiyasiz",
            "C) Kaldor-Hiks faqat tovar bozorlariga qo'llaniladi",
            "D) Ikkalasi bir xil, faqat terminologiya farqli"
        ],
        "correct": 1
    },
    {
        "question": "Real biznes tsikli (RBC) nazariyasi iqtisodiy tsikllarni qanday izohlaydi?",
        "options": [
            "A) Talab shoklar va narx yopishqoqligi orqali",
            "B) Texnologik shoklar va uy xo'jaliklari optimal javoblari orqali",
            "C) Pul massasi o'zgarishlari orqali",
            "D) Davlat xarajatlari multiplikatori orqali"
        ],
        "correct": 1
    },
    {
        "question": "Mirrlees optimal soliq nazariyasida yuqori daromadlilarga nima uchun 100% chegara soliq stavkasi optimal emas?",
        "options": [
            "A) Siyosiy jihatdan qabul qilinmaydi",
            "B) Axborot assimetriyasi va mehnat taklifi distorsiyasi tufayli incentive muammosi yuzaga keladi",
            "C) Kapital qochib ketadi",
            "D) Konstitutsiyaga zid"
        ],
        "correct": 1
    },
    {
        "question": "Grossman-Hart-Moore to'liqsiz shartnomalar nazariyasida mulkchilik huquqi qanday rol o'ynaydi?",
        "options": [
            "A) Faqat yuridik himoya beradi",
            "B) Shartnomada ko'zda tutilmagan holatlarda qaror qabul qilish huquqini belgilaydi va investitsiya incentivlarini shakllantiradi",
            "C) Soliq majburiyatlarini belgilaydi",
            "D) Bozor monopoliyasini kafolatlaydi"
        ],
        "correct": 1
    },
]


def _build_fallback() -> list:
    """Build 10 fallback questions: 5 high + 3 medium + 2 hard."""
    high   = random.sample(FALLBACK_HIGH,   min(5, len(FALLBACK_HIGH)))
    medium = random.sample(FALLBACK_MEDIUM, min(3, len(FALLBACK_MEDIUM)))
    hard   = random.sample(FALLBACK_HARD,   min(2, len(FALLBACK_HARD)))
    combined = high + medium + hard
    random.shuffle(combined)
    return combined[:10]


# ══════════════════════════════════════════════════════════
#  GEMINI CALL with rotating keys
# ══════════════════════════════════════════════════════════
MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
]


def _make_prompt(topic: str, level: str, count: int) -> str:
    level_desc = {
        "high":   "yuqori daraja — tahliliy va amaliy savollar",
        "medium": "o'rta daraja — tushunish va qo'llash",
        "hard":   "qiyin daraja — murakkab, ko'p qadamli tahlil",
    }
    return (
        f'"{topic}" mavzusi bo\'yicha {level_desc[level]} darajasida '
        f'{count} ta test savoli tuzing.\n\n'
        f'Qoidalar:\n'
        f'- Savollar FAQAT "{topic}" mavzusiga oid bo\'lsin\n'
        f'- Bakalavr 3-4 kurs darajasi\n'
        f'- Har bir savolda 4 ta variant (A, B, C, D)\n'
        f'- Faqat 1 ta to\'g\'ri javob\n'
        f'- O\'zbek tilida\n\n'
        f'Faqat JSON formatida, boshqa hech narsa yozmang:\n'
        f'[{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":0}}]'
    )


async def _call_gemini(api_key: str, prompt: str) -> list | None:
    """Try all models with one API key."""
    if not api_key or api_key.startswith("PUT_"):
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for model in MODELS:
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt
                )
                raw = response.text.strip()
                match = re.search(r'\[.*\]', raw, re.DOTALL)
                if match: raw = match.group()
                raw = re.sub(r'```json|```', '', raw).strip()
                questions = json.loads(raw)
                if isinstance(questions, list) and len(questions) >= 1:
                    return questions
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    print(f"[QUIZ] {model} key limit, next model...")
                    continue
                elif "503" in err or "UNAVAILABLE" in err:
                    print(f"[QUIZ] {model} unavailable, next model...")
                    continue
                else:
                    print(f"[QUIZ] {model} error: {e}")
                    continue
    except Exception as e:
        print(f"[QUIZ] Key error: {e}")
    return None


async def _fetch_by_level(topic: str, level: str, count: int) -> list:
    """
    Try all 3 keys for a specific level prompt.
    Returns empty list if all keys exhausted.
    """
    prompt = _make_prompt(topic, level, count)
    keys   = [k for k in GEMINI_KEYS if k and not k.startswith("PUT_")]

    for key in keys:
        result = await _call_gemini(key, prompt)
        if result:
            print(f"[QUIZ] Got {len(result)} {level} questions for '{topic}'")
            return result[:count]

    print(f"[QUIZ] All keys exhausted for level={level}")
    return []


async def _fetch_all_levels(topic: str) -> list:
    """
    Fetch 5 high + 3 medium + 2 hard questions about topic.
    Uses different API keys for different levels to maximize quota.
    """
    # Rotate keys per level to distribute load
    keys = [k for k in GEMINI_KEYS if k and not k.startswith("PUT_")]
    if not keys:
        return []

    # Fetch all 3 levels concurrently
    high_task   = asyncio.create_task(_fetch_by_level(topic, "high",   5))
    medium_task = asyncio.create_task(_fetch_by_level(topic, "medium", 3))
    hard_task   = asyncio.create_task(_fetch_by_level(topic, "hard",   2))

    high, medium, hard = await asyncio.gather(high_task, medium_task, hard_task)

    # Fill missing with fallback of same level
    if len(high) < 5:
        needed = 5 - len(high)
        high  += random.sample(FALLBACK_HIGH, min(needed, len(FALLBACK_HIGH)))

    if len(medium) < 3:
        needed  = 3 - len(medium)
        medium += random.sample(FALLBACK_MEDIUM, min(needed, len(FALLBACK_MEDIUM)))

    if len(hard) < 2:
        needed = 2 - len(hard)
        hard  += random.sample(FALLBACK_HARD, min(needed, len(FALLBACK_HARD)))

    combined = high[:5] + medium[:3] + hard[:2]
    random.shuffle(combined)
    print(f"[QUIZ] Final: {len(high[:5])} high + {len(medium[:3])} medium + {len(hard[:2])} hard")
    return combined[:10]


# ══════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════
async def generate_questions(topic: str, notify_msg=None) -> list:
    keys = [k for k in GEMINI_KEYS if k and not k.startswith("PUT_")]
    if not keys:
        print("[QUIZ] No API keys — using fallback")
        return _build_fallback()

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

            questions = await _fetch_all_levels(topic)

            if not questions:
                print("[QUIZ] All Gemini keys failed — full fallback")
                return _build_fallback()

            return questions
        finally:
            await _decrement()
