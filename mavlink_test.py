from pymavlink import mavutil
import threading
import time
import copy
import config

master = mavutil.mavlink_connection(config.MAVLINK_CONNECTION)

print("MAVLink 연결 대기 중...\n")
master.wait_heartbeat()
print("드론 연결 완료\n")

_latest = {
    "global": None,
    "local": None,
    "gps_raw": None,
}
_lock = threading.Lock()


def request_message_interval(msg_id: int, hz: float):
    """
    특정 MAVLink 메시지를 원하는 주기로 요청
    hz=5 -> 5Hz
    """
    interval_us = int(1e6 / hz)

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        msg_id,
        interval_us,
        0, 0, 0, 0, 0
    )


def setup_stream_rates():
    # MAVLink common message IDs
    # GLOBAL_POSITION_INT = 33
    # LOCAL_POSITION_NED  = 32
    # GPS_RAW_INT         = 24
    request_message_interval(33, 5)  # 5Hz
    request_message_interval(32, 5)  # 5Hz
    request_message_interval(24, 2)  # 2Hz


def _receiver():
    while True:
        msg = master.recv_match(
            type=["GLOBAL_POSITION_INT", "LOCAL_POSITION_NED", "GPS_RAW_INT"],
            blocking=True
        )
        if not msg:
            continue

        msg_type = msg.get_type()

        with _lock:
            if msg_type == "GLOBAL_POSITION_INT":
                _latest["global"] = {
                    "time_boot_ms": getattr(msg, "time_boot_ms", None),
                    "lat": msg.lat / 1e7,
                    "lng": msg.lon / 1e7,
                    "alt_msl_m": msg.alt / 1000.0,
                    "relative_alt_m": msg.relative_alt / 1000.0,
                    # GLOBAL_POSITION_INT 속도 단위는 cm/s
                    "vx_mps": msg.vx / 100.0,
                    "vy_mps": msg.vy / 100.0,
                    "vz_mps": msg.vz / 100.0,
                    # hdg는 cdeg (0.01 deg), 65535면 unknown
                    "hdg_deg": None if msg.hdg == 65535 else msg.hdg / 100.0,
                }

            elif msg_type == "LOCAL_POSITION_NED":
                _latest["local"] = {
                    "time_boot_ms": getattr(msg, "time_boot_ms", None),
                    "x_m": msg.x,
                    "y_m": msg.y,
                    "z_m": msg.z,
                    "vx_mps": msg.vx,
                    "vy_mps": msg.vy,
                    "vz_mps": msg.vz,
                }

            elif msg_type == "GPS_RAW_INT":
                _latest["gps_raw"] = {
                    "time_usec": getattr(msg, "time_usec", None),
                    "fix_type": getattr(msg, "fix_type", None),
                    "lat": getattr(msg, "lat", None) / 1e7 if getattr(msg, "lat", None) is not None else None,
                    "lng": getattr(msg, "lon", None) / 1e7 if getattr(msg, "lon", None) is not None else None,
                    "alt_msl_m": getattr(msg, "alt", None) / 1000.0 if getattr(msg, "alt", None) is not None else None,
                    "vel_mps": None if getattr(msg, "vel", None) in (None, 65535) else msg.vel / 100.0,
                    "cog_deg": None if getattr(msg, "cog", None) in (None, 65535) else msg.cog / 100.0,
                    "satellites_visible": getattr(msg, "satellites_visible", None),
                    "eph": None if getattr(msg, "eph", None) == 65535 else getattr(msg, "eph", None),
                    "epv": None if getattr(msg, "epv", None) == 65535 else getattr(msg, "epv", None),
                }


def get_debug_position():
    with _lock:
        return copy.deepcopy(_latest)


def _fmt_float(v, digits=3):
    if v is None:
        return "None"
    return f"{v:.{digits}f}"


def _delta(a, b):
    if a is None or b is None:
        return None
    return b - a


def _monitor():
    prev = {
        "global": None,
        "local": None,
        "gps_raw": None,
    }

    while True:
        time.sleep(1)

        cur = get_debug_position()

        print("\n" + "=" * 70)
        print("[1초 주기 위치 디버그]")

        # GLOBAL_POSITION_INT
        g = cur["global"]
        if g is None:
            print("GLOBAL_POSITION_INT : 아직 수신 안 됨")
        else:
            dg_lat = dg_lng = dg_alt = None
            if prev["global"] is not None:
                dg_lat = _delta(prev["global"]["lat"], g["lat"])
                dg_lng = _delta(prev["global"]["lng"], g["lng"])
                dg_alt = _delta(prev["global"]["relative_alt_m"], g["relative_alt_m"])

            print("GLOBAL_POSITION_INT")
            print(f"  boot_ms   : {g['time_boot_ms']}")
            print(f"  lat/lng   : {_fmt_float(g['lat'], 7)}, {_fmt_float(g['lng'], 7)}")
            print(f"  rel_alt   : {_fmt_float(g['relative_alt_m'])} m")
            print(f"  vel xyz   : {_fmt_float(g['vx_mps'])}, {_fmt_float(g['vy_mps'])}, {_fmt_float(g['vz_mps'])} m/s")
            print(f"  hdg       : {g['hdg_deg']}")
            print(f"  Δlat/lng  : {_fmt_float(dg_lat, 7) if dg_lat is not None else 'None'}, "
                  f"{_fmt_float(dg_lng, 7) if dg_lng is not None else 'None'}")
            print(f"  Δrel_alt  : {_fmt_float(dg_alt) if dg_alt is not None else 'None'}")

        # LOCAL_POSITION_NED
        l = cur["local"]
        if l is None:
            print("LOCAL_POSITION_NED  : 아직 수신 안 됨")
        else:
            dl_x = dl_y = dl_z = None
            if prev["local"] is not None:
                dl_x = _delta(prev["local"]["x_m"], l["x_m"])
                dl_y = _delta(prev["local"]["y_m"], l["y_m"])
                dl_z = _delta(prev["local"]["z_m"], l["z_m"])

            print("LOCAL_POSITION_NED")
            print(f"  boot_ms   : {l['time_boot_ms']}")
            print(f"  x/y/z     : {_fmt_float(l['x_m'])}, {_fmt_float(l['y_m'])}, {_fmt_float(l['z_m'])} m")
            print(f"  vel xyz   : {_fmt_float(l['vx_mps'])}, {_fmt_float(l['vy_mps'])}, {_fmt_float(l['vz_mps'])} m/s")
            print(f"  Δx/y/z    : {_fmt_float(dl_x) if dl_x is not None else 'None'}, "
                  f"{_fmt_float(dl_y) if dl_y is not None else 'None'}, "
                  f"{_fmt_float(dl_z) if dl_z is not None else 'None'}")

        # GPS_RAW_INT
        r = cur["gps_raw"]
        if r is None:
            print("GPS_RAW_INT         : 아직 수신 안 됨")
        else:
            dr_lat = dr_lng = None
            if prev["gps_raw"] is not None:
                dr_lat = _delta(prev["gps_raw"]["lat"], r["lat"])
                dr_lng = _delta(prev["gps_raw"]["lng"], r["lng"])

            print("GPS_RAW_INT")
            print(f"  time_usec : {r['time_usec']}")
            print(f"  fix_type  : {r['fix_type']}")
            print(f"  sats      : {r['satellites_visible']}")
            print(f"  lat/lng   : {_fmt_float(r['lat'], 7)}, {_fmt_float(r['lng'], 7)}")
            print(f"  alt_msl   : {_fmt_float(r['alt_msl_m'])} m")
            print(f"  vel/cog   : {_fmt_float(r['vel_mps'])} m/s, {_fmt_float(r['cog_deg'])} deg")
            print(f"  eph/epv   : {r['eph']}, {r['epv']}")
            print(f"  Δlat/lng  : {_fmt_float(dr_lat, 7) if dr_lat is not None else 'None'}, "
                  f"{_fmt_float(dr_lng, 7) if dr_lng is not None else 'None'}")

        prev = cur


if __name__ == "__main__":
    setup_stream_rates()

    threading.Thread(target=_receiver, daemon=True).start()
    threading.Thread(target=_monitor, daemon=True).start()

    while True:
        time.sleep(10)