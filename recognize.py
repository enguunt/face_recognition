
import os
import cv2
import time
import numpy as np
import mediapipe as mp

from deepface import DeepFace
from concurrent.futures import ThreadPoolExecutor

DATABASE = "dataset"
MODEL = "Facenet"
LIMIT = 0.36
INTERVAL = 0.7

# Зургийн векторуудыг санах
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


print("Бүртгэлтэй хүмүүсийн мэдээллийг ачаалж байна...")

# Зургуудыг зөвхөн эхлэх үед боловсруулна
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
                print("Зураг уншихад алдаа:", path, e)

        if vectors:
            known_faces[name] = np.stack(vectors)
            print(f"{name}: {len(vectors)} зураг")

print("Бүртгэлтэй хүмүүс:", list(known_faces.keys()))

# Нүүр таних функц
def recognize_face(face_image):
    try:
        vector = get_embedding(face_image)
    except Exception as e:
        print("Таних алдаа:", e)
        return "Unknown"

    if vector is None:
        return "Unknown"

    best_name = "Unknown"
    best_score = float("inf")

    for name, vectors in known_faces.items():
        # Cosine distance
        distances = 1 - (vectors @ vector)
        distances = np.sort(distances)

        count = min(3, len(distances))
        score = float(np.mean(distances[:count]))

        if score < LIMIT and score < best_score:
            best_score = score
            best_name = name

    return best_name


# Нэг зураг доторх бүх нүүрийг таних
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

cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

if not cap.isOpened():
    print("Камер нээгдсэнгүй!")
    detector.close()
    raise SystemExit

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Таних ажиллагааг тусдаа thread дээр хийнэ
executor = ThreadPoolExecutor(max_workers=1)
future = None

last_results = []
last_check = 0

def box_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def find_name(box, results):
    cx, cy = box_center(box)

    best_distance = float("inf")
    best_name = "Searching..."

    for old_box, name in results:
        ox, oy = box_center(old_box)

        distance = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5

        if distance < best_distance:
            best_distance = distance
            best_name = name

    # Хуучин байрлалаас хэт хол бол нэрийг ашиглахгүй
    if best_distance > 80:
        return "Searching..."

    return best_name


print("\nКамер ажиллаж байна. Q = гарах")

try:
    while True:
        ret, frame = cap.read()

        if not ret:
            print("Камерын дүрс авч чадсангүй!")
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

        # Дууссан танилтын үр дүнг авах
        if future is not None and future.done():
            try:
                last_results = future.result()
            except Exception as e:
                print("Таних ажиллагааны алдаа:", e)
                last_results = []

            future = None

        now = time.time()

        # Өмнөх танилт дууссан үед дараагийнхыг эхлүүлэх
        if (
            faces
            and future is None
            and now - last_check >= INTERVAL
        ):
            face_items = []

            for box in faces:
                x1, y1, x2, y2 = box

                padding = int((x2 - x1) * 0.15)

                left = max(0, x1 - padding)
                top = max(0, y1 - padding)
                right = min(width, x2 + padding)
                bottom = min(height, y2 + padding)

                crop = frame[top:bottom, left:right].copy()

                if crop.size > 0:
                    face_items.append((box, crop))

            if face_items:
                future = executor.submit(recognize_all, face_items)
                last_check = now

        # Хүн бүрт тусдаа дөрвөлжин, нэр
        for box in faces:
            x1, y1, x2, y2 = box

            name = find_name(box, last_results)

            if name not in ("Unknown", "Searching..."):
                color = (0, 255, 0)
            else:
                color = (0, 0, 255)

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
