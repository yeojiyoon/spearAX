import json
import logging
import math
from datetime import datetime, timezone

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


def should_send_target(result: dict) -> bool:
    return bool(result.get("isSmoke", False))


def meters_to_latlng(base_lat: float, base_lng: float, north_m: float, east_m: float):
    lat_per_meter = 1 / 111320.0
    lng_per_meter = 1 / (111320.0 * math.cos(math.radians(base_lat)))

    new_lat = base_lat + north_m * lat_per_meter
    new_lng = base_lng + east_m * lng_per_meter
    return new_lat, new_lng


def get_drone_gps():
    gps = get_current_gps()

    if gps:
        return gps

    if getattr(config, "USE_FALLBACK_DRONE_GPS", True):
        logger.warning("[GPS] 실시간 GPS 없음 → fallback GPS 사용: %s", config.DRONE_GPS)
        return config.DRONE_GPS

    return None


def tlwh_to_xyxy(bbox_tlwh):
    x, y, w, h = bbox_tlwh
    return [x, y, x + w, y + h]


def estimate_target_gps_from_bbox(bbox, drone_gps, frame_width, frame_height):
    x1, y1, x2, y2 = bbox

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0

    frame_cx = frame_width / 2.0
    frame_cy = frame_height / 2.0

    dx_norm = (cx - frame_cx) / frame_cx
    dy_norm = (cy - frame_cy) / frame_cy

    drone_alt = drone_gps.get("alt", 100.0)
    if drone_alt is None or drone_alt <= 0:
        drone_alt = 100.0

    width_at_100m = config.GROUND_WIDTH_METERS_AT_100M
    height_at_100m = config.GROUND_HEIGHT_METERS_AT_100M

    ground_width_m = width_at_100m * (drone_alt / 100.0)
    ground_height_m = height_at_100m * (drone_alt / 100.0)

    east_offset_m = dx_norm * (ground_width_m / 2.0)
    north_offset_m = -dy_norm * (ground_height_m / 2.0)

    lat, lng = meters_to_latlng(
        drone_gps["lat"],
        drone_gps["lng"],
        north_offset_m,
        east_offset_m,
    )

    return {
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "alt": 0.0
    }


def build_targets(result: dict):
    confirmed_events = result.get("confirmedEvents", [])
    drone_gps = get_drone_gps()

    if not drone_gps:
        raise ValueError("드론 GPS를 사용할 수 없음")

    frame_width = result.get("frameWidth", 320)
    frame_height = result.get("frameHeight", 180)

    targets = []

    for idx, event in enumerate(confirmed_events, start=1):
        bbox_tlwh = event.get("bbox_tlwh")
        event_class = event.get("final_event_class")
        score = event.get("final_event_score")

        if not bbox_tlwh or len(bbox_tlwh) != 4:
            logger.warning("TARGET SKIP | #%d bbox_tlwh 형식 불일치", idx)
            continue

        bbox = tlwh_to_xyxy(bbox_tlwh)

        target_gps = estimate_target_gps_from_bbox(
            bbox=bbox,
            drone_gps=drone_gps,
            frame_width=frame_width,
            frame_height=frame_height,
        )

        targets.append({
            "eventClass": event_class,
            "score": round(score, 2) if score is not None else None,
            "targetGps": target_gps,
        })

    return targets


def build_target_payload(result: dict) -> dict:
    analysis_oid = result.get("analysisOid")
    if not analysis_oid:
        raise ValueError("analysisOid 없음")

    targets = build_targets(result)

    return {
        "analysisOid": analysis_oid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "targets": targets,
    }


def send_target_from_result(result: dict) -> str:
    url = config.BASE_URL + config.TARGET_LOCATION_ENDPOINT

    try:
        if not should_send_target(result):
            log_block("TARGET SKIP", "isSmoke=False")
            return "skip"

        payload = build_target_payload(result)

        if not payload["targets"]:
            log_block("TARGET SKIP", "전송할 targets 없음")
            return "skip"

        log_block(
            f"TARGET ▶ REQUEST ({len(payload['targets'])} targets)",
            pretty_json(payload)
        )

        response = requests.post(
            url,
            json=payload,
            timeout=config.REQUEST_TIMEOUT
        )

        if not response.ok:
            log_block(
                f"TARGET ◀ ERROR ({response.status_code})",
                response.text or "Internal server error"
            )
            return "error"

        try:
            response_json = response.json()
            body = pretty_json(response_json)
        except Exception:
            body = response.text

        log_block(
            f"TARGET ◀ RESPONSE ({response.status_code})",
            body
        )

        return "success"

    except Exception as e:
        log_block("TARGET ◀ ERROR", str(e))
        return "error"