"""Camera and detection worker with one latest-frame slot, not a frame backlog."""
from dataclasses import dataclass
import threading
import time

import cv2


@dataclass(frozen=True)
class CameraFrame:
    sequence: int
    captured_at: float
    image: object
    boxes: tuple
    read_ms: float
    detect_ms: float


class CameraStream:
    def __init__(self, capture_factory=None, detector_factory=None):
        self._capture_factory = capture_factory or self._open_capture
        self._detector_factory = detector_factory or self._open_detector
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        self._latest = None
        self._error = None

    @staticmethod
    def _open_capture():
        capture = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return capture

    @staticmethod
    def _open_detector():
        import mediapipe as mp
        return mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.6)

    @property
    def alive(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def error(self):
        with self._lock:
            return self._error

    def start(self):
        if self._thread is not None:
            raise RuntimeError('CameraStream instances can only be started once')
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name='facevision-camera')
        self._thread.start()

    def stop(self):
        # The worker owns/release its devices; Tk must never wait for cap.read().
        self._stop.set()

    def latest(self, after_sequence):
        with self._lock:
            packet = self._latest
        return packet if packet is not None and packet.sequence > after_sequence else None

    def _run(self):
        capture = detector = None
        try:
            capture = self._capture_factory()
            if not capture.isOpened():
                raise RuntimeError('Camera neegdsengui. Mac Camera permission shalgana uu.')
            if self._stop.is_set():
                return
            detector = self._detector_factory()
            sequence = 0
            while not self._stop.is_set():
                started = time.monotonic()
                ok, frame = capture.read()
                captured_at = time.monotonic()
                if self._stop.is_set():
                    break
                if not ok:
                    raise RuntimeError('Camera-iin durs avch chadsangui.')
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                result = detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                boxes = []
                for detection in result.detections or []:
                    b = detection.location_data.relative_bounding_box
                    box = (max(0, int(b.xmin*w)), max(0, int(b.ymin*h)),
                           min(w, int((b.xmin+b.width)*w)),
                           min(h, int((b.ymin+b.height)*h)))
                    if box[2] > box[0] and box[3] > box[1]:
                        boxes.append(box)
                sequence += 1
                packet = CameraFrame(sequence, captured_at, frame, tuple(boxes),
                                     (captured_at-started)*1000,
                                     (time.monotonic()-captured_at)*1000)
                with self._lock:
                    self._latest = packet
        except Exception as error:
            with self._lock:
                self._error = str(error)
        finally:
            if capture is not None:
                capture.release()
            if detector is not None:
                detector.close()
