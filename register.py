
import cv2
import mediapipe as mp
import os
import time

# Хүний нэр авах
name = input("Нэрээ оруулна уу: ").strip()

if not name or name in (".", "..") or "/" in name or "\\" in name:
    print("Зөв нэр оруулна уу!")
    raise SystemExit

folder = os.path.join("dataset", name)
os.makedirs(folder, exist_ok=True)

# Нүүр илрүүлэгч
detector = mp.solutions.face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

stages = [
    "Front - No Glasses",
    "Front - With Glasses",
    "Turn Head Right",
    "Turn Head Left"
]

photos_per_stage = 3
stage_index = 0
stage_saved = 0
saved_total = 0

capture_started = None
next_capture_time = 0
message = "Press SPACE to start"

# Зургийн нэр давхцахаас хамгаалах
def get_image_path():
    number = 1

    while True:
        filename = f"{name}_new_{number}.jpg"
        path = os.path.join(folder, filename)

        if not os.path.exists(path):
            return path

        number += 1


# Зургийн чанар шалгах
def check_quality(image):
    if image.size == 0:
        return False, "Invalid image"

    height, width = image.shape[:2]

    if width < 90 or height < 90:
        return False, "Move closer to camera"

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

    if sharpness < 35:
        return False, "Image blurry - hold still"

    return True, "Good quality"


cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

if not cap.isOpened():
    print("Камер нээгдсэнгүй!")
    detector.close()
    raise SystemExit

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("\nБүртгэл эхэллээ!")
print("SPACE = Зураг авч эхлэх")
print("N = Үе шат алгасах")
print("Q = Гарах")

while stage_index < len(stages):
    ret, frame = cap.read()

    if not ret:
        print("Камерын дүрс авч чадсангүй!")
        break

    # Толин тусгал
    frame = cv2.flip(frame, 1)

    height, width = frame.shape[:2]

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = detector.process(rgb)

    faces = []

    if results.detections:
        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box

            x1 = max(0, int(bbox.xmin * width))
            y1 = max(0, int(bbox.ymin * height))
            x2 = min(width, int((bbox.xmin + bbox.width) * width))
            y2 = min(height, int((bbox.ymin + bbox.height) * height))

            if x2 > x1 and y2 > y1:
                faces.append((x1, y1, x2, y2))

    # Дэлгэц дээр мэдээлэл харуулах
    cv2.putText(
        frame, stages[stage_index], (15, 35),
        cv2.FONT_HERSHEY_SIMPLEX, 0.65,
        (0, 255, 255), 2
    )

    cv2.putText(
        frame, f"Stage: {stage_index + 1}/{len(stages)}",
        (15, 70), cv2.FONT_HERSHEY_SIMPLEX,
        0.6, (255, 255, 255), 2
    )

    cv2.putText(
        frame, f"Saved: {stage_saved}/{photos_per_stage}",
        (15, 105), cv2.FONT_HERSHEY_SIMPLEX,
        0.6, (0, 255, 0), 2
    )

    cv2.putText(
        frame, message[:45], (15, height - 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55,
        (255, 255, 255), 2
    )

    face_image = None
    quality_ok = False

    if len(faces) == 1:
        x1, y1, x2, y2 = faces[0]

        padding = int((x2 - x1) * 0.15)

        left = max(0, x1 - padding)
        top = max(0, y1 - padding)
        right = min(width, x2 + padding)
        bottom = min(height, y2 + padding)

        face_image = frame[top:bottom, left:right].copy()

        quality_ok, quality_message = check_quality(face_image)

        color = (0, 255, 0) if quality_ok else (0, 0, 255)

        cv2.rectangle(
            frame, (x1, y1), (x2, y2),
            color, 2
        )

        cv2.putText(
            frame, quality_message,
            (15, 145), cv2.FONT_HERSHEY_SIMPLEX,
            0.55, color, 2
        )

    elif len(faces) > 1:
        message = "Only one person allowed"

    else:
        message = "No face detected"

    # Автоматаар зураг авах
    if capture_started is not None:
        now = time.time()

        if now < capture_started:
            countdown = int(capture_started - now) + 1

            cv2.putText(
                frame, str(countdown),
                (width // 2 - 25, height // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.5, (0, 255, 255), 4
            )

        elif now >= next_capture_time:
            if len(faces) == 1 and quality_ok:
                image_path = get_image_path()

                if cv2.imwrite(image_path, face_image):
                    stage_saved += 1
                    saved_total += 1

                    print(
                        f"{stages[stage_index]}: "
                        f"{stage_saved}/{photos_per_stage}"
                    )

                    message = f"Photo saved: {stage_saved}/3"
                    next_capture_time = now + 0.8
                else:
                    message = "Could not save photo"
                    next_capture_time = now + 0.8

            else:
                message = "Waiting for a clear single face"
                next_capture_time = now + 0.3

            if stage_saved >= photos_per_stage:
                print(f"{stages[stage_index]} дууслаа!")

                stage_index += 1
                stage_saved = 0
                capture_started = None

                if stage_index < len(stages):
                    message = "Press SPACE for next stage"
                    print(f"Дараагийн байрлал: {stages[stage_index]}")

    cv2.imshow("Face Registration", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord(" ") and capture_started is None:
        if len(faces) == 1 and quality_ok:
            capture_started = time.time() + 3
            next_capture_time = capture_started
            message = "Get ready!"
            print("3 секундын дараа зураг авч эхэлнэ!")
        else:
            print("Нэг тод нүүр камераар харуулна уу!")

    elif key == ord("n") and capture_started is None:
        print(f"{stages[stage_index]} алгаслаа!")
        stage_index += 1
        stage_saved = 0
        message = "Press SPACE for next stage"

    elif key == ord("q"):
        break

cap.release()
detector.close()
cv2.destroyAllWindows()

print(f"\n{name}: нийт {saved_total} шинэ зураг хадгаллаа!")
