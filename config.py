import os

# ===== 서버 설정 =====
BASE_URL = "http://39.121.224.150:10116"
ANALYZE_ENDPOINT = "/api/drone/analyze"
TARGET_LOCATION_ENDPOINT = "/api/drone/target-location"

# ===== 주기 설정 =====
CAPTURE_INTERVAL_SECONDS = 10

# ===== 웹캠 설정 =====
WEBCAM_INDEX = 0

# ===== MAVLink 설정 =====
MAVLINK_CONNECTION = "udp:127.0.0.1:14550"

# ===== 경로 설정 =====
LOG_DIR = "./logs"
RESPONSE_DIR = "./responses"
FAIL_DIR = "./failed_frames"

# ===== 저장 옵션 =====
SAVE_RESPONSE_JSON = True
SAVE_FAILED_FRAMES = True

# ===== 드론 정보 =====
DRONE_OID = "drone-test"

# ===== 대략적 타겟 GPS 계산용 =====
APPROX_TARGET_GPS_ENABLED = True

# 카메라가 지면을 내려다본다고 아주 단순 가정했을 때,
# 고도 100m에서 화면 전체가 대략 몇 m를 커버하는지에 대한 러프 스케일
GROUND_WIDTH_METERS_AT_100M = 120.0
GROUND_HEIGHT_METERS_AT_100M = 90.0

# GPS 없을 때 fallback
USE_FALLBACK_DRONE_GPS = True

# fallback용 (GPS 못 받을 때만 사용)
DRONE_GPS = {
    "lat": 35.8714,
    "lng": 128.6014,
    "alt": 100.0,
}

# ===== 2번 API 임시 targetGps =====
DEFAULT_TARGET_GPS = {
    "lat": 35.8714,
    "lng": 128.6014,
    "alt": 0.0,
}

# ===== 요청 설정 =====
REQUEST_TIMEOUT = 30

# ===== 허용 확장자 =====
VALID_EXTENSIONS = (".jpg", ".jpeg", ".png")

# ===== 폴더 생성 =====
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(RESPONSE_DIR, exist_ok=True)
os.makedirs(FAIL_DIR, exist_ok=True)