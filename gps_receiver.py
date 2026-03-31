from pymavlink import mavutil
import threading
import time
import config

master = mavutil.mavlink_connection(config.MAVLINK_CONNECTION)

print("MAVLink 연결 대기 중...")
master.wait_heartbeat()
print("드론 연결 완료")

# 🔥 최신 GPS 캐싱
_latest_gps = None
_lock = threading.Lock()


def _gps_listener():
    global _latest_gps

    while True:
        msg = master.recv_match(type="GLOBAL_POSITION_INT", blocking=True)

        if msg:
            gps = {
                "lat": msg.lat / 1e7,
                "lng": msg.lon / 1e7,
                "alt": msg.alt / 1000,
            }

            with _lock:
                _latest_gps = gps


# 🔥 백그라운드 스레드 시작
threading.Thread(target=_gps_listener, daemon=True).start()


def get_current_gps():
    with _lock:
        return _latest_gps