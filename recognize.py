
import os
import cv2
import time
import numpy as np
import mediapipe as mp

from deepface import DeepFace
from concurrent.futures import ThreadPoolExecutor
from recognition_policy import match_identity, MultiFaceTracker
from facevision_config import DATASET

DATABASE = str(DATASET)
MODEL = "Facenet"
LIMIT = 0.36  # Starting point; calibrate with genuine and unknown people.
INTERVAL = 0.15

# Zurgiin vektoruudiig sanah
known_faces = {}

def get_embedding(image):
    result = DeepFace.represent(
        img_path=image,
        model_name=MODEL,
        detector_backend="skip",
        enforce_detection=False,
        align=False
    )

    vector = np.array(result[0]["embedding"], dtype=np.float32)
    length = np.linalg.norm(vector)

    if length == 0:
        return None

    return vector / length


print("burtgeltei humuusiin medeelliig achaalj bn...")

# zurguudiig zovhn ehleh uyd bolovsruulns
if os.path.isdir(DATABASE):
    for name in os.listdir(DATABASE):
        folder = os.path.join(DATABASE, name)

        if not os.path.isdir(folder):
            continue

        vectors = []

        for filename in sorted(os.listdir(folder)):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            path = os.path.join(folder, filename)

            try:
                vector = get_embedding(path)

                if vector is not None:
                    vectors.append(vector)

            except Exception as e:
                print("Zurag unshihad aldaa:", path, e)

        if vectors:
            known_faces[name] = np.stack(vectors)
            print(f"{name}: {len(vectors)} зураг")

print("burtgeltei humuus:", list(known_faces.keys()))

# Nuur tanih punkts
def recognize_face(face_image):
    if min(face_image.shape[:2]) < 90:
        return "Unknown"
    gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
    if cv2.Laplacian(gray, cv2.CV_64F).var() < 35:
        return "Unknown"
    try:
        vector = get_embedding(face_image)
    except Exception as e:
        print("tanih aldaa:", e)
        return "Unknown"

    if vector is None:
        return "Unknown"

    return match_identity(vector, known_faces, threshold=LIMIT)


# Neg zurag dotorh buh huniig tanih
def recognize_all(face_items):
    answers = []

    for box, face_image in face_items:
        name = recognize_face(face_image)
        answers.append((box, name))

    return answers


detector = mp.solutions.face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.6
)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("camera neegdh!")
    detector.close()
    raise SystemExit

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# tanih ajilggaag tusdaa thread deer hiine
executor = ThreadPoolExecutor(max_workers=1)
future = None

last_check = 0
tracker = MultiFaceTracker()
submitted_at = 0


print("\ncamera ajilllaj bn. Q = garah")

try:
    while True:
        ret, frame = cap.read()

        if not ret:
            print("camera ii ndurs avj chadsngui!")
            break

        # MIRROR КАМЕР
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

        now = time.monotonic()
        visible = tracker.update(faces, now)
        if future is not None and future.done():
            try:
                for name in tracker.apply(future.result(), submitted_at, now):
                    print(f"Ene hun bol {name} yum baina. Q = garah")
            except Exception as e:
                print("tanih ajilgaany aldaa:", e)
            future = None

        if visible and future is None and now - last_check >= INTERVAL:
            face_items = []

            for person in visible:
                if not person.needs_recognition(now):
                    continue
                box = person.box
                x1, y1, x2, y2 = box

                padding = int((x2 - x1) * 0.15)

                left = max(0, x1 - padding)
                top = max(0, y1 - padding)
                right = min(width, x2 + padding)
                bottom = min(height, y2 + padding)

                crop = frame[top:bottom, left:right].copy()

                if crop.size > 0:
                    face_items.append((person.id, crop))

            if face_items:
                future = executor.submit(recognize_all, face_items)
                last_check = now
                submitted_at = now

        for person in visible:
            x1, y1, x2, y2 = person.display_box
            name, color = person.label()

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            cv2.putText(
                frame,
                name,
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

        cv2.putText(
            frame,
            f"Faces: {len(faces)}",
            (15, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.imshow("Face Recognition System", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    detector.close()
    cv2.destroyAllWindows()
    executor.shutdown(wait=True)

print("Camera closed.")
