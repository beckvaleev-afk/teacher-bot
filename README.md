# Teacher Assistant Bot

## Quick Start (Windows PowerShell)

### Step 1 — Run setup (one time only)
```powershell
cd D:\3Teacher_bot
.\setup.ps1
```

### Step 2 — Fill in your tokens
Open `.env` and set:
```
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_telegram_user_id
```

**Get BOT_TOKEN:** Open Telegram → @BotFather → /newbot → copy token

**Get ADMIN_ID:** Open Telegram → @userinfobot → send /start → copy your ID

### Step 3 — Run the bot
```powershell
.\run.ps1
```

---

## What works without extra API keys

| Feature | Without API key | With API key |
|---|---|---|
| /start menu | ✅ Works | ✅ Works |
| Student info collection | ✅ Works | ✅ Works |
| File upload | ✅ Saves locally | ✅ Saves to AWS S3 |
| Face verification | ⚠️ Skipped (dev mode) | ✅ AWS Rekognition |
| Quiz questions | ✅ Generic questions | ✅ Topic-specific (OpenAI) |
| Grading | ✅ Works | ✅ Works |
| Result saving | ✅ SQLite database | ✅ SQLite + Google Sheets |
| Admin commands | ✅ Works | ✅ Works |

You can run and test the bot with ONLY `BOT_TOKEN` and `ADMIN_ID`.

---

## File structure
```
3Teacher_bot/
├── bot.py              ← Entry point
├── config.py           ← Environment variables
├── requirements.txt    ← Python packages
├── .env                ← Your secrets (never share this)
├── setup.ps1           ← One-time setup
├── run.ps1             ← Start bot
├── database/
│   ├── models.py       ← Database tables
│   └── db.py           ← Database connection
├── handlers/
│   ├── start.py        ← /start command
│   ├── student_flow.py ← Full student FSM
│   └── admin.py        ← Admin commands
├── services/
│   ├── s3.py           ← File upload
│   ├── face.py         ← Face verification
│   ├── quiz.py         ← Question generation
│   ├── grading.py      ← Score to grade
│   └── sheets.py       ← Google Sheets
└── webapp/
    └── face_capture.html ← Camera mini-app
```

## Admin Commands
- `/admin` — show admin menu
- `/results` — last 20 submissions
- `/stats` — overall statistics  
- `/export` — download CSV of all results
