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


def pretty_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def log_block(title: str, body: str = ""):
    if body:
        logger.info("%s\n%s", title, body)
    else:
        logger.info("%s", title)


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
        logger.warning("[GPS] 실시간 GPS 없음 → fallback GPS 사용: %s", gps_data)

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

        payload_for_log = dict(payload)
        payload_for_log["image"] = f"<base64 length={len(payload['image'])}>"

        log_block(
            "ANALYZE ▶ REQUEST",
            f"POST {url}\n{pretty_json(payload_for_log)}"
        )

        response = requests.post(
            url,
            json=payload,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        result = response.json()

        log_block(
            f"ANALYZE ◀ RESPONSE ({response.status_code})",
            pretty_json(result)
        )

        confirmed_events = result.get("confirmedEvents", [])
        logger.info(
            "ANALYZE PARSED | analysisOid=%s | isSmoke=%s | confidence=%s | confirmedEvents=%d",
            result.get("analysisOid"),
            result.get("isSmoke"),
            result.get("confidence"),
            len(confirmed_events),
        )

        for idx, event in enumerate(confirmed_events, start=1):
            logger.info(
                "  #%d %s %.6f | bbox_tlwh=%s",
                idx,
                event.get("final_event_class"),
                event.get("final_event_score", 0.0),
                event.get("bbox_tlwh"),
            )

        if getattr(config, "SAVE_RESPONSE_JSON", True):
            path = save_response_json(frame_name, result)
            logger.info("ANALYZE SAVE | %s", path)

        return result

    except Exception as e:
        log_block("ANALYZE ◀ ERROR", str(e))
        return None