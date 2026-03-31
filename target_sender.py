import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
import config

logger = logging.getLogger("drone_pipeline")


def should_send_target(result: dict) -> bool:
    return bool(result.get("isSmoke", False))


def build_target_payload(result: dict) -> dict:
    analysis_oid = result.get("analysisOid")

    if not analysis_oid:
        raise ValueError("analysisOid 없음")

    return {
        "analysisOid": analysis_oid,
        "targetGps": config.DEFAULT_TARGET_GPS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def send_target_from_result(result: dict, source="memory") -> bool:
    url = config.BASE_URL + config.TARGET_LOCATION_ENDPOINT

    try:
        if not should_send_target(result):
            logger.info("[TARGET SKIP] isSmoke=False")
            return False

        payload = build_target_payload(result)

        logger.info("[TARGET SEND] %s", json.dumps(payload))

        response = requests.post(url, json=payload, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()

        logger.info("[TARGET SUCCESS]")
        return True

    except Exception as e:
        logger.error("[TARGET ERROR] %s", e)
        return False