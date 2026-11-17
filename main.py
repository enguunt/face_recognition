
import cv2
import mediapipe as mp
import time

mp_face = mp.solutions.face_detection

face_detector = mp_face.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.5
)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Камер нээгдсэнгүй!")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

previous_box = None
missing_frames = 0
max_missing_frames = 5

previous_time = time.time()
fps_smooth = 0

while True:

    ret, frame = cap.read()

    if not ret:
        print("Дүрс авч чадсангүй!")
        break
    height, width, _ = frame.shape
    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )
    results = face_detector.process(rgb_frame)
    current_box = None
    if results.detections:
        detection = max(
            results.detections,
            key=lambda d: d.score[0]
        )
        bbox = detection.location_data.relative_bounding_box
        x = int(bbox.xmin * width)
        y = int(bbox.ymin * height)
        w = int(bbox.width * width)
        h = int(bbox.height * height)
        x = max(0, x)
        y = max(0, y)
        w = min(w, width - x)
        h = min(h, height - y)
        current_box = (x, y, w, h)
        missing_frames = 0
    else:
        missing_frames += 1

    if current_box is not None:

        if previous_box is None:
            previous_box = current_box

        else:
            alpha = 0.65

            previous_box = tuple(
                int(alpha * new + (1 - alpha) * old)
                for new, old in zip(current_box, previous_box)
            )
    elif missing_frames > max_missing_frames:
        previous_box = None

    if previous_box is not None:

        x, y, w, h = previous_box

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )
        cv2.putText(
            frame,
            "Face Detected",
            (x, max(y - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
    current_time = time.time()

    fps = 1 / max(current_time - previous_time, 0.0001)

    fps_smooth = 0.8 * fps_smooth + 0.2 * fps
    previous_time = current_time

    cv2.putText(
        frame,
        f"FPS: {fps_smooth:.1f}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )
    cv2.imshow("MediaPipe Face Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
cap.release()
face_detector.close()
cv2.destroyAllWindows()

print("Camera closed.")
