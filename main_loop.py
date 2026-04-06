import time
import logging
import threading
from typing import Optional

import cv2

import config
from analyze_sender import send_analyze_frame
from target_sender import send_target_from_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("drone_pipeline")


def print_divider(title: str):
    line = "=" * 80
    logger.info("\n%s\n[ %s ]\n%s", line, title, line)


def save_failed_frame(frame, prefix="failed") -> Optional[str]:
    if not config.SAVE_FAILED_FRAMES:
        return None

    try:
        filename = f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        path = f"{config.FAIL_DIR}/{filename}"
        cv2.imwrite(path, frame)
        logger.info("[FAIL SAVE] %s", path)
        return path
    except Exception:
        logger.exception("[FAIL SAVE ERROR] 실패 프레임 저장 중 오류")
        return None


def webcam_loop():
    cap = cv2.VideoCapture(config.WEBCAM_INDEX)

    if not cap.isOpened():
        logger.error("[WEBCAM] 웹캠 열기 실패 → GPS 수신만 유지")
        while True:
            time.sleep(1)

    last = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("[WEBCAM] 프레임 읽기 실패")
            time.sleep(1)
            continue

        now = time.time()

        if now - last >= config.CAPTURE_INTERVAL_SECONDS:
            frame_name = f"webcam_{time.strftime('%Y%m%d_%H%M%S')}"

            print_divider(f"PIPELINE START | frame={frame_name}")

            result = send_analyze_frame(frame, frame_name)

            if not result:
                logger.error("[PIPELINE] analyze 실패")
                save_failed_frame(frame, "analyze_fail")
                last = now
                print_divider(f"PIPELINE END | frame={frame_name}")
                continue

            target_status = send_target_from_result(result)

            if target_status == "error":
                logger.error("[PIPELINE] target-location 실패")
                save_failed_frame(frame, "target_fail")
            else:
                logger.info("[PIPELINE] target 처리 결과: %s", target_status)

            print_divider(f"PIPELINE END | frame={frame_name}")
            last = now

        time.sleep(0.1)


def main():
    threading.Thread(target=webcam_loop, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()