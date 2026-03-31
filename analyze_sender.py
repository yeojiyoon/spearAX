import os
import json
import base64
import logging
from datetime import datetime, timezone
from typing import Optional

import cv2
import requests

import config
from gps_receiver import get_current_gps

logger = logging.getLogger("drone_pipeline")


def encode_frame_to_base64(frame) -> str:
    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        raise ValueError("프레임 JPEG 인코딩 실패")
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def make_timestamp_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_analyze_payload_from_frame(frame) -> dict:
    image_b64 = encode_frame_to_base64(frame)

    gps_data = get_current_gps()
    if gps_data is None:
        gps_data = config.DRONE_GPS
        logger.warning("[GPS] fallback GPS 사용")

    return {
        "droneOid": config.DRONE_OID,
        "image": image_b64,
        "gps": gps_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def save_response_json(frame_name: str, result: dict) -> str:
    timestamp_str = make_timestamp_str()
    save_name = f"{frame_name}_{timestamp_str}.json"
    save_path = os.path.join(config.RESPONSE_DIR, save_name)

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return save_path


def send_analyze_frame(frame, frame_name: str = "webcam_capture") -> Optional[dict]:
    url = config.BASE_URL + config.ANALYZE_ENDPOINT

    try:
        payload = build_analyze_payload_from_frame(frame)

        logger.info("[ANALYZE SEND] frame=%s | gps=%s", frame_name, payload["gps"])

        response = requests.post(
            url,
            json=payload,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        result = response.json()

        logger.info(
            "[ANALYZE SUCCESS] frame=%s | isSmoke=%s | confidence=%s | analysisOid=%s",
            frame_name,
            result.get("isSmoke"),
            result.get("confidence"),
            result.get("analysisOid"),
        )

        if getattr(config, "SAVE_RESPONSE_JSON", True):
            path = save_response_json(frame_name, result)
            logger.info("응답 JSON 저장: %s", path)

        return result

    except Exception as e:
        logger.error("[ANALYZE ERROR] %s", e)
        return None