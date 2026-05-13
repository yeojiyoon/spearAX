# spearAX

`spearAX`는 드론 또는 지상 장비의 웹캠 영상을 주기적으로 캡처하고, 분석 서버에 프레임과 GPS 정보를 전송한 뒤, 연기 감지 결과가 확인되면 타겟 위치 정보를 다시 서버로 전송하는 Python 기반 드론 영상 처리 파이프라인입니다.

## 주요 기능

- 웹캠 프레임을 일정 주기마다 캡처
- 프레임을 JPEG/Base64로 인코딩해 분석 API로 전송
- MAVLink `GLOBAL_POSITION_INT` 메시지에서 드론 GPS 수신
- GPS 수신 실패 시 설정된 fallback GPS 사용
- 분석 결과에서 연기 감지 여부와 이벤트 bbox 확인
- bbox 중심점과 드론 GPS를 이용해 대략적인 타겟 GPS 계산
- 타겟 위치 API로 분석 결과 및 타겟 좌표 전송
- 분석 응답 JSON, 실패 프레임, 로그 디렉터리 관리
- PyInstaller 기반 단일 실행 파일 빌드 지원
- GitHub Actions를 통한 Linux 빌드 아티팩트 생성

## 처리 흐름

```text
웹캠 프레임 캡처
    ↓
/api/drone/analyze 로 이미지 + 드론 GPS 전송
    ↓
분석 결과 수신
    ↓
isSmoke=True 인 경우 confirmedEvents bbox 기반 타겟 GPS 계산
    ↓
/api/drone/target-location 로 타겟 위치 전송
```

## 프로젝트 구조

```text
.
├── main_loop.py          # 메인 실행 루프: 웹캠 캡처 및 전체 파이프라인 실행
├── analyze_sender.py     # 분석 API 요청 생성 및 응답 저장
├── target_sender.py      # 분석 결과 기반 타겟 좌표 계산 및 전송
├── gps_receiver.py       # MAVLink GPS 수신 및 최신 GPS 캐싱
├── mavlink_test.py       # MAVLink 위치 메시지 디버그용 스크립트
├── capture.py            # 웹캠 캡처 테스트 스크립트
├── config.py             # 서버, 웹캠, MAVLink, 저장 옵션 설정
├── requirements.txt      # Python 의존성 목록
├── spearax.spec          # PyInstaller 빌드 설정
└── .github/workflows/    # GitHub Actions 빌드 워크플로
```

## 요구 사항

- Python 3.11 권장
- 웹캠 또는 OpenCV에서 접근 가능한 카메라 장치
- MAVLink 데이터를 송신하는 드론, 시뮬레이터, 또는 QGroundControl/ArduPilot 환경
- 분석 서버 API 접근 가능 환경

Python 패키지:

```text
requests
opencv-python
pymavlink
pyinstaller
```

## 설치

```bash
git clone https://github.com/yeojiyoon/spearAX.git
cd spearAX
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell에서는 가상환경 활성화 명령이 다릅니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## 설정

실행 전 [config.py](config.py)를 환경에 맞게 수정합니다.

```python
BASE_URL = "http://39.121.224.150:10116"
ANALYZE_ENDPOINT = "/api/drone/analyze"
TARGET_LOCATION_ENDPOINT = "/api/drone/target-location"

CAPTURE_INTERVAL_SECONDS = 10
WEBCAM_INDEX = 0
MAVLINK_CONNECTION = "udp:127.0.0.1:14550"

DRONE_OID = "drone-test"
```

주요 설정:

| 항목 | 설명 |
| --- | --- |
| `BASE_URL` | 분석/타겟 위치 API 서버 주소 |
| `CAPTURE_INTERVAL_SECONDS` | 웹캠 프레임 캡처 주기 |
| `WEBCAM_INDEX` | OpenCV 웹캠 인덱스 |
| `MAVLINK_CONNECTION` | MAVLink 연결 문자열 |
| `SAVE_RESPONSE_JSON` | 분석 응답 JSON 저장 여부 |
| `SAVE_FAILED_FRAMES` | 실패 프레임 이미지 저장 여부 |
| `USE_FALLBACK_DRONE_GPS` | 실시간 GPS가 없을 때 fallback GPS 사용 여부 |
| `DRONE_GPS` | fallback GPS 좌표 |

## 실행

메인 파이프라인 실행:

```bash
python main_loop.py
```

실행 시 `gps_receiver.py`가 MAVLink 연결값 사용 여부를 묻습니다.

```text
기존 연결값 [udp:127.0.0.1:14550] 사용? (y/n):
```

- `y`: `config.py`의 `MAVLINK_CONNECTION` 사용
- `n`: IP와 PORT를 직접 입력

웹캠을 열 수 없으면 프로그램은 GPS 수신 상태만 유지합니다.

## 보조 스크립트

웹캠 캡처 테스트:

```bash
python capture.py
```

MAVLink 위치 데이터 디버그:

```bash
python mavlink_test.py
```

`mavlink_test.py`는 `GLOBAL_POSITION_INT`, `LOCAL_POSITION_NED`, `GPS_RAW_INT` 메시지를 주기적으로 출력합니다.

## 저장되는 파일

실행 중 아래 디렉터리가 자동 생성됩니다.

```text
logs/           # 로그 저장용 디렉터리
responses/      # 분석 API 응답 JSON 저장
failed_frames/  # 분석 또는 타겟 전송 실패 시 프레임 저장
snapshots/      # capture.py 실행 시 웹캠 캡처 이미지 저장
```

`responses/`, `failed_frames/`, `logs/`, `build/`, `dist/` 등 실행/빌드 산출물은 `.gitignore`에 포함되어 있습니다.

## 빌드

PyInstaller로 단일 실행 파일을 만들 수 있습니다.

```bash
pyinstaller --onefile --name spearax --collect-all pymavlink --hidden-import cv2 main_loop.py
```

또는 포함된 spec 파일을 사용할 수 있습니다.

```bash
pyinstaller spearax.spec
```

빌드 결과는 `dist/` 디렉터리에 생성됩니다.

## GitHub Actions

`.github/workflows/build.yml`은 `main` 브랜치 push 또는 수동 실행 시 Linux 환경에서 다음 작업을 수행합니다.

1. Python 3.11 설치
2. OpenCV 실행에 필요한 시스템 패키지 설치
3. `requirements.txt` 의존성 설치
4. PyInstaller로 `spearax` 실행 파일 빌드
5. `spearax-linux` 아티팩트 업로드

## API 요청 형식

분석 API 요청은 대략 다음 형태입니다.

```json
{
  "droneOid": "drone-test",
  "image": "<base64 encoded jpeg>",
  "gps": {
    "lat": 35.8714,
    "lng": 128.6014,
    "alt": 100.0
  },
  "timestamp": "2026-05-13T00:00:00+00:00"
}
```

타겟 위치 API 요청은 분석 결과의 `analysisOid`와 `confirmedEvents`를 기반으로 생성됩니다.

```json
{
  "analysisOid": "analysis-id",
  "timestamp": "2026-05-13T00:00:00+00:00",
  "targets": [
    {
      "eventClass": "smoke",
      "score": 0.95,
      "targetGps": {
        "lat": 35.8714,
        "lng": 128.6014,
        "alt": 0.0
      }
    }
  ]
}
```

## 참고 사항

- `target_sender.py`의 타겟 GPS 계산은 카메라가 지면을 내려다본다는 단순 가정에 기반한 근사값입니다.
- 정확한 위치 산출이 필요한 경우 카메라 FOV, 자세 정보, 고도, 짐벌 각도, 지형 정보 등을 함께 반영해야 합니다.
- `config.py`의 서버 주소, 드론 식별자, fallback GPS는 운영 환경에 맞게 반드시 확인하세요.
