"""
Google Drive + Google Sheets integration using OAuth2.
- Files uploaded to TeacherBot_Submissions folder on Drive
- Results logged to Google Sheets automatically
"""
import os
import io
import mimetypes
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

CLIENT_SECRETS  = "client_secrets.json"
TOKEN_FILE      = "token.json"
DRIVE_FOLDER    = "TeacherBot_Submissions"
SPREADSHEET_ID  = "1v5tahs9dE7ZsL39GzDQ0ndwIZLqmzL8lOYZgnLOWGtA"


# ── Credentials ───────────────────────────────────────────
def _get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS):
                raise FileNotFoundError("client_secrets.json topilmadi!")
            flow  = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("[AUTH] Token saqlandi.")
    return creds


# ── Drive helpers ─────────────────────────────────────────
def _get_or_create_folder(service, folder_name: str) -> str:
    query   = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id,name)").execute()
    files   = results.get("files", [])
    if files:
        return files[0]["id"]
    meta   = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=meta, fields="id").execute()
    print(f"[DRIVE] Papka yaratildi: {folder_name}")
    return folder["id"]


def _get_student_folder(service, parent_id: str, student_name: str) -> str:
    """Create a subfolder per student inside TeacherBot_Submissions."""
    safe_name = student_name.replace("/", "_").replace("\\", "_")
    query     = (
        f"name='{safe_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id,name)").execute()
    files   = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name":    safe_name,
        "mimeType":"application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    print(f"[DRIVE] Talaba papkasi yaratildi: {safe_name}")
    return folder["id"]


# ── Main upload function ──────────────────────────────────
async def upload_to_drive(file_bytes: bytes, filename: str,
                           student_name: str = "Unknown") -> str:
    """
    Upload file to Google Drive.
    Structure: TeacherBot_Submissions / StudentName / filename
    Returns shareable link.
    """
    try:
        creds        = _get_credentials()
        drive_svc    = build("drive", "v3", credentials=creds)

        # Get or create main folder
        main_folder  = _get_or_create_folder(drive_svc, DRIVE_FOLDER)
        # Get or create student subfolder
        stud_folder  = _get_student_folder(drive_svc, main_folder, student_name)

        mime_type, _ = mimetypes.guess_type(filename)
        mime_type    = mime_type or "application/octet-stream"

        file_meta = {"name": filename, "parents": [stud_folder]}
        media     = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        uploaded  = drive_svc.files().create(
            body=file_meta, media_body=media, fields="id,name,webViewLink"
        ).execute()

        file_id   = uploaded["id"]
        file_link = uploaded.get("webViewLink", "")

        # Make viewable by anyone with link
        drive_svc.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        print(f"[DRIVE] Yuklandi: {filename} → {file_link}")
        return file_link

    except Exception as e:
        print(f"[DRIVE] Xato: {e}")
        return _local_fallback(file_bytes, filename)


def _local_fallback(file_bytes: bytes, filename: str) -> str:
    import uuid
    folder = "local_uploads"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{uuid.uuid4()}_{filename}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    print(f"[DRIVE] Lokal saqlandi: {path}")
    return f"local://{path}"


# ── Google Sheets logger ──────────────────────────────────
async def log_to_sheets(submission_data: dict, result: dict,
                         file_url: str = "") -> bool:
    """
    Append one row to Google Sheets with all student data.
    Columns: Vaqt | Ism | Kurs | Guruh | Tur | Mavzu | Fayl | Ball | Baho | Holat | O'tdimi
    """
    try:
        creds      = _get_credentials()
        sheets_svc = build("sheets", "v4", credentials=creds)

        # Ensure header row exists
        _ensure_header(sheets_svc)

        row = [[
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            submission_data.get("full_name", ""),
            submission_data.get("course", ""),
            submission_data.get("group", ""),
            submission_data.get("subject", ""),
            submission_data.get("assignment_type", ""),
            submission_data.get("topic", ""),
            file_url or submission_data.get("file_url", ""),
            f"{result.get('score', 0)}/{result.get('total', 10)}",
            result.get("grade", ""),
            result.get("status", ""),
            "Ha" if result.get("passed") else "Yo'q",
        ]]

        sheets_svc.spreadsheets().values().append(
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


def _ensure_header(sheets_svc):
    """Add header row if sheet is empty."""
    try:
        result = sheets_svc.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="Sheet1!A1"
        ).execute()
        if result.get("values"):
            return  # Header already exists
    except Exception:
        pass

    headers = [[
        "Vaqt", "Ism Familiya", "Kurs", "Guruh", "Fan nomi",
        "Topshiriq turi", "Mavzu", "Fayl (Drive link)",
        "Ball", "Baho", "Holat", "O'tdimi"
    ]]
    sheets_svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": headers},
    ).execute()
    print("[SHEETS] Header qo'shildi.")
