"""
import time
import logging
import threading
from typing import Optional

import cv2

import config
from analyze_sender import send_analyze_frame
from target_sender import send_target_from_result

logger = logging.getLogger("drone_pipeline")
logging.basicConfig(level=logging.INFO)


def save_failed_frame(frame, prefix="failed") -> Optional[str]:
    if not config.SAVE_FAILED_FRAMES:
        return None

    try:
        filename = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        path = f"{config.FAIL_DIR}/{filename}"
        cv2.imwrite(path, frame)
        logger.info("[FAIL SAVE] %s", path)
        return path
    except:
        return None


def webcam_loop():
    cap = cv2.VideoCapture(config.WEBCAM_INDEX)

    if not cap.isOpened():
        logger.error("웹캠 없음 → GPS만 수신 상태 유지")
        while True:
            time.sleep(1)

    last = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue

        now = time.time()

        if now - last >= config.CAPTURE_INTERVAL_SECONDS:
            name = f"webcam_{time.strftime('%Y%m%d_%H%M%S')}"

            logger.info("[CAPTURE]")

            result = send_analyze_frame(frame, name)

            if not result:
                save_failed_frame(frame, "analyze_fail")
                last = now
                continue

            ok = send_target_from_result(result)

            if not ok:
                save_failed_frame(frame, "target_fail")

            last = now

        time.sleep(0.1)


def main():
    threading.Thread(target=webcam_loop, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
"""

import time
import logging
import threading
from typing import Optional

import numpy as np
import cv2

import config
from analyze_sender import send_analyze_frame
from target_sender import send_target_from_result

logger = logging.getLogger("drone_pipeline")
logging.basicConfig(level=logging.INFO)


def save_failed_frame(frame, prefix="failed") -> Optional[str]:
    if not config.SAVE_FAILED_FRAMES:
        return None

    try:
        filename = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        path = f"{config.FAIL_DIR}/{filename}"
        cv2.imwrite(path, frame)
        logger.info("[FAIL SAVE] %s", path)
        return path
    except:
        return None


# 🔥 여기 핵심: 랜덤 프레임 생성
def generate_fake_frame():
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


def fake_camera_loop():
    logger.info("=== FAKE CAMERA PIPELINE 시작 ===")

    last = 0

    while True:
        now = time.time()

        if now - last >= config.CAPTURE_INTERVAL_SECONDS:
            frame = generate_fake_frame()
            name = f"fake_{time.strftime('%Y%m%d_%H%M%S')}"

            logger.info("[FAKE CAPTURE]")

            result = send_analyze_frame(frame, name)

            if not result:
                save_failed_frame(frame, "analyze_fail")
                last = now
                continue

            ok = send_target_from_result(result)

            if not ok:
                save_failed_frame(frame, "target_fail")

            last = now

        time.sleep(0.1)


def main():
    threading.Thread(target=fake_camera_loop, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()