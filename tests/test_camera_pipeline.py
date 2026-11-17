import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from camera_stream import CameraStream, CameraFrame
from facevision_light_minimal import App
from frame_metrics import FrameMetrics
from recognition_policy import MultiFaceTracker


class Capture:
    def __init__(self):
        self.release_called = threading.Event()
        self.entered = threading.Event()
        self.proceed = threading.Event()
        self.thread_id = None

    def isOpened(self): return True

    def read(self):
        self.thread_id = threading.get_ident()
        self.entered.set()
        self.proceed.wait(2)
        return True, np.zeros((20, 30, 3), dtype=np.uint8)

    def release(self): self.release_called.set()


class Detector:
    def __init__(self): self.closed = False
    def process(self, frame): return SimpleNamespace(detections=[])
    def close(self): self.closed = True


class PipelineTests(unittest.TestCase):
    def test_camera_read_is_off_main_thread_and_stop_does_not_wait(self):
        capture, detector = Capture(), Detector()
        stream = CameraStream(lambda: capture, lambda: detector)
        stream.start()
        try:
            self.assertTrue(capture.entered.wait(2))
            self.assertNotEqual(capture.thread_id, threading.get_ident())
            stream.stop()
            # read() is still waiting, but stop() has already returned.
            self.assertFalse(capture.release_called.is_set())
        finally:
            stream.stop(); capture.proceed.set()
            stream._thread.join(2)
        self.assertFalse(stream.alive)
        self.assertTrue(capture.release_called.is_set())
        self.assertTrue(detector.closed)

    def test_latest_slot_skips_old_frames_without_replaying_them(self):
        stream = CameraStream()
        for number in range(1, 1001):
            stream._latest = CameraFrame(number, 0, None, (), 0, 0)
        self.assertEqual(stream.latest(0).sequence, 1000)
        self.assertIsNone(stream.latest(1000))

    def test_camera_failure_releases_capture_and_exposes_error(self):
        capture = Capture()
        capture.isOpened = lambda: False
        stream = CameraStream(lambda: capture, Detector)
        stream.start(); stream._thread.join(2)
        self.assertTrue(capture.release_called.is_set())
        self.assertIsNotNone(stream.error)
        self.assertFalse(stream.alive)

    def test_detection_failure_closes_both_resources(self):
        capture, detector = Capture(), Detector()
        capture.proceed.set()
        detector.process = Mock(side_effect=ValueError('detection failed'))
        stream = CameraStream(lambda: capture, lambda: detector)
        stream.start(); stream._thread.join(2)
        self.assertEqual(stream.error, 'detection failed')
        self.assertTrue(capture.release_called.is_set())
        self.assertTrue(detector.closed)

    def test_ui_waiting_for_frame_only_schedules_another_tick(self):
        app = App.__new__(App)
        app.running=True; app.update_job='old'; app.last_sequence=0
        app.stream=SimpleNamespace(error=None, latest=Mock(return_value=None))
        app.root=Mock()
        app.update()
        app.root.after.assert_called_once_with(8, app.update)
        app.schedule_update(8)
        self.assertEqual(app.root.after.call_count, 1)

    def test_ui_renders_each_sequence_once_and_reports_fps(self):
        app=App.__new__(App)
        frame=np.zeros((100,100,3),dtype=np.uint8)
        packet=CameraFrame(1,time.monotonic(),frame,(),4,5)
        app.stream=Mock(error=None)
        app.stream.latest.side_effect=[packet,None]
        app.root=Mock(); app.screen=Mock()
        app.screen.winfo_width.return_value=400
        app.screen.winfo_height.return_value=300
        app.running=True; app.update_job=None; app.last_sequence=0
        app.status=Mock(); app.fps_text=Mock(); app.metrics=FrameMetrics()
        app.tracker=MultiFaceTracker(); app.mode='detect'
        app.last_metrics_update=0; app.profile=False
        with patch('facevision_light_minimal.ImageTk.PhotoImage') as photo:
            app.update(); app.update()
        self.assertEqual(photo.call_count,1)
        self.assertEqual(app.last_sequence,1)
        self.assertEqual(app.frame_time,packet.captured_at)
        self.assertEqual(len(app.metrics.presented),1)
        self.assertTrue(np.array_equal(frame,np.zeros_like(frame)))

    def test_display_fps_uses_elapsed_time_and_bounded_history(self):
        metrics=FrameMetrics()
        for n in range(1000):
            metrics.present(n/30)
            metrics.record('detect',5)
        self.assertAlmostEqual(metrics.fps,30)
        self.assertEqual(len(metrics.presented),60)
        self.assertEqual(len(metrics.timings['detect']),60)

    def test_recognition_timestamps_are_from_camera_not_queue_submission(self):
        app=App.__new__(App)
        app.busy=False; app.session=1; app.frame_time=12.5
        import queue
        app.q=queue.Queue()
        self.assertTrue(app.background('recognize',lambda: []))
        result=app.q.get(timeout=2)
        self.assertEqual(result[4],12.5)
        self.assertEqual(result[0],'recognize')
        self.assertEqual(len(result),6)


if __name__ == '__main__': unittest.main()
