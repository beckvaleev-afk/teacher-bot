"""
Google Drive + Google Sheets integration.
Uses Service Account credentials from environment variable.
No token.json or client_secrets.json needed on server.
"""
import os
import io
import json
import mimetypes
from datetime import datetime

SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "")
DRIVE_FOLDER   = "TeacherBot_Submissions"


def _get_credentials():
    """Load credentials from environment variable (Railway) or file (local)."""
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/spreadsheets",
    ]

    # Try environment variable first (Railway)
    creds_content = os.getenv("GOOGLE_CREDENTIALS_CONTENT", "")
    if creds_content and creds_content.strip().startswith("{"):
        try:
            info = json.loads(creds_content)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            print(f"[AUTH] Env credentials error: {e}")

    # Fallback: local file (development)
    creds_file = os.getenv("GOOGLE_CREDS_JSON", "google_credentials.json")
    if os.path.exists(creds_file):
        try:
            return Credentials.from_service_account_file(creds_file, scopes=scopes)
        except Exception as e:
            print(f"[AUTH] File credentials error: {e}")

    # OAuth2 token fallback (local dev with token.json)
    token_file = "token.json"
    if os.path.exists(token_file):
        try:
            from google.oauth2.credentials import Credentials as OAuthCreds
            from google.auth.transport.requests import Request
            creds = OAuthCreds.from_authorized_user_file(token_file, scopes)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds
        except Exception as e:
            print(f"[AUTH] Token file error: {e}")

    raise Exception(
        "Google credentials not found!\n"
        "Set GOOGLE_CREDENTIALS_CONTENT env variable on Railway."
    )


def _get_or_create_folder(service, folder_name: str) -> str:
    query   = (
        f"name='{folder_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id,name)").execute()
    files   = results.get("files", [])
    if files:
        return files[0]["id"]
    meta   = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=meta, fields="id").execute()
    print(f"[DRIVE] Papka yaratildi: {folder_name}")
    return folder["id"]


def _get_student_folder(service, parent_id: str, student_name: str) -> str:
    safe  = student_name.replace("/", "_").replace("\\", "_")[:100]
    query = (
        f"name='{safe}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id,name)").execute()
    files   = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name":     safe,
        "mimeType": "application/vnd.google-apps.folder",
        "parents":  [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    print(f"[DRIVE] Talaba papkasi yaratildi: {safe}")
    return folder["id"]


async def upload_to_drive(file_bytes: bytes, filename: str,
                           student_name: str = "Unknown") -> str:
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        creds      = _get_credentials()
        service    = build("drive", "v3", credentials=creds)
        main_fold  = _get_or_create_folder(service, DRIVE_FOLDER)
        stud_fold  = _get_student_folder(service, main_fold, student_name)

        mime_type, _ = mimetypes.guess_type(filename)
        mime_type    = mime_type or "application/octet-stream"

        file_meta = {"name": filename, "parents": [stud_fold]}
        media     = MediaIoBaseUpload(
            io.BytesIO(file_bytes), mimetype=mime_type, resumable=True
        )
        uploaded = service.files().create(
            body=file_meta, media_body=media, fields="id,name,webViewLink"
        ).execute()

        file_id   = uploaded["id"]
        file_link = uploaded.get("webViewLink", "")

        service.permissions().create(
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
        "Topshiriq turi", "Mavzu", "Fayl (Drive link)",
        "Ball", "Baho", "Holat", "O'tdimi"
    ]]
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": headers},
    ).execute()
    print("[SHEETS] Header qo'shildi.")
