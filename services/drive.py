"""
Google Drive + Google Sheets integration.
Files uploaded to owner's Drive folder (not service account storage).
"""
import os
import io
import json
import mimetypes
from datetime import datetime

SPREADSHEET_ID  = os.getenv("GOOGLE_SHEETS_ID", "")
DRIVE_FOLDER    = "TeacherBot_Submissions"
PARENT_FOLDER_ID = "1IngrYBU-kSdok8Oudf6-GoYO1vE3T1UJ"  # Owner's Drive folder


def _get_credentials():
    from google.oauth2.service_account import Credentials
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    creds_content = os.getenv("GOOGLE_CREDENTIALS_CONTENT", "")
    if creds_content and creds_content.strip().startswith("{"):
        try:
            info = json.loads(creds_content)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            print(f"[AUTH] Env credentials error: {e}")

    creds_file = os.getenv("GOOGLE_CREDS_JSON", "google_credentials.json")
    if os.path.exists(creds_file):
        try:
            return Credentials.from_service_account_file(creds_file, scopes=scopes)
        except Exception as e:
            print(f"[AUTH] File credentials error: {e}")

    raise Exception("Google credentials not found!")


def _get_or_create_subfolder(service, parent_id: str, folder_name: str) -> str:
    safe  = folder_name.replace("/", "_").replace("\\", "_")[:100]
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
    print(f"[DRIVE] Papka yaratildi: {safe}")
    return folder["id"]


async def upload_to_drive(file_bytes: bytes, filename: str,
                           student_name: str = "Unknown") -> str:
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        creds   = _get_credentials()
        service = build("drive", "v3", credentials=creds)

        # Create student subfolder inside owner's folder
        student_folder = _get_or_create_subfolder(
            service, PARENT_FOLDER_ID, student_name
        )

        mime_type, _ = mimetypes.guess_type(filename)
        mime_type    = mime_type or "application/octet-stream"

        file_meta = {"name": filename, "parents": [student_folder]}
        media     = MediaIoBaseUpload(
            io.BytesIO(file_bytes), mimetype=mime_type, resumable=True
        )
        uploaded = service.files().create(
            body=file_meta, media_body=media, fields="id,name,webViewLink"
        ).execute()

        file_id   = uploaded["id"]
        file_link = uploaded.get("webViewLink", "")

        # Make viewable by anyone with link
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
