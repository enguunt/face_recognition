import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from facevision_light_minimal import App


class GuiLogicTests(unittest.TestCase):
    def test_registration_completion_refreshes_and_returns_to_recognition(self):
        app = SimpleNamespace(stage=3, count=3, total=12, person='Test', mode='register',
                              capture_time=1, student_store=Mock(), attendance=Mock(),
                              manager_window=None, session=4, tracker=Mock(), known={'old':'vectors'},
                              status=Mock(), background=Mock(return_value=True),
                              load_people=Mock(), refresh_student_lists=Mock())
        app.student_store.names.return_value=['Test']
        App.next_stage(app)
        self.assertEqual(app.stage,4)
        self.assertEqual(app.mode,'recognize')
        self.assertEqual(app.known,{})
        self.assertEqual(app.session,5)
        app.attendance.roster.assert_called_once_with(['Test'])
        app.background.assert_called_once_with('load',app.load_people)

    def test_registration_with_no_photos_does_not_load(self):
        app = SimpleNamespace(stage=3, count=0, total=0, person='None', mode='register',
                              capture_time=None, student_store=Mock(), attendance=Mock(),
                              manager_window=None, status=Mock(), background=Mock())
        App.next_stage(app)
        self.assertEqual(app.mode, 'detect')
        app.background.assert_not_called()

if __name__=='__main__':
    unittest.main()
