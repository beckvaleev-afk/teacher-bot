"""
Quiz - 1 API call per user, 10 medium-level questions about the topic.
3 keys rotate to maximize quota.
Fallback: university-level economics questions (medium level).
"""
import json
import re
import asyncio
import random
import os

GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY",   ""),
    os.getenv("GEMINI_API_KEY_2", ""),
    os.getenv("GEMINI_API_KEY_3", ""),
]

MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
]

_semaphore  = asyncio.Semaphore(15)
_active     = 0
_lock       = asyncio.Lock()
_key_index  = 0
_key_lock   = asyncio.Lock()

async def _increment():
    global _active
    async with _lock: _active += 1

async def _decrement():
    global _active
    async with _lock: _active -= 1

async def _get_active():
    async with _lock: return _active

async def _next_key() -> str:
    global _key_index
    async with _key_lock:
        keys = [k for k in GEMINI_KEYS if k and not k.startswith("PUT_")]
        if not keys:
            return ""
        key = keys[_key_index % len(keys)]
        _key_index += 1
        return key


# ── Fallback — medium level economics ────────────────────
FALLBACK_QUESTIONS = [
    {"question": "Talab elastikligi -1.5 bo'lsa, narx 10% oshirilganda talab qancha o'zgaradi?", "options": ["A) 10% kamayadi", "B) 15% kamayadi", "C) 15% ortadi", "D) 1.5% kamayadi"], "correct": 1},
    {"question": "MPC=0.8 bo'lsa, davlat xarajati 100 mln ga oshirilganda YaIM qancha o'zgaradi?", "options": ["A) 100 mln", "B) 400 mln", "C) 500 mln", "D) 800 mln"], "correct": 2},
    {"question": "Bankning majburiy zahira normasi 10% bo'lsa, pul multiplikatori qancha?", "options": ["A) 1", "B) 5", "C) 10", "D) 20"], "correct": 2},
    {"question": "Qaysi holat stagflatsiyani ifodalaydi?", "options": ["A) Yuqori o'sish + past inflyatsiya", "B) Past o'sish + yuqori inflyatsiya", "C) Yuqori o'sish + yuqori inflyatsiya", "D) Past o'sish + past inflyatsiya"], "correct": 1},
    {"question": "Xarajatlar yondashuvi bo'yicha YaIM formulasi?", "options": ["A) C + I + G + NX", "B) C + S + T", "C) W + R + P + I", "D) GDP - amortizatsiya"], "correct": 0},
    {"question": "Markaziy bank obligatsiyalarini sotib olsa nima bo'ladi?", "options": ["A) Pul massasi kamayadi", "B) Pul massasi ko'payadi", "C) Foiz stavkasi oshadi", "D) Inflyatsiya kamayadi"], "correct": 1},
    {"question": "Savdo balansi defitsitida erkin kurs rejimida milliy valyuta qanday o'zgaradi?", "options": ["A) Kuchayadi", "B) O'zgarmaydi", "C) Zaiflashadi", "D) Barqarorlashadi"], "correct": 2},
    {"question": "IS egri chizig'i nimani ifodalaydi?", "options": ["A) Pul bozori muvozanati", "B) Tovar bozori muvozanati", "C) Mehnat bozori muvozanati", "D) Valyuta bozori muvozanati"], "correct": 1},
    {"question": "Monopolistik raqobat bozorida uzoq muddatda iqtisodiy foyda qanday bo'ladi?", "options": ["A) Musbat", "B) Manfiy", "C) Nolga teng", "D) O'zgaruvchan"], "correct": 2},
    {"question": "Foiz stavkasi oshganda investitsiyalar bilan bog'liq IS egri chizig'i qanday siljiydi?", "options": ["A) O'ngga siljiydi", "B) Chapga siljiydi", "C) Siljimaydi, harakat IS bo'ylab bo'ladi", "D) Yuqoriga siljiydi"], "correct": 2},
    {"question": "Laffer egri chizig'i qaysi ikki o'zgaruvchi o'rtasidagi bog'liqlikni ko'rsatadi?", "options": ["A) Inflyatsiya va ishsizlik", "B) Soliq stavkasi va soliq tushumlari", "C) YaIM o'sishi va import", "D) Foiz stavkasi va investitsiyalar"], "correct": 1},
    {"question": "Giffen tovari uchun talab egri chizig'i qanday ko'rinishga ega?", "options": ["A) Pastga egilgan (oddiy)", "B) Yuqoriga egilgan", "C) Gorizontal", "D) Vertikal"], "correct": 1},
    {"question": "Tobin q koeffitsienti 1 dan katta bo'lsa firma qanday qaror qabul qiladi?", "options": ["A) Investitsiyani kamaytiradi", "B) Investitsiyani oshiradi", "C) Kapital sotadi", "D) Dividend to'lashni to'xtatadi"], "correct": 1},
    {"question": "Nash muvozanatida har bir o'yinchi nima qiladi?", "options": ["A) Raqib strategiyasini o'zgartiradi", "B) Raqib strategiyasiga eng yaxshi javob beradi va o'zgartirish foydali emas", "C) Hamkorlik qiladi", "D) Dominant strategiyani tanlaydi"], "correct": 1},
    {"question": "Heckscher-Ohlin teoremasi bo'yicha mamlakat qaysi tovarni eksport qiladi?", "options": ["A) Eng ko'p talab qilinadigan", "B) Nisbatan mo'l omil ko'p ishlatilgan", "C) Eng arzon ishlab chiqariladigan", "D) Texnologik jihatdan ilg'or"], "correct": 1},
    {"question": "J-egri chizig'i effekti devalvatsiyadan keyin savdo balansining qanday o'zgarishini tushuntiradi?", "options": ["A) Darhol yaxshilanadi", "B) Avval yomonlashadi keyin yaxshilanadi", "C) O'zgarmaydi", "D) Doimiy yomonlashadi"], "correct": 1},
    {"question": "Duration obligatsiya uchun nimani o'lchaydi?", "options": ["A) Obligatsiya muddati", "B) Foiz stavkasi o'zgarishiga narx sezgirligi", "C) To'lov qobiliyatini", "D) Kupon daromadini"], "correct": 1},
    {"question": "CAPM modelida beta koeffitsienti nimani ifodalaydi?", "options": ["A) Umumiy risk", "B) Bozor (diversifikatsiyalanmagan) riski", "C) Firma spetsifik riski", "D) Likvidlik riski"], "correct": 1},
    {"question": "Bertrand oligopoliyasida muvozanat natijasi qanday bo'ladi?", "options": ["A) Monopoliya narxi", "B) Kartel narxi", "C) Raqobat narxi (MC=P)", "D) Cournot narxi"], "correct": 2},
    {"question": "Solow modelida texnologik o'sish bo'lmasa aholi boshiga kapital nima bo'ladi?", "options": ["A) Cheksiz o'sadi", "B) Nolga tushadi", "C) Barqaror holatga keladi (steady state)", "D) Tsiklik o'zgaradi"], "correct": 2},
]


def _build_fallback() -> list:
    questions = FALLBACK_QUESTIONS.copy()
    random.shuffle(questions)
    return questions[:10]


async def _call_gemini(topic: str) -> list | None:
    """
    Single API call — 10 medium level questions about topic.
    Tries all keys and models before giving up.
    """
    prompt = (
        f'"{topic}" mavzusi bo\'yicha O\'rta daraja (medium level) '
        f'Bakalavr 3-4 kurs uchun 10 ta test savoli tuzing.\n\n'
        f'Qoidalar:\n'
        f'- Savollar FAQAT "{topic}" mavzusiga oid bo\'lsin\n'
        f'- O\'rta qiyinlikda: juda oson ham, juda qiyin ham bo\'lmasin\n'
        f'- Tushunish, tahlil va qo\'llash ko\'nikmalarini sinashi kerak\n'
        f'- Har bir savolda 4 ta variant (A, B, C, D)\n'
        f'- Faqat 1 ta to\'g\'ri javob\n'
        f'- O\'zbek tilida\n\n'
        f'Faqat JSON formatida, boshqa hech narsa yozmang:\n'
        f'[{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"correct":0}}]'
    )

    keys = [k for k in GEMINI_KEYS if k and not k.startswith("PUT_")]
    if not keys:
        return None

    for key in keys:
        for model in MODELS:
            try:
                from google import genai
                client   = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model=model, contents=prompt
                )
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
                    print(f"[QUIZ] {model} key limit, next...")
                    continue
                elif "503" in err or "UNAVAILABLE" in err:
                    print(f"[QUIZ] {model} unavailable, next...")
                    continue
                else:
                    print(f"[QUIZ] {model} error: {e}")
                    continue

    return None


async def generate_questions(topic: str, notify_msg=None) -> list:
    keys = [k for k in GEMINI_KEYS if k and not k.startswith("PUT_")]
    if not keys:
        print("[QUIZ] No API keys — fallback")
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

            questions = await _call_gemini(topic)

            if not questions:
                print("[QUIZ] All keys failed — fallback")
                return _build_fallback()

            return questions
        finally:
            await _decrement()
