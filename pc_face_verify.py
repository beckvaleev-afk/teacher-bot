"""
PC Face Verification Script
============================
Bu skriptni ishga tushiring:
  python pc_face_verify.py YOUR_TELEGRAM_USER_ID

Kerak bo'lgan kutubxonalar:
  pip install opencv-python requests
"""
import sys
import time
import cv2
import requests
import tempfile
import os

# ── Bot API settings ──────────────────────────────────────
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # .env dan oling
API_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"

COUNTDOWN = 3   # seconds to look at camera


def send_photo_to_bot(user_id: int, image_path: str):
    """Send captured photo to Telegram bot."""
    url = f"{API_URL}/sendPhoto"
    with open(image_path, "rb") as f:
        resp = requests.post(url, data={"chat_id": user_id}, files={"photo": f})
    return resp.ok


def run_face_capture(user_id: int):
    print("\n" + "="*50)
    print("  Teacher Bot — PC Yuz Tasdiqlash")
    print("="*50)

    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("\nXATO: Webcam topilmadi!")
        print("Webcam ulanganligini tekshiring.")
        return

    print("\nWebcam ochildi. Kameraga qarab turing.\n")
    time.sleep(1)

    # Load face detector
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # Countdown
    for i in range(COUNTDOWN, 0, -1):
        ret, frame = cap.read()
        if not ret:
            break
        display = frame.copy()

        # Show countdown on frame
        h, w = display.shape[:2]
        cv2.putText(display, f"{i}", (w//2 - 40, h//2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 255, 255), 8)
        cv2.putText(display, "Kameraga qarab turing",
                    (w//2 - 200, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Teacher Bot — Yuz Tasdiqlash", display)
        cv2.waitKey(1000)
        print(f"  {i}...")

    # Capture final frame
    ret, frame = cap.read()
    cap.release()
    cv2.destroyAllWindows()

    if not ret:
        print("\nXATO: Rasm olinmadi.")
        return

    # Check face present
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

    if len(faces) == 0:
        print("\nXATO: Yuz aniqlanmadi!")
        print("Qayta ishga tushiring va kameraga to'g'ridan qarang.")
        return

    print(f"\nYuz aniqlandi! Bot ga yuborilmoqda...")

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(tmp.name, frame)
    tmp.close()

    # Send to bot
    ok = send_photo_to_bot(user_id, tmp.name)
    os.unlink(tmp.name)

    if ok:
        print("Rasm muvaffaqiyatli yuborildi!")
        print("Telegram botni tekshiring — test boshlanishi kerak.")
    else:
        print("XATO: Bot ga yuborishda muammo.")
        print("Internet aloqasini tekshiring.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Foydalanish: python pc_face_verify.py YOUR_TELEGRAM_USER_ID")
        print("\nTelegram ID ni bilish uchun @userinfobot ga /start yuboring.")
        sys.exit(1)

    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print("XATO: Telegram ID raqam bo'lishi kerak.")
        sys.exit(1)

    run_face_capture(user_id)
