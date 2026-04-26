"""
Face verification using OpenCV Haar Cascades.
100% free, runs locally, no external API needed.
"""
import base64
import os
import urllib.request

import cv2
import numpy as np


def _get_cascade_path(filename: str) -> str:
    cv2_dir = os.path.dirname(cv2.__file__)
    candidates = [
        os.path.join(cv2_dir, "data", filename),
        os.path.join(cv2_dir, filename),
        os.path.join(os.path.dirname(cv2_dir), "data", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    local_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(local_path):
        url = (
            "https://raw.githubusercontent.com/opencv/opencv/"
            f"master/data/haarcascades/{filename}"
        )
        print(f"[FACE] Yuklanmoqda: {filename}")
        urllib.request.urlretrieve(url, local_path)
    return local_path


try:
    _face_cascade = cv2.CascadeClassifier(
        _get_cascade_path("haarcascade_frontalface_default.xml")
    )
    _eye_cascade = cv2.CascadeClassifier(
        _get_cascade_path("haarcascade_eye.xml")
    )
    print("[FACE] OpenCV yuklandi.")
except Exception as _e:
    print(f"[FACE] Ogohlantirish: {_e}")
    _face_cascade = None
    _eye_cascade  = None


def _decode_image(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _run_detection(img) -> dict:
    if _face_cascade is None:
        return {"verified": False, "reason": "Detektor yuklanmadi."}
    if img is None:
        return {"verified": False, "reason": "Rasm o'qilmadi."}

    gray  = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )

    if len(faces) == 0:
        return {
            "verified": False,
            "reason": (
                "Yuz aniqlanmadi.\n"
                "- Yaxshi yoritilgan joyda turing\n"
                "- Kameraga to'g'ridan qarang\n"
                "- Yuzingizni to'liq ko'rsating"
            ),
        }
    if len(faces) > 1:
        return {
            "verified": False,
            "reason": f"{len(faces)} ta yuz aniqlandi. Faqat siz bo'lishingiz kerak.",
        }

    x, y, w, h = faces[0]
    eyes = _eye_cascade.detectMultiScale(
        gray[y:y+h, x:x+w], scaleFactor=1.1, minNeighbors=3, minSize=(20, 20),
    )
    if len(eyes) == 0:
        return {
            "verified": False,
            "reason": (
                "Ko'zlar aniqlanmadi.\n"
                "- Ko'zlaringizni oching\n"
                "- Kameraga to'g'ridan qarang"
            ),
        }

    coverage = (w * h) / (img.shape[0] * img.shape[1])
    if coverage < 0.04:
        return {"verified": False, "reason": "Yuz juda kichik. Kameraga yaqinroq keling."}

    print(f"[FACE] OK — 1 yuz, {len(eyes)} ko'z, {coverage:.1%}")
    return {"verified": True}


async def verify_face(image_bytes: bytes) -> dict:
    return _run_detection(_decode_image(image_bytes))
