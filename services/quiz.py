"""
Quiz - Gemini API (3 keys) first, fallback 100-question bank.
10 medium-level questions per user.
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
#  100-QUESTION FALLBACK BANK
#  Makroiqtisodiyot (50) + Global iqtisodiy rivojlanish (50)
#  O'rta: 70% | Qiyin: 30%
# ══════════════════════════════════════════════════════════
FALLBACK_QUESTIONS = [
    # ── MAKROIQTISODIYOT ─────────────────────────────────
    {"question": "Nominal YaIM va real YaIM o'rtasidagi farq nimada?", "options": ["A) Nominal YaIM — joriy narxlarda, real YaIM — bazis yil narxlarida hisoblanadi", "B) Nominal YaIM — faqat mahalliy tovarlar, real YaIM — import ham kiritilgan", "C) Nominal YaIM — aholi soni bilan bo'linadi, real YaIM — emas", "D) Nominal va real YaIM bir xil, faqat hisoblash usuli farq qiladi"], "correct": 0},
    {"question": "YaIM deflyatori nima?", "options": ["A) Narx o'zgarishini hisobga oluvchi, nominal YaIMni real YaIMga aylantirish koeffitsienti", "B) Faqat iste'mol tovarlariga narx indeksi", "C) Eksport narxlarining o'rtacha ko'rsatkichi", "D) Davlat xarajatlarini YaIMga nisbati"], "correct": 0},
    {"question": "Yalpi milliy mahsulot (YaMM) YaIMdan qanday farq qiladi?", "options": ["A) YaMM — milliy rezidentlar tomonidan ishlab chiqarilgan mahsulot (xorijda ham), YaIM — faqat mamlakat hududida ishlab chiqarilgan", "B) YaMM faqat davlat korxonalari mahsulotini o'lchaydi", "C) YaMM inflyatsiya ta'sirini hisobga oladi, YaIM olmaydi", "D) YaMM va YaIM bir xil ko'rsatkich, faqat nomlanishi farqli"], "correct": 0},
    {"question": "Iqtisodiy rifoh (well-being) ni YaIM to'liq ifodalay olmaydigan asosiy sabab nima?", "options": ["A) YaIM faqat mahalliy valyutada o'lchanadi", "B) YaIM bozor operatsiyalari bo'lmagan mahsulot va xizmatlarni, tashqi ta'sirlarni, daromad taqsimotini va bo'sh vaqt qiymatini inobatga olmaydi", "C) YaIM faqat bir yil uchun hisoblanadi", "D) YaIM korxonalar foydasini ikki marta hisoblaydi"], "correct": 1},
    {"question": "Biznes sikli (iqtisodiy tebranish) fazalari qaysilar?", "options": ["A) Inflyatsiya, deflatsiya, stagflyatsiya, giperinflyatsiya", "B) Yuksalish (expansion), cho'qqi (peak), tanazzul (recession), tub (trough)", "C) O'sish, barqarorlik, inqiroz, tiklanish, barqarorlik", "D) Boom, bum, bust, rebound"], "correct": 1},
    {"question": "Friktsion ishsizlik nima?", "options": ["A) Texnologik o'zgarishlar sababli ish o'rnini yo'qotish", "B) Ish qidirayotgan va ish takliflari o'rtasidagi vaqtinchalik nomuvofiqlik", "C) Iqtisodiy pasayish davrida ish o'rnlarining yo'qolishi", "D) Malaka darajasi past bo'lganligi uchun ishga joylasha olmaslik"], "correct": 1},
    {"question": "Okun qonuniga ko'ra ishsizlik darajasi 1% oshsa, YaIM qancha yo'qotadi?", "options": ["A) YaIM 0.5% kamayadi", "B) YaIM taxminan 2% kamayadi", "C) YaIM 5% kamayadi", "D) YaIM o'zgarmaydi"], "correct": 1},
    {"question": "Mehnat bozorida 'hysteresis' effekti nimani anglatadi?", "options": ["A) Ish haqi moslashuvchanligi tufayli ishsizlik tez kamayadi", "B) Qisqa muddatli ishsizlik uzoq muddatli tabiiy ishsizlik darajasiga doimiy ta'sir ko'rsatadi", "C) Yosh ishchilar keksa ishchilarga qaraganda tezroq ish topadi", "D) Ishsizlik va inflyatsiya o'rtasidagi munosabat uzoq muddatda vertikal bo'ladi"], "correct": 1},
    {"question": "Talabga asoslangan inflyatsiya (demand-pull) qachon paydo bo'ladi?", "options": ["A) Xom ashyo narxlari oshganda", "B) Yalpi talab yalpi taklifdan oshib ketganda", "C) Valyuta qadrsizlanganda", "D) Monopoliya narxlarni ko'targanda"], "correct": 1},
    {"question": "Stagflyatsiya deganda nima tushuniladi?", "options": ["A) Yuqori o'sish va past inflyatsiya bir vaqtda", "B) Past ishsizlik va yuqori o'sish", "C) Bir vaqtda yuqori inflyatsiya va yuqori ishsizlik (iqtisodiy tanazzul)", "D) Inflyatsiyaning keskin pasayishi"], "correct": 2},
    {"question": "Qisqa muddatli Filips egri chizig'i nimani ko'rsatadi?", "options": ["A) Inflyatsiya va iqtisodiy o'sish o'rtasidagi to'g'ri bog'liqlik", "B) Inflyatsiya va ishsizlik o'rtasidagi teskari munosabat", "C) Pul taklifi va inflyatsiya o'rtasidagi munosabat", "D) Soliq va inflyatsiya o'rtasidagi bog'liqlik"], "correct": 1},
    {"question": "Phelps-Fridman tanqidiga ko'ra uzoq muddatli Filips egri chizig'i qanday ko'rinishda bo'ladi?", "options": ["A) Gorizontal — inflyatsiya ishsizlikka ta'sir qilmaydi", "B) Vertikal — tabiiy ishsizlik darajasida; uzoq muddatda inflyatsiyani kamaytirish uchun ishsizlikni oshirish kerak emas", "C) Pastga qiyshaygan — uzoq muddatda ham almashuv mavjud", "D) Yuqoriga ko'tariluvchi — inflyatsiya oshganda ishsizlik ham oshadi"], "correct": 1},
    {"question": "Yalpi talab (AD) egri chizig'i nima sababdan pastga qiyshaygan?", "options": ["A) Narx oshganda xaridorlar arzonroq xorijiy tovarlar sotib oladi, pul qiymati pasayadi, foiz stavkasi oshib investitsiyalar kamayadi", "B) Narx oshganda ish haqi ham oshadi", "C) Narx oshganda davlat xarajatlari kamayadi", "D) Narx oshganda eksport ko'payadi"], "correct": 0},
    {"question": "Qisqa muddatli yalpi taklif (SRAS) egri chizig'i nima sababdan yuqoriga qiyshaygan?", "options": ["A) Korxonalar ko'proq daromad olish uchun narxlarni oshiradi", "B) Narxlar oshganda ish haqi va xomashyo narxlari qisqa muddatda o'zgarmaydi, shuning uchun foyda oshib, ishlab chiqarish kengayadi", "C) Hukumat narxlarni tartibga soladi", "D) Import narxlari oshganda mahalliy taklif ortadi"], "correct": 1},
    {"question": "Supply shock (taklif zarbasi) AD-AS modelida qanday ko'rinadi?", "options": ["A) AD egri chizig'i chapga siljiydi", "B) SRAS egri chizig'i chapga siljib, narx oshadi va YaIM kamayadi", "C) LRAS egri chizig'i o'ngga siljiydi", "D) AD va SRAS bir vaqtda o'ngga siljiydi"], "correct": 1},
    {"question": "AD-AS modelida Keyns va klassik yondashuvlar o'rtasidagi asosiy farq nimada?", "options": ["A) Keyns uzoq muddatni, klassiklar qisqa muddatni tahlil qiladi", "B) Keyns narx va ish haqining pastga moslashmasligi sababli SRAS gorizontal bo'lishini, klassiklar esa narxlar moslashuvchan bo'lgani uchun LRAS vertikal ekanini ta'kidlaydi", "C) Keyns savdo balansiga e'tibor bersa, klassiklar faqat ichki bozorni ko'radi", "D) Keyns inflyatsiyani yaxshi, klassiklar yomon deb biladi"], "correct": 1},
    {"question": "Iste'molga chegaraviy moyillik (MPC) nima?", "options": ["A) Daromadning qancha qismi soliqqa tortiladi", "B) Qo'shimcha 1 birlik daromadning qancha qismi iste'molga sarflanishi", "C) Iste'mol va jamg'armaning yalpi nisbati", "D) Investitsiyalarning iste'molga ta'sir koeffitsienti"], "correct": 1},
    {"question": "Keyns multiplikatori formulasi qanday hisoblanadi?", "options": ["A) 1 / (1 - MPC) yoki 1 / MPS", "B) MPC × MPS", "C) 1 / foiz stavkasi", "D) YaIM / investitsiya"], "correct": 0},
    {"question": "'Paradox of thrift' (jamg'arma paradoksi) nimani ifodalaydi?", "options": ["A) Ko'p jamg'arsa, bank foydalari oshib, iqtisodiyot o'sadi", "B) Barcha uy xo'jaliklari bir vaqtda jamg'armasini oshirishga harakat qilsa, umumiy talab va YaIM kamayib, jamg'arma oshmaydi", "C) Investitsiyalar ko'paygan sari iste'mol ortadi", "D) Jamg'arma inflyatsiyani kamaytiradi"], "correct": 1},
    {"question": "Keyns modelida muvozanat YaIM qanday aniqlanadi?", "options": ["A) Narxlar muvozanati orqali", "B) Yalpi xarajatlar (AE) yalpi mahsulotga (YaIM) teng bo'lganda", "C) Eksport importga teng bo'lganda", "D) Davlat byudjeti balansda bo'lganda"], "correct": 1},
    {"question": "Injeksiya (injection) va chiqib ketish (leakage) qaysilar?", "options": ["A) Injeksiya: soliqlar, import, jamg'arma; Chiqib ketish: investitsiyalar, eksport, davlat xarajatlari", "B) Injeksiya: investitsiyalar, davlat xarajatlari, eksport; Chiqib ketish: jamg'arma, soliqlar, import", "C) Injeksiya: iste'mol; Chiqib ketish: barcha boshqa xarajatlar", "D) Injeksiya: soliqlar; Chiqib ketish: subsidiyalar"], "correct": 1},
    {"question": "Keyns modelida 'deflyatsion bo'shliq' (deflationary gap) nima va uni yopish uchun qanday siyosat zarur?", "options": ["A) Haqiqiy YaIM potentsial YaIMdan past bo'lganda paydo bo'ladi; uni yopish uchun ekspansionar fiskal yoki pul siyosati zarur", "B) Inflyatsiya yuqori bo'lganda narxlar va YaIM o'rtasida vujudga keladi", "C) Eksport importdan past bo'lganda savdo balansida yuzaga keladi", "D) Davlat byudjet taqchilligi yalpi talabdan past bo'lganda hosil bo'ladi"], "correct": 0},
    {"question": "Avtomatik stabilizatorlar qanday ishlaydi?", "options": ["A) Markaziy bank foiz stavkasini o'zgartiradi", "B) Iqtisodiy pasayishda ijtimoiy to'lovlar oshib, soliq daromadlari kamayib, talab o'z-o'zidan qo'llab-quvvatlanadi", "C) Hukumat maxsus qonun qabul qilib xarajatlarni oshiradi", "D) Eksport subsidiyalari avtomatik oshiriladi"], "correct": 1},
    {"question": "Davlat qarzi va byudjet taqchilligi o'rtasidagi farq nima?", "options": ["A) Bular bir xil tushuncha", "B) Byudjet taqchilligi — bir yillik farq (xarajat > daromad), davlat qarzi — barcha yillar taqchilliklarining yig'indisi", "C) Davlat qarzi faqat xorijiy kreditlardan iborat", "D) Byudjet taqchilligi faqat harbiy xarajatlar sababli paydo bo'ladi"], "correct": 1},
    {"question": "Ekspansionar fiskal siyosat deganda nima tushuniladi?", "options": ["A) Davlat xarajatlarini qisqartirish va soliqlarni oshirish", "B) Davlat xarajatlarini oshirish va/yoki soliqlarni kamaytirish orqali yalpi talabni rag'batlantirish", "C) Markaziy bank pul massasini qisqartirishi", "D) Import bojlarini oshirish"], "correct": 1},
    {"question": "'Crowding out' (siqib chiqarish) effekti nima?", "options": ["A) Davlat xarajatlari oshganda inflyatsiya ko'tariladi va bu eksportni qisqartiradi", "B) Hukumat qarz olganda foiz stavkasi oshib, xususiy investitsiyalar kamayadi — davlat xarajatlarining bir qismi xususiy sektordagi investitsiyalarni siqib chiqaradi", "C) Import ko'payishi mahalliy ishlab chiqaruvchilarni bozordan siqib chiqaradi", "D) Soliq oshishi iste'molchi xarajatlarini kamaytiradi"], "correct": 1},
    {"question": "Majburiy zaxira talablari (reserve requirements) pul taklifiga qanday ta'sir qiladi?", "options": ["A) Zaxira talabi oshirilsa, banklar ko'proq kredit bera oladi", "B) Zaxira talabi oshirilsa, banklar kam kredit beradi, pul taklifi kamayadi", "C) Zaxira talabi pul taklifiga ta'sir qilmaydi", "D) Zaxira talabi faqat inflyatsiyaga ta'sir qiladi"], "correct": 1},
    {"question": "Pul miqdori nazariyasida MV = PQ tenglamasida M nima?", "options": ["A) Bozor narxi", "B) Muomaladagi pul miqdori", "C) Multiplikator", "D) Import hajmi"], "correct": 1},
    {"question": "Inflyatsiyani maqsadlash (inflation targeting) rejimi nima?", "options": ["A) Hukumat narxlarni to'g'ridan-to'g'ri belgilaydi", "B) Markaziy bank aniq inflyatsiya maqsadini e'lon qilib, kutishlarni barqarorlashtiradi va pul siyosatini shaffof qiladi", "C) Hukumat inflyatsiyani kamaytirish uchun importni taqiqlaydi", "D) Markaziy bank valyuta kursini maqsad qilib belgilaydi"], "correct": 1},
    {"question": "IS egri chizig'i nima va u nima uchun pastga qiyshaygan?", "options": ["A) Pul bozorini ifodalaydi; foiz stavkasi oshganda pul taklifi kamayadi", "B) Tovar bozorini ifodalaydi; foiz stavkasi oshganda investitsiyalar kamayib, YaIM pasayadi", "C) Valyuta bozorini ifodalaydi; foiz oshganda kurs o'zgaradi", "D) Mehnat bozorini ifodalaydi; ish haqi oshganda ishsizlik kamayadi"], "correct": 1},
    {"question": "LM egri chizig'i yuqoriga qiyshaygan, chunki:", "options": ["A) Pul taklifi kamaysa, foiz oshadi", "B) YaIM oshganda pul talabi ortadi, barqaror pul taklifi sharoitida foiz stavkasi ko'tariladi", "C) Hukumat xarajatlari oshganda foiz ortadi", "D) Inflyatsiya oshganda pul taklifi kamayadi"], "correct": 1},
    {"question": "IS-LM modelida likvidlik tuzoq (liquidity trap) sharoitida pul siyosatining samarasi nima uchun nolga teng?", "options": ["A) Pul taklifi oshganda foiz stavkasi noldan past tushib ketadi", "B) Foiz stavkasi allaqachon nolga yaqin bo'lganda LM gorizontal — qo'shimcha pul odamlar tomonidan naqd saqlanadi, investitsiyalar va YaIM o'zgarmaydi", "C) Pul bozori to'liq raqobatli bo'lganda pul taklifi o'zgarmaydi", "D) Markaziy bank tuzoqda o'zi ham kredit bera olmaydi"], "correct": 1},
    {"question": "Solow modelida uzoq muddatli iqtisodiy o'sishning asosiy harakatlantiruvchi kuchi nima?", "options": ["A) Kapital to'planishi", "B) Texnologik taraqqiyot (total factor productivity)", "C) Aholi o'sishi", "D) Davlat investitsiyalari"], "correct": 1},
    {"question": "Harrod-Domar modeli iqtisodiy o'sishni nimaga bog'laydi?", "options": ["A) Faqat texnologiyaga", "B) Jamg'arma normasiga va kapital-mahsulot nisbatiga (ICOR)", "C) Aholining ta'lim darajasiga", "D) Eksport hajmiga"], "correct": 1},
    {"question": "Endogen o'sish nazariyasi (Romer) neoklassik Solow modelidan nima bilan farq qiladi?", "options": ["A) Endogen nazariya faqat ochiq iqtisodiyotlar uchun amal qiladi", "B) Endogen nazariya bilim, inson kapitali va innovatsiyalarga investitsiyalar ortib boruvchi daromadlilik berishi mumkinligini ko'rsatadi — texnologiya ichki omil", "C) Endogen nazariya savdo va globallashuvni inobatga oladi, Solow olmaydi", "D) Endogen nazariya kapital to'planishi barqaror holat (steady state) ga olib kelishini rad etadi"], "correct": 1},
    {"question": "Mutlaq ustunlik (absolute advantage) nazariyasiga ko'ra savdo qachon foydali?", "options": ["A) Bir mamlakat hamma tovarlarni arzonroq ishlab chiqarganda ham savdo foydali", "B) Har bir mamlakat boshqasiga qaraganda mutlaq arzonroq ishlab chiqara oladigan tovarlarni eksport qilganda", "C) Faqat rivojlanayotgan mamlakatlar uchun savdo foydali", "D) Tovar narxi xalqaro bozorda ichki narxdan past bo'lganda"], "correct": 1},
    {"question": "Heckscher-Ohlin nazariyasiga ko'ra mamlakat qanday tovarlarni eksport qiladi?", "options": ["A) Eng yuqori narxdagi tovarlarni", "B) Ko'proq mavjud (ko'p va arzon) omildan foydalanuvchi tovarlarni", "C) Faqat texnologiya talab qilmaydigan tovarlarni", "D) Xorijiy talab katta bo'lgan tovarlarni"], "correct": 1},
    {"question": "'Yangi savdo nazariyasi' (Krugman) klassik qiyosiy ustunlikdan nima bilan farq qiladi?", "options": ["A) Yangi nazariya faqat rivojlangan mamlakatlar o'rtasidagi savdoni tushuntiradi", "B) Yangi nazariya miqyos iqtisodiyoti va iste'molchilarning xilma-xil tovarlarni xohlashi sababli o'xshash mamlakatlar o'rtasida ham savdo bo'lishini tushuntiradi", "C) Yangi nazariya faqat xom ashyo savdosini ko'rib chiqadi", "D) Yangi nazariya proteksionizm har doim foydali ekanligini isbotlaydi"], "correct": 1},
    {"question": "Import kvotasi va import boji o'rtasidagi asosiy farq nima?", "options": ["A) Boj — importni butunlay taqiqlaydi, kvota — cheklamaydi", "B) Boj — narxga ta'sir qilib davlatga daromad keltiradi; kvota — miqdorni cheklab, kvota rentasini import qiluvchilarga beradi", "C) Kvota faqat rivojlanayotgan mamlakatlar uchun, boj rivojlangan mamlakatlar uchun", "D) Ular bir xil ta'sir ko'rsatadi, farq yo'q"], "correct": 1},
    {"question": "'Yosh tarmoq' (infant industry) argumenti nimani asoslaydi?", "options": ["A) Barcha tarmoqlarni abadiy himoya qilish zarurligi", "B) Yangi rivojlanayotgan tarmoqlarni vaqtincha himoya qilish — raqobatbardosh bo'lguncha — keyin himoyani olib tashlash", "C) Faqat qishloq xo'jaligi himoya talab qiladi", "D) Xorijiy raqobat har doim zararli, shuning uchun himoya kerak"], "correct": 1},
    {"question": "Strategik savdo siyosati nazariyasi hukumatning muayyan tarmoqlarni subsidiyalashini qanday asoslaydi?", "options": ["A) Subsidiyalar davlat byudjeti uchun daromad manbayi hisoblanadi", "B) Oligopolistik global bozorlarda strategik subsidiyalar mahalliy firmaga raqobatchilar hisobidan bozor ulushi va foyda olish imkonini beradi (Brander-Spencer modeli)", "C) Subsidiyalar inflyatsiyani pasaytiradi", "D) Barcha tarmoqlar uchun subsidiya berilganda iqtisodiyot tezroq o'sadi"], "correct": 1},
    {"question": "To'lov balansining joriy hisob (current account) tarkibiga nima kiradi?", "options": ["A) Qimmatli qog'ozlar va obligatsiyalar savdosi", "B) Tovarlar va xizmatlar savdosi, daromadlar va joriy transferlar", "C) To'g'ridan-to'g'ri va portfel investitsiyalar", "D) Markaziy bank zaxiralari"], "correct": 1},
    {"question": "Sotib olish quvvati pariteti (PPP) nazariyasiga ko'ra valyuta kursi nima bilan aniqlanadi?", "options": ["A) Markaziy bank qarorlariga", "B) Ikki mamlakattagi tovar narxlari nisbatiga — narxlar teng bo'lguncha kurs moslashadi", "C) Ikki mamlakattagi foiz stavkalari farqiga", "D) Davlatning valyuta zahiralari hajmiga"], "correct": 1},
    {"question": "J-egri chizig'i effekti devalvatsiya va savdo balansiga qanday ta'sirini ifodalaydi?", "options": ["A) Devalvatsiya savdo balansini darhol va doimiy ravishda yaxshilaydi", "B) Devalvatsiya dastlab savdo balansini yomonlashtiradi, keyin eksport oshib import kamayib muvozanat yaxshilanadi — J harfiga o'xshash dinamika", "C) Devalvatsiya inflyatsiyani kamaytiradi va importni oshiradi", "D) Devalvatsiya kapital oqimini oshirib, savdo balansini o'zgartirmaydi"], "correct": 1},
    {"question": "Mundell-Fleming modelida qat'iy valyuta kursi va erkin kapital harakatchanligi sharoitida pul siyosati nima uchun samarasiz?", "options": ["A) Markaziy bank pul chiqarish huquqiga ega emas", "B) Pul taklifi oshirilganda foiz stavkasi tushib, kapital chiqib ketadi va markaziy bank kursni ushlab turish uchun valyuta sotib pul massasini kamaytiradi — siyosat o'z-o'zini bekor qiladi", "C) Pul siyosati faqat yopiq iqtisodiyotda ishlaydi", "D) Qat'iy kursda inflyatsiya foiz stavkasiga ta'sir qilmaydi"], "correct": 1},
    {"question": "Erkin valyuta kursi va erkin kapital harakatchanligi sharoitida fiskal siyosat nima uchun samarasiz?", "options": ["A) Hukumat xorijdan qarz ola olmaydi", "B) Davlat xarajatlari oshganda foiz stavkasi ko'tarilib, kapital kiradi, valyuta qimmatlashadi va eksport kamayadi — bu fiskal impulsni to'liq siqib chiqaradi", "C) Fiskal siyosat faqat rivojlangan mamlakatlarda ishlaydi", "D) Erkin kurs sharoitida soliq tushumi oshadi va taqchillik yo'qoladi"], "correct": 1},
    {"question": "Valyuta kengashi (currency board) rejimining afzalligi va kamchiligi nima?", "options": ["A) Afzalligi — inflyatsiyani to'liq bartaraf etadi; kamchiligi — kapital harakati to'xtab qoladi", "B) Afzalligi — mustaqil valyuta kursiga asoslangan shaffof tizim ishonchlilikni oshiradi; kamchiligi — mustaqil pul siyosatidan voz kechiladi va tashqi zarbalarga moslashish qobiliyati yo'qoladi", "C) Afzalligi — eksportni rag'batlantiradi; kamchiligi — import qimmatlashadi", "D) Afzalligi — barcha tashqi qarzlarni bekor qiladi; kamchiligi — moliya bozori rivojlanmaydi"], "correct": 1},
    {"question": "'Disinflyatsiya' va 'deflatsiya' o'rtasidagi farq nima?", "options": ["A) Disinflyatsiya — narxlarning oshib borishi; deflatsiya — o'sish to'xtashi", "B) Disinflyatsiya — inflyatsiyaning sekinlashishi (narxlar o'sadi, lekin kamroq tez); deflatsiya — narxlar mutlaq tushishi", "C) Ikkalasi bir xil ma'noni anglatadi", "D) Disinflyatsiya faqat rivojlangan mamlakatlarda, deflatsiya rivojlanayotganlarda bo'ladi"], "correct": 1},
    {"question": "Tarkibiy ishsizlik (structural unemployment) nima?", "options": ["A) Mavsumiy sabablar tufayli yuzaga keladigan ishsizlik", "B) Iqtisodiyot tarkibi o'zgarishi (texnologiya, sanoat siljishi) sababli mavjud ko'nikmalar talab etilmaydigan ish o'rinlariga mos kelmasligi", "C) Retsessiya davrida ish o'rinlarining vaqtincha yo'qolishi", "D) Ish izlovchilar va ish beruvchilar o'rtasidagi axborot nomutanosibligi"], "correct": 1},
    {"question": "IS-LM modelida ekspansionar fiskal siyosat foiz stavkasiga ta'siri va 'crowding out' jarayoni qanday ketma-ketlikda sodir bo'ladi?", "options": ["A) Davlat xarajatlari oshadi → YaIM o'sadi → pul talabi ortadi → foiz stavkasi ko'tariladi → xususiy investitsiyalar kamayadi (siqib chiqariladi)", "B) Davlat xarajatlari oshadi → inflyatsiya oshadi → markaziy bank foizni ko'taradi → investitsiyalar kamayadi", "C) Davlat xarajatlari oshadi → eksport oshadi → valyuta qimmatlashadi → import ortadi", "D) Davlat xarajatlari oshadi → soliqlar kamayadi → iste'mol oshadi → inflyatsiya ko'tariladi"], "correct": 0},

    # ── GLOBAL IQTISODIY RIVOJLANISH ─────────────────────
    {"question": "Global iqtisodiyot fanining asosiy tadqiqot ob'ekti nima?", "options": ["A) Faqat rivojlangan mamlakatlar iqtisodiyoti", "B) Milliy iqtisodiyotlar o'rtasidagi o'zaro bog'liqlik, xalqaro savdo, moliya va rivojlanish masalalari", "C) Faqat xalqaro tashkilotlar faoliyati", "D) Faqat valyuta kurslari va pul oqimlari"], "correct": 1},
    {"question": "'Washington konsensusi' qaysi siyosat to'plamini ifodalaydi?", "options": ["A) NATO mamlakatlari o'rtasidagi mudofaa shartnomasi", "B) 1980-90-larda IMF va Jahon banki tomonidan tavsiya etilgan erkinlashtirish, xususiylash va makroiqtisodiy barqarorlashtirish siyosati to'plami", "C) G7 mamlakatlari qabul qilgan iqtisodiy o'sish strategiyasi", "D) Rivojlanish maqsadlari (SDGs) ga erishish dasturi"], "correct": 1},
    {"question": "'Post-Washington konsensusi' Washington konsensusidan qanday farq qiladi?", "options": ["A) U faqat Afrika mamlakatlariga mo'ljallangan yangi qoida to'plami", "B) U bozor islohatlari bilan bir qatorda institutlar, boshqaruv sifati, ijtimoiy kapital va taqsimot adolatiga ham e'tibor berilishi zarurligini ta'kidlaydi", "C) U erkin savdo o'rniga proteksionizm afzalligini asoslaydi", "D) U faqat o'tish iqtisodiyotlari uchun mo'ljallangan"], "correct": 1},
    {"question": "Global ishlab chiqarish zanjirlarining (GVC) asosiy xususiyati nima?", "options": ["A) Barcha ishlab chiqarish jarayoni bir mamlakat ichida amalga oshiriladi", "B) Tovar yoki xizmat ishlab chiqarish turli mamlakatlarda bajariluvchi qiymat qo'shish bosqichlariga bo'linadi", "C) Faqat rivojlangan mamlakatlar bunday zanjirlarni boshqaradi", "D) GVC faqat avtomobil sanoatiga xos"], "correct": 1},
    {"question": "'G-20' guruhining roli nima?", "options": ["A) Faqat rivojlanayotgan mamlakatlar manfaatini himoya qilish", "B) Dunyo YaIMining 85% ini tashkil etuvchi 20 ta yirik iqtisodiyot rahbarlari global iqtisodiy muammolarni muvofiqlashtiradigan forum", "C) Harbiy ittifoq sifatida tashkil etilgan", "D) Savdo kelishuvlarini imzolash uchun maxsus organ"], "correct": 1},
    {"question": "'Sharq ko'tarilishi' (Rise of the East) deb qaysi tendentsiya ataladi?", "options": ["A) Yaponiyaning 1980-lardagi iqtisodiy yuksalishi", "B) Xitoy, Hindiston va boshqa Osiyo iqtisodiyotlarining global YaIM va savdodagi ulushining ortib borishi", "C) Quyosh energiyasining sharqiy mamlakatlarda rivojlanishi", "D) ASEAN mamlakatlarining NATO ga kirish jarayoni"], "correct": 1},
    {"question": "'Deglobalization' yoki 'slowbalization' tendentsiyasini qaysi omillar rag'batlantirdi?", "options": ["A) Texnologik taraqqiyot va internet savdosi", "B) 2008 moliyaviy inqirozi, COVID-19 pandemiyasi, savdo urushlari va milliychilik tendentsiyalari GVC ni qisqartirib, neoproteksionizmni kuchaytirdi", "C) Neft narxlarining tushishi va transport xarajatlarining kamayishi", "D) Rivojlanayotgan mamlakatlarning o'sishi savdo ehtiyojini kamaytirdi"], "correct": 1},
    {"question": "WTO ning asosiy printsipi — Eng Ma'qul Mamlakat (MFN) rejimi nima?", "options": ["A) Eng kambag'al mamlakatga maxsus imtiyozlar berish", "B) Bir WTO a'zosiga berilgan savdo imtiyozi boshqa barcha a'zolarga ham avtomatik berilishi kerak — kamsitmaslik printsipi", "C) Har bir mamlakatga alohida savdo shartnomalari belgilanadi", "D) Faqat rivojlangan mamlakatlar o'rtasida teng shartlar"], "correct": 1},
    {"question": "Xizmatlar savdosi (GATS) tovarlar savdosidan (GATT) qanday farq qiladi?", "options": ["A) Xizmatlar savdosi faqat rivojlangan mamlakatlar uchun amal qiladi", "B) Xizmatlar ko'pincha chegarada tutib bo'lmaydi — ular 4 ta usulda sotilishi mumkin (chegara orqali, xorijda iste'mol, tijorat vakilligi, shaxslarning harakati)", "C) Xizmatlar savdosi soliqlanmaydi", "D) Xizmatlar GATTning bir qismi hisoblanadi"], "correct": 1},
    {"question": "'Dumping' deganda nima tushuniladi?", "options": ["A) Tovarlarni eksport qilishdan voz kechish", "B) Mahsulotni xorijiy bozorda o'z ichki narxidan yoki ishlab chiqarish xarajatidan past narxda sotish", "C) Import narxini sun'iy ravishda oshirish", "D) Import kvotasini belgilash"], "correct": 1},
    {"question": "Savdo shartlari (terms of trade) yomonlashishi rivojlanayotgan mamlakatlar uchun nima sababdan muammo (Prebisch-Singer gipotezasi)?", "options": ["A) Rivojlanayotgan mamlakatlar xom ashyo eksport qiladi; uning narxi uzoq muddatda sanoat tovarlariga nisbatan pasayish tendentsiyasiga ega", "B) Savdo shartlari faqat valyuta kursiga bog'liq", "C) Rivojlanayotgan mamlakatlar ko'p import qilgani uchun defitsit doimo oshib boradi", "D) Sanoat tovarlarining sifati pasayishi savdo shartlarini yomonlashtiradi"], "correct": 0},
    {"question": "Kapital va moliyaviy hisob (capital and financial account) tarkibiga nima kiradi?", "options": ["A) Tovarlar va xizmatlar eksporti", "B) To'g'ridan-to'g'ri investitsiyalar, portfel investitsiyalar va boshqa kapital oqimlari", "C) Daromadlar va transferlar", "D) Oltin va valyuta zahiralari faqat"], "correct": 1},
    {"question": "To'lov balansi har doim balanslanishi kerakligi nima sababdan?", "options": ["A) Xalqaro qonunchilik shuni talab qiladi", "B) Joriy hisob taqchilligini kapital va moliyaviy hisob profitsiti qoplaydi — ikkalasining yig'indisi nolga teng bo'lishi kerak (buxgalteriya qoidasi)", "C) Markaziy banklar balansi ta'minlaydi", "D) WTO qoidalari to'lov balansini muvozanatlaydi"], "correct": 1},
    {"question": "'Global imbalances' (global nomutanosibliklar) deganda nima tushuniladi va u nima sababdan muammo?", "options": ["A) Ba'zi mamlakatlarning katta joriy hisob profitsitiga ega bo'lishi va boshqalarning katta taqchillikka ega bo'lishi — bu beqaror kapital oqimlariga, valyuta bosimiga va potentsial moliyaviy inqirozga olib kelishi mumkin", "B) G'arb va Sharq mamlakatlari o'rtasidagi texnologiya farqi", "C) Rivojlanayotgan mamlakatlarning qarzlarini to'lay olmasligi", "D) Global inflyatsiya sur'atlarining farqliligi"], "correct": 0},
    {"question": "Globallashuv davrida qaysi guruh nisbatan ko'proq foydaga ega bo'ldi?", "options": ["A) Rivojlanayotgan mamlakatlarning malakasiz ishchilari va rivojlangan mamlakatlarning malakali professional sinfi", "B) Faqat transmilliy korporatsiyalar", "C) Faqat moliyachi va investorlar", "D) Barcha guruhlar teng foyda ko'rdi"], "correct": 0},
    {"question": "'Elephant curve' (Branco Milanovic) nimani ko'rsatadi?", "options": ["A) Neft narxlarining uzoq muddatli tendentsiyasini", "B) 1988-2008 yillar orasida global daromad o'sishining taqsimotini — rivojlanayotgan mamlakatlar o'rta sinfi va eng boy 1% eng ko'p foyda ko'rdi, rivojlangan mamlakatlar quyi o'rta sinfi esa eng kam foyda ko'rdi", "C) Global aholi o'sishi va iqtisodiy o'sish o'rtasidagi bog'liqlikni", "D) Xitoy iqtisodiyotining o'sish egri chizig'ini"], "correct": 1},
    {"question": "Globallashuvning rivojlanayotgan mamlakatlarda 'deindustrializatsiya' ga olib kelish xavfi nima sababdan mavjud?", "options": ["A) Rivojlanayotgan mamlakatlar sanoat uchun zarur resursga ega emas", "B) Uchinchi mamlakatlardagi arzon raqobat va GVCning o'rta darajali ishlarni avtomatlashishi ba'zi rivojlanayotgan mamlakatlar tarixiy industrializatsiya yo'lidan o'tishiga imkon bermasligi mumkin", "C) WTO sanoat rivojlanishini taqiqlaydi", "D) Rivojlangan mamlakatlar texnologiya transferiga yo'l qo'ymaydi"], "correct": 1},
    {"question": "Dani Rodrik 'globalization trilemma' sida qaysi uchta maqsadni bir vaqtda amalga oshirish mumkin emasligini ta'kidlaydi?", "options": ["A) Erkin savdo, barqaror valyuta kursi va mustaqil pul siyosati", "B) Chuqur iqtisodiy integratsiya (globallashuv), milliy siyosat mustaqilligi va demokratik siyosat — uchidan faqat ikkitasini tanlash mumkin", "C) Yuqori o'sish, past inflyatsiya va to'liq bandlik", "D) Erkin kapital harakati, savdo profitsiti va mustaqil fiskal siyosat"], "correct": 1},
    {"question": "BM Barqaror rivojlanish maqsadlari (SDGs) nechta va qachon qabul qilingan?", "options": ["A) 15 ta maqsad, 2000-yilda", "B) 17 ta maqsad, 2015-yilda 2030-yilgacha bo'lgan davrni qamrab oladi", "C) 10 ta maqsad, 2010-yilda", "D) 20 ta maqsad, 2020-yilda"], "correct": 1},
    {"question": "Karbon solig'i (carbon tax) qanday mexanizm bilan ishlaydi?", "options": ["A) Kompaniyalarning foydasiga qo'shimcha soliq", "B) CO₂ emissiyasiga narx belgilash orqali firmalarga ifloslantishi uchun to'lov yuklab, yashil texnologiyalarga o'tishni iqtisodiy jihatdan foydaliroq qilish", "C) Yashil energiya importini subsidiyalash", "D) Ifloslantiradigan tarmoqlarga importni taqiqlash"], "correct": 1},
    {"question": "'Just transition' (adolatli o'tish) tushunchasi nimani anglatadi?", "options": ["A) Barcha mamlakatlar teng miqdorda emissiyani kamaytirishi kerakligi", "B) Yashil iqtisodiyotga o'tishda ko'mir va boshqa qazilma yoqilg'i tarmoqlarida ishlayotgan ishchilar va hamjamiyatlarning zararini minimallashtirish va yangi imkoniyatlar yaratish", "C) Rivojlangan mamlakatlarning rivojlanayotganlarga iqlim mablag'ini o'tkazishi", "D) Iste'molchilardan yashil mahsulotlar uchun qo'shimcha to'lov olish"], "correct": 1},
    {"question": "'Carbon border adjustment mechanism' (CBAM) nima maqsadda kiritilgan?", "options": ["A) Iqlim bo'yicha xalqaro shartnomalar tuzishni rag'batlantirish", "B) Qat'iy iqlim siyosati bo'lgan mamlakatdan ko'proq emissiyaga ruxsat beruvchi mamlakatga ishlab chiqarishning ko'chib ketishini (carbon leakage) oldini olish", "C) Yashil energiya eksportini subsidiyalash", "D) Rivojlanayotgan mamlakatlarning emissiya hisobotini tekshirish"], "correct": 1},
    {"question": "Raqamli platformalar iqtisodiyotida 'network effect' nima?", "options": ["A) Internet tezligiga bog'liq texnik cheklov", "B) Platforma foydalanuvchilari ko'paygan sari har bir foydalanuvchi uchun platforma qiymati oshib boradi — bu katta platformalarga monopol afzallik beradi", "C) Raqamli tovarlarning nol marginal xarajatga ega bo'lishi", "D) Ma'lumotlar hajmining oshishi serverlar quvvatini oshirishni talab qilishi"], "correct": 1},
    {"question": "'Data as a new oil' iborasi nima sababdan ishlatilinadi?", "options": ["A) Ma'lumotlar sotilib daromad keltiradi, neft kabi", "B) Ma'lumotlar 21-asrda qimmatli xom ashyoga aylandi — AI va raqamli iqtisodiyotning asosiy resursini tashkil qiladi va uni egallaganlar katta raqobat ustunligiga ega bo'ladi", "C) Ma'lumotlar neft kabi tabiatdan olinadi", "D) Raqamli sanoat neft sanoatini almashtirmoqda"], "correct": 1},
    {"question": "'Digital divide' (raqamli tengsizlik) nimani anglatadi?", "options": ["A) Katta va kichik raqamli kompaniyalar o'rtasidagi farq", "B) Raqamli texnologiyalarga kirish imkoniyatidagi tengsizlik — rivojlangan va rivojlanayotgan mamlakatlar, shahar va qishloq, boy va kambag'allar o'rtasida", "C) Dasturchilar va oddiy foydalanuvchilar o'rtasidagi bilim farqi", "D) Turli raqamli platformalar o'rtasidagi raqobat"], "correct": 1},
    {"question": "Raqamli iqtisodiyotda an'anaviy YaIM hisoblash nima uchun etarli emas?", "options": ["A) Raqamli tovarlar juda tez ishlab chiqariladi va hisoblash imkoni yo'q", "B) Ko'pgina raqamli xizmatlar (Google, Facebook) iste'molchilarga bepul taqdim etiladi — YaIM pul bilan to'langan operatsiyalarni o'lchaydi, bepul xizmatlar esa o'lchovga kirmaydi", "C) Raqamli tovarlar davlat tomonidan boshqarilgani uchun YaIMga kiritilmaydi", "D) Raqamli iqtisodiyot YaIMni sun'iy oshiradi"], "correct": 1},
    {"question": "Erkin savdo hududi va Bojxona ittifoqi o'rtasidagi farq nima?", "options": ["A) Erkin savdo hududida kapital harakati erkin, Bojxona ittifoqida yo'q", "B) Erkin savdo hududida a'zolar o'rtasida bojlar olib tashlanadi, lekin har biri uchinchi mamlakatlar uchun o'z bojlarini belgilaydi; Bojxona ittifoqida esa uchinchi mamlakatlar uchun umumiy tashqi boj belgilanadi", "C) Bojxona ittifoqida tovarlar harakati cheklangan, erkin savdoda emas", "D) Ular bir xil, faqat nomlanishi farqli"], "correct": 1},
    {"question": "Integratsiyaning eng yuqori shakli qaysi?", "options": ["A) Erkin savdo hududi", "B) To'liq iqtisodiy ittifoq — yagona bozor, yagona valyuta va umumiy iqtisodiy siyosat", "C) Bojxona ittifoqi", "D) Umumiy bozor"], "correct": 1},
    {"question": "Savdo yaratish (trade creation) va savdo burilishi (trade diversion) effekti nima?", "options": ["A) Integratsiya yangi tovarlarni ixtiro qiladi — savdo yaratiladi; eski tovarlar o'rnini yangilari oladi", "B) Savdo yaratish: integratsiya arzonroq manbani a'zolardan olishga imkon beradi (samarali); Savdo burilishi: integratsiya uchinchi mamlakatlardan arzon tovar o'rniga a'zolardan qimmatroq tovar sotib olishga majburlaydi (samarasiz)", "C) Savdo yaratish — eksportni oshirish; savdo burilishi — importni kamaytirish", "D) Ikkalasi ham integratsiyaning ijobiy natijalari"], "correct": 1},
    {"question": "'Optimal valyuta hududi' (OCA — Mundell) nazariyasiga ko'ra mamlakatlarga umumiy valyutani qabul qilish uchun qanday shartlar kerak?", "options": ["A) Yalpi daromad darajasi teng bo'lishi kerak", "B) Omillar harakatchanligi (ayniqsa mehnat), narx/ish haqi moslashuvchanligi, savdoning integratsiyalashuvi va simetrik tashqi zarbalar", "C) Barcha a'zo mamlakatlar demokratik bo'lishi kerak", "D) Umumiy mudofaa shartnomasi mavjud bo'lishi kerak"], "correct": 1},
    {"question": "FDI ning portfel investitsiyalardan asosiy farqi nima?", "options": ["A) FDI faqat rivojlangan mamlakatlardan keladi", "B) FDI boshqaruvni ham o'z ichiga oladi (10% dan ko'proq aktsiya) — investor faoliyatni bevosita nazorat qiladi; portfelda faqat moliyaviy daromad maqsad", "C) FDI faqat ishlab chiqarish sektoriga yo'naltiriladi", "D) Portfel investitsiyalar davlatlar o'rtasida, FDI esa kompaniyalar o'rtasida amalga oshiriladi"], "correct": 1},
    {"question": "FDI qabul qiluvchi mamlakatlar uchun asosiy afzalliklar qaysilar?", "options": ["A) Faqat ish o'rinlari yaratiladi", "B) Kapital, texnologiya, boshqaruv ko'nikmalari, bozor kirish imkoniyatlari va eksport potentsialining oshishi", "C) Faqat davlat soliq daromadlari ko'payadi", "D) Milliy valyuta mustahkamlanadi"], "correct": 1},
    {"question": "Transmilliy korporatsiyalar (TMK) nima uchun ko'pincha rivojlanayotgan mamlakatlarda ishlab chiqarishni joylashtiradi?", "options": ["A) Faqat tabiiy resurslardan foydalanish uchun", "B) Arzon mehnat, past soliqlar, ko'proq yumshoq ekologik talablar, bozorga yaqinlik va imtiyozli shart-sharoitlar", "C) Faqat davlat moliyaviy yordami uchun", "D) Rivojlanayotgan mamlakatlar yaxshiroq texnologiyaga ega"], "correct": 1},
    {"question": "'Transfer pricing' (transfer narxlash) TMK lar tomonidan qanday maqsadda qo'llaniladi?", "options": ["A) TMK filiallar o'rtasidagi operatsiyalarda bozor narxidan farqli ichki narx belgilab, foydani past soliqli mamlakatlarga siljitadi — bu mamlakatlarning soliq daromadlarini kamaytirib, 'profit shifting' muammosini keltirib chiqaradi", "B) Transfer narxlash — xalqaro buxgalteriya standarti bo'lib, foyda taqsimotini tartibga soladi", "C) TMK tovarlarni bozor narxidan past narxda sotib, raqobatchilarni siqib chiqaradi", "D) Transfer narxlash faqat rivojlangan mamlakatlar o'rtasida qo'llaniladi"], "correct": 0},
    {"question": "Oltin standart tizimi qanday ishlaydi?", "options": ["A) Markaziy bank oltin narxini belgilaydi", "B) Valyutalar oltin bilan belgilangan qat'iy paritetda bo'ladi — markaziy bank valyutasini oltinga kafolatlangan narxda almashtiradi", "C) Davlatlar oltin zaxiralarini oshirib bozorni boshqaradi", "D) Oltin narxi erkin suzuvchi bo'ladi"], "correct": 1},
    {"question": "Maxsus chiqim huquqlari (SDR) nima?", "options": ["A) Faqat rivojlangan mamlakatlar uchun moliyalashtirish vositasi", "B) IMF tomonidan chiqarilgan xalqaro zaxira vositasi — a'zo mamlakatlarga proportional taqsimlanadi va valyutalar savatasiga asoslangan", "C) G7 mamlakatlari tomonidan yaratilgan umumiy valyuta", "D) Xalqaro kredit kartasi tizimi"], "correct": 1},
    {"question": "Valyuta kursi rejimlarining asosiy turlari qaysilar?", "options": ["A) Erkin va taqiqlangan", "B) Qat'iy belgilangan (fixed/pegged), boshqariladigan suzuvchi (managed float) va erkin suzuvchi (free float)", "C) Oltin standart va dollar standart", "D) Bir tomonlama va ikki tomonlama"], "correct": 1},
    {"question": "Dollarning global zaxira valyutasi sifatidagi mavqei AQSHga qanday 'imtiyoz' (exorbitant privilege) beradi?", "options": ["A) AQSH boshqa mamlakatlarni dollardan foydalanish uchun to'lov ola oladi", "B) AQSH o'z valyutasida arzon qarz ola oladi, tashqi taqchilligini osonlikcha moliyalashtira oladi va senioraj daromadi oladi — boshqalar dollar zaxirasini saqlash uchun AQSHga resurs beradi", "C) AQSH WTO qoidalarini boshqalarga nisbatan qat'iyroq qo'llash huquqiga ega", "D) AQSH dollarini istalgan vaqtda devalvatsiya qila oladi va bu savdo balansini yaxshilaydi"], "correct": 1},
    {"question": "'Triffin dilemmasi' xalqaro valyuta tizimidagi qanday ziddiyatni ifodalaydi?", "options": ["A) Kichik mamlakatlar qat'iy kurs va erkin kapital harakati o'rtasida tanlashga majbur", "B) Zaxira valyutasi emitenti (AQSH) joriy hisob taqchilligi orqali dunyo likvid valyuta bilan ta'minlaydi, lekin bu taqchillik chuqurlashgani sari valyutaga bo'lgan ishonch pasayadi", "C) IMF va Jahon banki bir-birining siyosatini bekor qiladi", "D) Rivojlanayotgan mamlakatlar ko'p qarz olgani uchun zaxira valyutasini ushlab tura olmaydi"], "correct": 1},
    {"question": "'Cap and trade' (limitlash va savdo) tizimi qanday ishlaydi?", "options": ["A) Kompaniyalar iqlim shartnomasini imzolasa, soliq to'lamaydi", "B) Emissiya uchun umumiy chegara belgilanadi, kompaniyalar kvota doirasida emissiya huquqini bozorda sotib oladi yoki sotadi — bu iqtisodiy samarali yo'l bilan emissiyani kamaytiradi", "C) Hukumat emissiyani taqiqlaydi va jarimalar oladi", "D) Kompaniyalar yashil texnologiya uchun subsidiya oladi"], "correct": 1},
    {"question": "'Friend-shoring' (do'stona manbalashtirish) nima?", "options": ["A) Eng arzon mamlakatlardan tovar sotib olish strategiyasi", "B) Geosiyosiy ishonchli ittifoqchilar va do'st mamlakatlardan ta'minot zanjirlari qurishga o'tish tendentsiyasi", "C) TMKlarning o'z mamlakatiga ishlab chiqarishni qaytarishi", "D) Madaniy yaqinlikka asoslanib ish sheriklari tanlash"], "correct": 1},
    {"question": "'Brain drain' (miya oqishi) rivojlanayotgan mamlakatlar uchun nima sababdan muammo?", "options": ["A) Aholining kamayishi", "B) Yaxshi malakali mutaxassislar rivojlangan mamlakatlarga ko'chib, yuqori ta'lim xarajatlari o'tkazilgan inson kapitalini mamlakat yo'qotadi", "C) Mehnat bozorida raqobat kuchayadi", "D) Xorijda ishlayotganlar pul o'tkazmaydi"], "correct": 1},
    {"question": "Yevropa Ittifoqi (EU) Monetar Ittifoqining asosiy muammosi 2010-yillardagi Yevrozonadagi qarz inqirozida nima edi?", "options": ["A) Yevro valyutasi juda kuchsiz bo'lgani uchun inflyatsiya oshdi", "B) A'zo mamlakatlar yagona valyutada bo'lib, valyutani devalvatsiya qila olmadilar va mustaqil pul siyosati yurgazolmadilar — tashqi zarbalarga moslashish qiyin bo'ldi", "C) WTO EU integratsiyasini taqiqladi", "D) Yevrozona a'zoligi uchun soliq siyosati yagona edi"], "correct": 1},
    {"question": "'Sanoat siyosati' (industrial policy) nima va u erkin savdo tarafdorlari tomonidan qanday tanqid qilinadi?", "options": ["A) Hukumat muayyan tarmoqlarni soliq, subsidiya yoki himoya orqali rag'batlantiradi; tanqidchilar 'g'oliblarni tanlash' (picking winners) da hukumat bozordan ko'ra yomonroq ekanligini aytadi", "B) Hukumat barcha tarmoqlarga teng soliq belgilaydi", "C) Sanoat siyosati faqat eksport tarmoqlarini himoyalaydi", "D) Hukumat mehnat qonunchiligini tartibga soladi"], "correct": 0},
    {"question": "'Fintech' va an'anaviy bank xizmatlari o'rtasidagi asosiy farq nima?", "options": ["A) Fintech faqat kriptovalyuta bilan ishlaydi", "B) Fintech texnologiya orqali moliyaviy xizmatlarni tezroq, arzonroq va kengroq auditoriyaga yetkazadi — qo'shimcha filial infratuzilmasiz", "C) Fintech davlat tomonidan to'liq boshqariladi", "D) Fintech faqat korporativ mijozlarga xizmat ko'rsatadi"], "correct": 1},
    {"question": "'Rivojlanishning institutsional nazariyasi' (Acemoglu, Robinson) asosiy argumenti nima?", "options": ["A) Geografik joylashuv iqtisodiy rivojlanishni belgilaydi", "B) Inklyuziv siyosiy va iqtisodiy institutlar uzoq muddatli farovonlikni ta'minlaydi — ekstraktiv institutlar o'sishni to'sadi", "C) Xorijiy investitsiyalar rivojlanishning yagona omili", "D) Ta'lim darajasi barcha boshqa omillardan muhimroq"], "correct": 1},
    {"question": "'Race to the bottom' (tubiga qarab poyga) hodisasi FDI jalb qilishda nima sababdan yuzaga keladi?", "options": ["A) Mamlakatlar eng arzon tovarlarni ishlab chiqarishga harakat qiladi", "B) Mamlakatlar FDI jalb qilish uchun bir-biridan kam soliq, zaiflashtirilgan mehnat va ekologik standartlar taklif qiladi — bu global me'yorlarning pasayishiga olib keladi", "C) TMK larning foydasi kamayib boradi", "D) Mamlakatlar o'rtasida texnologiya raqobati kuchayadi"], "correct": 1},
    {"question": "'Impossible trinity' ni global moliyada qanday tushuntirish mumkin?", "options": ["A) Mamlakat bir vaqtning o'zida: erkin kapital harakati, barqaror valyuta kursi va mustaqil pul siyosatini olib borolmaydi — uchdan faqat ikkitasini tanlashi mumkin", "B) To'lov balansi har doim muvozanatlashadi, shuning uchun siyosat zarur emas", "C) Kapital harakati va pul siyosati o'rtasida ziddiyat yo'q, faqat fiskal siyosat bilan muammo bor", "D) Valyuta kursi erkin bo'lganda to'lov balansi avtomatik tuzaladi"], "correct": 0},
    {"question": "'Regionalism vs. Multilateralism' munozarasida mintaqaviy savdo bitimlari (RTA) global erkin savdo tizimini qanday xavf ostiga qo'yishi mumkin?", "options": ["A) Mintaqaviy bitimlar WTO ni bekor qiladi", "B) Ko'p RTAlar bir-biri ustiga to'planishi ('spaghetti bowl' effekti) savdo qoidalarini murakkablashtiradi, savdo burilishini keltirib chiqaradi va multilateral muzokaralardan e'tiborni chalg'itadi", "C) Mintaqaviy bitimlar faqat rivojlangan mamlakatlar uchun foydali", "D) RTA lar WTO qoidalari bilan zid kelganda avtomatik bekor bo'ladi"], "correct": 1},
    {"question": "Xitoy yuanining (renminbi) xalqaro zaxira valyutasiga aylanishi yo'lidagi asosiy to'siqlar nima?", "options": ["A) Xitoy valyutasini xalqaro tizimga ulash uchun texnik imkoniyat yo'q", "B) Kapital hisobining to'liq ochiq emasligi, moliyaviy bozor chuqurligining yetarli emasligi, qonun ustuvorligiga ishonch va yuan konvertatsiyasini cheklash — zaxira valyutasi uchun zarur bo'lgan likvidlik va ishonch shakllanmagan", "C) WTO Xitoyga zaxira valyutasiga chiqishni taqiqlagan", "D) SDR tizimi yangi valyutalarning kirishiga yo'l qo'ymaydi"], "correct": 1},
]


def _build_fallback() -> list:
    """Return 10 random questions from 100-question bank."""
    questions = FALLBACK_QUESTIONS.copy()
    random.shuffle(questions)
    return questions[:10]


async def _call_gemini(topic: str) -> list | None:
    """Try all 3 keys × all models. Return questions or None."""
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
        print("[QUIZ] No API keys — fallback (100-question bank)")
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
                print("[QUIZ] All Gemini keys failed — fallback (100-question bank)")
                return _build_fallback()

            return questions
        finally:
            await _decrement()
