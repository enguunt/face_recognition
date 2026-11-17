import queue
import unittest
from unittest.mock import patch
import numpy as np
from recognition_policy import Confirmation, MultiFaceTracker, match_identity
from facevision_light_minimal import App
from frame_metrics import FrameMetrics

CARLO = (0, 0, 100, 100)
OTHER = (200, 0, 300, 100)


class Value:
    def set(self, value): self.value = value


class Root:
    def after(self, *args): pass


class RecognitionTests(unittest.TestCase):
    def confirm(self, tracker):
        person = tracker.update([CARLO], 0)[0]
        for t in (0, .15):
            tracker.update([CARLO], t)
            self.assertEqual(tracker.apply([(person.id, 'Carlo')], t, t), [])
            self.assertEqual(person.label()[0], 'Searching...')
        tracker.update([CARLO], .3)
        self.assertEqual(tracker.apply([(person.id, 'Carlo')], .3, .3), ['Carlo'])
        self.assertEqual(person.label(), ('Carlo', (0,255,0)))
        return person

    def test_fast_confirmation_and_independent_second_person(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        # Detection ordering may change when a second person enters.
        other, same = tracker.update([OTHER, CARLO], 3.1)
        self.assertIs(same, carlo)
        self.assertEqual(carlo.confirmed, 'Carlo')
        self.assertEqual(other.label()[0], 'Searching...')
        tracker.apply([(other.id,'Unknown'), (carlo.id,'Carlo')], 3.1, 3.1)
        self.assertEqual(carlo.label()[0], 'Carlo')
        self.assertEqual(other.label()[0], 'Unknown')
        tracker.update([CARLO], 3.2)
        self.assertEqual(carlo.confirmed, 'Carlo')

    def test_duplicate_name_cannot_attach_to_second_face(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        _, other = tracker.update([CARLO, OTHER], 3.1)
        tracker.apply([(carlo.id,'Carlo'), (other.id,'Carlo')], 3.1, 3.1)
        self.assertEqual(carlo.confirmed, 'Carlo')
        self.assertEqual(other.name, 'Unknown')

    def test_lost_face_cannot_inherit_late_results(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        tracker.update([], 3.1)
        replacement = tracker.update([CARLO], 3.2)[0]
        tracker.apply([(carlo.id,'Carlo')], 3, 3.2)
        self.assertIsNone(replacement.confirmed)
        self.assertEqual(replacement.label()[0], 'Searching...')

    def test_confirmed_name_survives_two_temporary_mismatches(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        tracker.apply([(carlo.id,'Unknown')], 3.1, 3.1)
        self.assertEqual(carlo.confirmed, 'Carlo')
        tracker.apply([(carlo.id,'Other')], 3.2, 3.2)
        tracker.update([CARLO], 6)
        self.assertEqual(carlo.label()[0], 'Carlo')

    def test_duplicate_observations_do_not_advance_confirmation(self):
        c = Confirmation()
        for _ in range(20): self.assertIsNone(c.observe('Carlo',0))
        self.assertEqual(c.samples, 1)
        self.assertIsNone(c.observe('Carlo',4))
        self.assertEqual(c.samples,1)

    def test_ambiguous_crossing_does_not_transfer_names(self):
        tracker = MultiFaceTracker()
        self.confirm(tracker)
        tracks = tracker.update([CARLO,(10,0,110,100)],3.1)
        self.assertTrue(all(t.confirmed is None for t in tracks))

    def test_match_rejects_unknown_and_ambiguous_identity(self):
        v = np.array([1.,0.]); refs = np.array([v,v,v])
        self.assertEqual(match_identity(v, {'Carlo':refs}), 'Carlo')
        self.assertEqual(match_identity(-v, {'Carlo':refs}), 'Unknown')
        self.assertEqual(match_identity(v, {'Carlo':refs,'Other':refs}), 'Unknown')

    def test_app_retains_camera_and_existing_person(self):
        app = App.__new__(App)
        app.q=queue.Queue(); app.root=Root(); app.status=Value(); app.metrics=FrameMetrics()
        app.mode='recognize'; app.running=True; app.session=1
        app.tracker=MultiFaceTracker()
        app.close_camera=lambda: self.fail('Camera must stay open')
        carlo=self.confirm(app.tracker)
        _, other=app.tracker.update([CARLO,OTHER],3.1)
        app.q.put(('recognize',[(carlo.id,'Carlo'),(other.id,'Unknown')],None,1,3.1,10.0))
        with patch('facevision_light_minimal.time.monotonic',return_value=3.2): app.poll()
        self.assertTrue(app.running)
        self.assertEqual(app.mode,'recognize')
        self.assertEqual(carlo.confirmed,'Carlo')
        self.assertEqual(other.name,'Unknown')

    def test_brief_detection_gap_keeps_name_but_draws_no_ghost(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        self.assertEqual(tracker.update([], .35), [])
        self.assertFalse(carlo.visible)
        self.assertFalse(carlo.needs_recognition(.35))
        returned = tracker.update([CARLO], .5)[0]
        self.assertIs(returned, carlo)
        self.assertEqual(returned.label()[0], 'Carlo')

    def test_long_detection_gap_requires_new_confirmation(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        tracker.update([], .35)
        replacement = tracker.update([CARLO], .7)[0]
        self.assertNotEqual(replacement.id, carlo.id)
        self.assertIsNone(replacement.confirmed)

    def test_periodic_recheck_and_three_consecutive_mismatches(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        self.assertFalse(carlo.needs_recognition(1))
        self.assertTrue(carlo.needs_recognition(1.8))
        for t in (1.8, 3.3):
            tracker.update([CARLO], t)
            tracker.apply([(carlo.id, 'Unknown')], t, t)
            self.assertEqual(carlo.confirmed, 'Carlo')
        tracker.update([CARLO], 4.8)
        tracker.apply([(carlo.id, 'Unknown')], 4.8, 4.8)
        self.assertIsNone(carlo.confirmed)
        self.assertEqual(carlo.label()[0], 'Unknown')
        self.assertTrue(carlo.needs_recognition(4.9))

    def test_successful_recheck_clears_mismatch_streak(self):
        tracker = MultiFaceTracker()
        carlo = self.confirm(tracker)
        for t,name in ((1.8,'Unknown'),(3.3,'Carlo'),(4.8,'Unknown'),(6.3,'Unknown')):
            tracker.update([CARLO], t)
            tracker.apply([(carlo.id,name)], t, t)
        self.assertEqual(carlo.confirmed, 'Carlo')
        self.assertEqual(carlo.mismatches, 2)

    def test_recheck_can_correct_initial_wrong_identity(self):
        tracker = MultiFaceTracker()
        person = self.confirm(tracker)
        for t in (1.8,3.3,4.8):
            tracker.update([CARLO],t)
            tracker.apply([(person.id,'Other')],t,t)
        self.assertIsNone(person.confirmed)
        for t in (5,5.4):
            tracker.update([CARLO],t)
            tracker.apply([(person.id,'Other')],t,t)
        self.assertEqual(person.confirmed,'Other')

    def test_hidden_track_ignores_inflight_results(self):
        tracker = MultiFaceTracker()
        person = tracker.update([CARLO],0)[0]
        tracker.update([],.1)
        tracker.apply([(person.id,'Carlo')],0,.1)
        self.assertIsNone(person.result_time)

    def test_legacy_entry_point_opens_the_same_minimal_app(self):
        import facevision
        self.assertIs(facevision.App, App)

    def test_all_entry_points_use_shared_dataset(self):
        import ast
        from pathlib import Path
        import facevision_config
        import facevision_light_minimal
        self.assertEqual(facevision_light_minimal.DATASET, facevision_config.DATASET)
        # Parse CLI files without importing them: imports would open a camera.
        root = Path(__file__).resolve().parents[1]
        for name in ('register.py','recognize.py'):
            tree = ast.parse((root/name).read_text())
            self.assertTrue(any(isinstance(n,ast.ImportFrom) and
                                n.module == 'facevision_config' and
                                any(a.name == 'DATASET' for a in n.names)
                                for n in tree.body))


if __name__ == '__main__': unittest.main()
