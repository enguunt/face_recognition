import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from openpyxl import load_workbook

from attendance_excel import AttendanceRecorder
from student_manager import StudentStore


class AttendanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dataset = self.root / 'dataset'
        self.dataset.mkdir()
        self.record = AttendanceRecorder(self.dataset)
        self.addCleanup(self.record.close)

    def wait(self):
        self.record._tasks.join()

    def test_roster_present_repeat_rename_remove_finish(self):
        for name in ('Bat', 'Saraa'):
            (self.dataset / name).mkdir()
        store = StudentStore(self.dataset)
        self.record.roster(store.names())
        self.record.present('Bat', store.names())
        self.record.present('Bat', store.names())
        self.wait()
        payload = json.loads(self.record.json_path.read_text(encoding='utf-8'))
        day_key = next(iter(payload['days']))
        first_time = payload['days'][day_key]['present']['Bat']
        self.assertEqual(len(payload['days'][day_key]['present']), 1)
        self.assertEqual(load_workbook(self.record.excel_path)[day_key]['B6'].value, 'Bat')
        store.rename('Bat','Bataa')
        self.record.rename_student('Bat','Bataa',store.names())
        self.wait()
        payload = json.loads(self.record.json_path.read_text(encoding='utf-8'))
        self.assertEqual(payload['days'][day_key]['present']['Bataa'], first_time)
        self.assertNotIn('Bat',payload['days'][day_key]['students'])
        self.assertEqual(load_workbook(self.record.excel_path)[day_key]['B6'].value, 'Bataa')
        old_dir = store.remove('Saraa')
        self.assertTrue(old_dir.is_dir())
        self.record.roster(store.names())
        self.wait()
        self.assertEqual(load_workbook(self.record.excel_path)[day_key]['B7'].value, None)
        key = store.removed()[0][0]
        store.restore(key)
        self.record.roster(store.names())
        self.record.finish_day(store.names())
        self.wait()
        ws = load_workbook(self.record.excel_path)[day_key]
        self.assertEqual(ws['C7'].value,'Ирээгүй')

    def test_lateness_boundary(self):
        self.assertFalse(AttendanceRecorder._is_late('09:15:00'))
        self.assertTrue(AttendanceRecorder._is_late('09:15:01'))
        self.assertFalse(AttendanceRecorder._is_late('08:00:00'))

    def test_excel_windows_lock_recovery(self):
        original = self.record._save_excel
        locked = {'active':True}
        def occasionally_locked(data, destination=None):
            if destination is None and locked['active']:
                raise PermissionError(13, 'Excel locked')
            return original(data,destination)
        with patch.object(self.record,'_save_excel',side_effect=occasionally_locked):
            self.record.roster(['TestStudent'])
            self.record.present('TestStudent',['TestStudent'])
            self.wait()
            self.assertTrue(self.record.json_path.is_file())
            self.assertFalse(self.record.excel_path.is_file())
            self.assertTrue((self.root/'attendance_pending.xlsx').is_file())
            locked['active']=False
            self.record.resync()
            self.wait()
            self.assertTrue(self.record.excel_path.is_file())
            self.assertEqual(self.record._excel_pending, False)
            key=next(iter(json.loads(self.record.json_path.read_text(encoding='utf-8'))['days']))
            self.assertEqual(load_workbook(self.record.excel_path)[key]['B6'].value,'TestStudent')

    def test_retry_without_manual_resync(self):
        original = self.record._save_excel
        locked = {'active': True}
        def temporary_lock(data, destination=None):
            if destination is None and locked['active']:
                raise PermissionError(13, 'Excel locked')
            return original(data, destination)
        with patch.object(self.record, '_save_excel', side_effect=temporary_lock):
            self.record.roster(['RetryStudent'])
            self.wait()
            self.assertTrue(self.record._excel_pending)
            locked['active'] = False
            deadline = time.monotonic() + 6
            while not self.record.excel_path.exists() and time.monotonic() < deadline:
                time.sleep(.1)
            self.assertTrue(self.record.excel_path.exists())

    def test_both_workbooks_locked_creates_distinct_snapshot(self):
        original = self.record._save_excel
        def two_locks(data, destination=None):
            target = Path(destination) if destination else self.record.excel_path
            if target.name in ('attendance.xlsx', 'attendance_pending.xlsx'):
                raise PermissionError(13, 'Excel locked')
            return original(data, destination)
        with patch.object(self.record, '_save_excel', side_effect=two_locks):
            self.record.roster(['Locked'])
            self.wait()
            snapshots = list(self.root.glob('attendance_pending_*.xlsx'))
            self.assertEqual(len(snapshots), 1)
            self.assertTrue(self.record.json_path.is_file())

    def test_no_excel_formula_injection(self):
        self.record.roster(['=2+2'])
        self.wait()
        day = next(iter(load_workbook(self.record.excel_path).sheetnames))
        cell = load_workbook(self.record.excel_path)[day]['B6']
        self.assertEqual(cell.value, '=2+2')
        self.assertEqual(cell.data_type, 's')

if __name__=='__main__':
    unittest.main()
