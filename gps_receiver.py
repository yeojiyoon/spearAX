from pymavlink import mavutil
import threading
import time
import config

# 최신 GPS 캐싱
_latest_gps = None
_lock = threading.Lock()


def _select_mavlink_connection():
    default_conn = config.MAVLINK_CONNECTION

    # 기본값 파싱 (udp:127.0.0.1:14550 → ip, port 추출)
    try:
        _, ip, port = default_conn.split(":")
    except:
        ip, port = "127.0.0.1", "14550"

    while True:
        answer = input(
            f"기존 연결값 [{default_conn}] 사용? (y/n): "
        ).strip().lower()

        if answer == "y":
            print(f"config 값 사용: {default_conn}")
            return default_conn

        elif answer == "n":
            new_ip = input(f"IP 입력 (기본: {ip}): ").strip()
            new_port = input(f"PORT 입력 (기본: {port}): ").strip()

            # 빈값이면 기본값 사용
            new_ip = new_ip if new_ip else ip
            new_port = new_port if new_port else port

            new_conn = f"udp:{new_ip}:{new_port}"

            print(f"새 연결값 사용: {new_conn}")
            return new_conn

        else:
            print("y 또는 n만 입력해주세요.")


selected_connection = _select_mavlink_connection()
master = mavutil.mavlink_connection(selected_connection)

print("MAVLink 연결 대기 중...")
master.wait_heartbeat()
print("드론 연결 완료")


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


# 백그라운드 스레드 시작
threading.Thread(target=_gps_listener, daemon=True).start()


def get_current_gps():
    with _lock:
        return _latest_gps