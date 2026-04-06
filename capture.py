import cv2
import time
import os

# 저장 폴더
SAVE_DIR = "snapshots"
os.makedirs(SAVE_DIR, exist_ok=True)

# 웹캠 열기 (기본 웹캠: 0)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("웹캠을 열 수 없습니다. \n")
    exit()

last_save_time = 0
image_count = 0

print("웹캠 실행 중... 종료하려면 q를 누르세요. \n")

while True:
    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다.\n")
        break

    current_time = time.time()

    # 10초마다 저장
    if current_time - last_save_time >= 10:
        filename = os.path.join(SAVE_DIR, f"capture_{image_count:04d}.jpg")
        cv2.imwrite(filename, frame)
        print(f"저장됨: {filename} \n")
        image_count += 1
        last_save_time = current_time

    # 화면 출력
    cv2.imshow("Webcam", frame)

    # q 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()