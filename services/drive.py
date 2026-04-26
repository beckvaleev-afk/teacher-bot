"""
Google Sheets logging + Telegram file storage.
Files stored on Telegram servers (free, unlimited).
Admin can access files via Telegram links in Sheets.
"""
import os
import io
import json
from datetime import datetime

SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "")
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")


def _get_credentials():
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    creds_content = os.getenv("GOOGLE_CREDENTIALS_CONTENT", "")
    if creds_content and creds_content.strip().startswith("{"):
        try:
            info = json.loads(creds_content)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            print(f"[AUTH] Error: {e}")

    creds_file = os.getenv("GOOGLE_CREDS_JSON", "google_credentials.json")
    if os.path.exists(creds_file):
        return Credentials.from_service_account_file(creds_file, scopes=scopes)

    raise Exception("Google credentials not found!")


def make_telegram_file_link(file_id: str) -> str:
    """
    Create a direct download link for a Telegram file.
    Admin can open this link to download the file.
    """
    if not BOT_TOKEN or not file_id:
        return ""
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}"


async def get_telegram_file_path(bot, file_id: str) -> str:
    """Get the actual file path from Telegram servers."""
    try:
        tg_file = await bot.get_file(file_id)
        return make_telegram_file_link(tg_file.file_path)
    except Exception as e:
        print(f"[TELEGRAM] File path error: {e}")
        return f"tg://file_id/{file_id}"


# Keep upload_to_drive name for compatibility — now saves to Telegram
async def upload_to_drive(file_bytes: bytes, filename: str,
                           student_name: str = "Unknown",
                           file_id: str = "") -> str:
    """
    Returns Telegram download link using file_id.
    file_bytes kept for signature compatibility but not used.
    """
    if file_id and BOT_TOKEN:
        link = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_id}"
        print(f"[TELEGRAM] Fayl linki yaratildi: {filename}")
        return link
    print(f"[TELEGRAM] file_id yo'q — link yaratilmadi")
    return f"tg://unknown/{filename}"


async def log_to_sheets(submission_data: dict, result: dict,
                         file_url: str = "") -> bool:
    try:
        from googleapiclient.discovery import build

        creds   = _get_credentials()
        service = build("sheets", "v4", credentials=creds)

        _ensure_header(service)

        row = [[
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            submission_data.get("full_name", ""),
            submission_data.get("course", ""),
            submission_data.get("group", ""),
            submission_data.get("subject", ""),
            submission_data.get("assignment_type", ""),
            submission_data.get("topic", ""),
            file_url or submission_data.get("file_url", ""),
            submission_data.get("selfie_url", ""),
            f"{result.get('score', 0)}/{result.get('total', 10)}",
            result.get("grade", ""),
            result.get("status", ""),
            "Ha" if result.get("passed") else "Yo'q",
        ]]

        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range="Sheet1!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": row},
        ).execute()

        print(f"[SHEETS] Yozildi: {submission_data.get('full_name')}")
        return True

    except Exception as e:
        print(f"[SHEETS] Xato: {e}")
        return False


def _ensure_header(service):
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="Sheet1!A1"
        ).execute()
        if result.get("values"):
            return
    except Exception:
        pass

    headers = [[
        "Vaqt", "Ism Familiya", "Kurs", "Guruh", "Fan nomi",
        "Topshiriq turi", "Mavzu",
        "Fayl (Telegram link)",
        "Selfi (Telegram link)",
        "Ball", "Baho", "Holat", "O'tdimi"
    ]]
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": headers},
    ).execute()
    print("[SHEETS] Header qo'shildi.")
