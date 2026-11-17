import csv
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app_data import AttendanceStore, EnrollmentStore, TIMEZONE
from facevision_light_minimal import App
from recognition_policy import MultiFaceTracker


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = AttendanceStore(self.root / 'attendance.sqlite3')
        self.enrollments = EnrollmentStore(self.root / 'dataset')

    def enroll(self, name='Carlo'):
        folder=self.enrollments.dataset/name
        folder.mkdir(parents=True)
        (folder/'photo.jpg').write_bytes(b'test photo placeholder')
        return folder

    def test_first_arrival_survives_restart_and_next_day_gets_new_row(self):
        start=datetime(2026,11,17,9,12,tzinfo=TIMEZONE)
        self.assertTrue(self.store.record('Carlo',start))
        reopened=AttendanceStore(self.store.path)
        self.assertFalse(reopened.record('Carlo',start.replace(hour=10)))
        self.assertTrue(reopened.record('Carlo',start.replace(day=18)))
        rows=reopened.rows(today=False)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1][2],start.isoformat(timespec='seconds'))

    def test_timezone_day_is_ulanbaatar_not_utc(self):
        now=datetime(2026,11,17,18,tzinfo=timezone.utc)
        self.store.record('Carlo',now)
        self.assertEqual(self.store.rows(False)[0][1],'2026-11-18')
        with self.assertRaises(ValueError): self.store.record('Other',datetime(2026,11,17))

    def test_csv_has_arrival_time_and_status(self):
        self.store.record('Carlo',datetime(2026,11,17,9,12,34,tzinfo=TIMEZONE))
        path=self.root/'out.csv'; self.store.export(path,self.store.rows(False))
        with path.open(encoding='utf-8-sig',newline='') as file: rows=list(csv.reader(file))
        self.assertEqual(rows[1],['Carlo','2026-11-17','09:12:34','Present'])

    def test_remove_and_restore_preserve_photos_and_history(self):
        folder=self.enroll()
        self.store.record('Carlo')
        token=self.enrollments.remove('Carlo')
        self.assertFalse(folder.exists())
        self.assertEqual(self.enrollments.people(),[])
        self.assertEqual(self.enrollments.removed(),[(token,'Carlo')])
        self.assertEqual(len(self.store.rows(False)),1)
        self.assertEqual(self.enrollments.restore(token),'Carlo')
        self.assertEqual((folder/'photo.jpg').read_bytes(),b'test photo placeholder')
        self.assertEqual(self.enrollments.removed(),[])

    def test_restore_never_overwrites_new_registration(self):
        self.enroll(); token=self.enrollments.remove('Carlo'); self.enroll()
        with self.assertRaises(FileExistsError): self.enrollments.restore(token)
        self.assertTrue(self.enrollments.removed())

    def test_invalid_paths_cannot_remove_other_folders(self):
        for name in ('..','../outside','a/b','a\\b',''):
            with self.assertRaises(ValueError): self.enrollments.remove(name)
        outside=self.root/'outside';outside.mkdir()
        self.enrollments.dataset.mkdir()
        (self.enrollments.dataset/'linked').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError): self.enrollments.remove('linked')

    def test_invalidation_drops_cached_vectors_and_old_session(self):
        app=App.__new__(App); app.session=3; app.known={'Carlo':object()}
        app.tracker=MultiFaceTracker();app.tracker.update([(0,0,100,100)],0)
        app.invalidate_people()
        self.assertEqual(app.session,4);self.assertEqual(app.known,{})
        self.assertEqual(app.tracker.tracks,{})
        self.assertEqual(app.mode,'detect');self.assertIsNone(app.capture_time)

    def test_only_visible_confirmed_person_creates_attendance(self):
        app=App.__new__(App);app.tracker=MultiFaceTracker()
        person=app.tracker.update([(0,0,100,100)],0)[0]
        app.attendance=self.store;app.attendance_seen=set();app.status=Mock()
        app.record_attendance();self.assertEqual(self.store.rows(False),[])
        person.confirmed='Carlo'
        app.record_attendance();app.record_attendance()
        self.assertEqual(len(self.store.rows(False)),1)
        person.confirmed='Other';person.visible=False
        app.record_attendance();self.assertEqual(len(self.store.rows(False)),1)

    def test_write_failure_can_retry(self):
        app=App.__new__(App);app.tracker=MultiFaceTracker()
        person=app.tracker.update([(0,0,100,100)],0)[0];person.confirmed='Carlo'
        app.attendance=Mock();app.attendance.record.side_effect=OSError('disk full')
        app.attendance_seen=set();app.status=Mock()
        app.record_attendance()
        self.assertEqual(app.attendance_seen,set())
        app.status.set.assert_called_once()

    def test_people_dialog_remove_and_restore_callbacks_use_store(self):
        self.enroll()
        app=App.__new__(App); app.root=Mock(); app.enrollments=self.enrollments
        app.session=0;app.tracker=MultiFaceTracker();app.known={'Carlo':object()};app.status=Mock()
        active,removed=Mock(),Mock()
        active.get_children.return_value=();removed.get_children.return_value=()
        active.selection.return_value=('row',);active.item.return_value=('Carlo',1)
        commands={}
        def button(*args,**kwargs):
            commands[kwargs['text']]=kwargs['command']
            return Mock()
        with patch('facevision_light_minimal.tk.Toplevel'), patch('facevision_light_minimal.tk.Label'), \
             patch('facevision_light_minimal.ttk.Notebook'), patch('facevision_light_minimal.ttk.Frame'), \
             patch('facevision_light_minimal.ttk.Treeview',side_effect=[active,removed]), \
             patch('facevision_light_minimal.ttk.Button',side_effect=button), \
             patch('facevision_light_minimal.messagebox.askyesno',return_value=True), \
             patch('facevision_light_minimal.messagebox.showerror') as error:
            app.show_people()
            commands['Сонгосон хүнийг устгах']()
            self.assertEqual(self.enrollments.people(),[])
            self.assertEqual(app.known,{})
            token=self.enrollments.removed()[0][0]
            removed.selection.return_value=(token,)
            commands['Сэргээх']()
            self.assertEqual(self.enrollments.people(),[('Carlo',1)])
            error.assert_not_called()

    def test_attendance_dialog_loads_and_exports_without_real_widgets(self):
        self.store.record('Carlo')
        app=App.__new__(App);app.root=Mock();app.attendance=self.store
        table=Mock();table.get_children.return_value=()
        commands={}
        def button(*args,**kwargs):
            commands[kwargs['text']]=kwargs['command']
            return Mock()
        path=self.root/'dialog.csv'
        with patch('facevision_light_minimal.tk.Toplevel'), \
             patch('facevision_light_minimal.tk.BooleanVar') as today, \
             patch('facevision_light_minimal.ttk.Frame'), \
             patch('facevision_light_minimal.ttk.Treeview',return_value=table), \
             patch('facevision_light_minimal.ttk.Scrollbar'), \
             patch('facevision_light_minimal.ttk.Checkbutton'), \
             patch('facevision_light_minimal.ttk.Button',side_effect=button), \
             patch('facevision_light_minimal.filedialog.asksaveasfilename',return_value=str(path)), \
             patch('facevision_light_minimal.messagebox.showerror') as error:
            today.return_value.get.return_value=True
            app.show_attendance()
            table.insert.assert_called_once()
            commands['CSV хадгалах']()
            self.assertIn('Carlo',path.read_text(encoding='utf-8-sig'))
            error.assert_not_called()


if __name__=='__main__': unittest.main()
