"""FACEVISION attendance: local JSON is the durable record; Excel is the colored view.

No SQL/database server is needed. Records are stored outside the project at
Documents/FACEVISION, beside the shared dataset folder. The Excel workbook is
updated in a worker thread so that saving it cannot block the camera UI.
"""

import errno
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, time as clock_time
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


BLUE = '164E9E'
NAVY = '132B4F'
GREEN_BG = 'DCFCE7'
GREEN_TEXT = '166534'
YELLOW_BG = 'FEF3C7'
YELLOW_TEXT = '92400E'
PENDING_BG = 'E2E8F0'
PENDING_TEXT = '475569'
LATE_AFTER = clock_time(9, 15, 0)  # 09:15:00 is on time; 09:15:01 is late.
RED_BG = 'FEE2E2'
RED_TEXT = '991B1B'
WHITE = 'FFFFFF'


class AttendanceRecorder:
    """Thread-safe FIFO: record a student's first confirmed recognition per day."""

    def __init__(self, dataset_path):
        self.folder = Path(dataset_path).parent
        self.excel_path = self.folder / 'attendance.xlsx'
        self.json_path = self.folder / 'attendance_data.json'
        self._tasks = queue.Queue()
        self.messages = queue.Queue()
        self._closed = False
        self._excel_pending = False
        self._lock_notified = False
        self._thread = threading.Thread(target=self._run, name='facevision-attendance', daemon=True)
        self._thread.start()

    def roster(self, names):
        self._tasks.put(('roster', tuple(names), datetime.now().isoformat(timespec='seconds')))

    def present(self, name, names):
        if name and name not in ('Unknown', 'Searching...'):
            self._tasks.put(('present', (str(name), tuple(names)), datetime.now().isoformat(timespec='seconds')))

    def finish_day(self, names):
        self._tasks.put(('finish', tuple(names), datetime.now().isoformat(timespec='seconds')))

    def rename_student(self, old, new, names):
        self._tasks.put(('rename', (str(old), str(new), tuple(names)),
                         datetime.now().isoformat(timespec='seconds')))

    def resync(self):
        self._tasks.put(('resync', None, datetime.now().isoformat(timespec='seconds')))

    def close(self):
        if not self._closed:
            self._closed = True
            self._tasks.put((None, None, None))
            self._thread.join(timeout=4)

    def _load(self):
        if not self.json_path.exists():
            return {'days': {}}
        with self.json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get('days'), dict):
            raise ValueError('Ирцийн JSON файл буруу бүтэцтэй байна.')
        return data

    def _save_json(self, data):
        self.folder.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.folder,
                                         prefix='.attendance_', suffix='.json',
                                         delete=False) as f:
            temp = Path(f.name)
            try:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                temp.unlink(missing_ok=True)
                raise
        try:
            os.replace(temp, self.json_path)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _day(data, date_string):
        return data['days'].setdefault(date_string,
                {'students': [], 'present': {}, 'finished': False})

    @staticmethod
    def _sync_roster(day, names):
        """Current day uses current active folders. Older days are untouched."""
        normalized = sorted({str(n).strip() for n in names if str(n).strip()},
                            key=str.casefold)
        if day['students'] != normalized:
            day['students'] = normalized
            return True
        return False

    @staticmethod
    def _is_late(arrival):
        try:
            return clock_time.fromisoformat(str(arrival)) > LATE_AFTER
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_file_locked(error):
        return (isinstance(error, PermissionError)
                or getattr(error, 'winerror', None) in (5, 32)
                or getattr(error, 'errno', None) in (errno.EACCES, errno.EPERM))

    def _save_locked_copy(self, data):
        """Produce an accessible current snapshot if Windows holds attendance.xlsx open."""
        fallback = self.folder / 'attendance_pending.xlsx'
        try:
            self._save_excel(data, fallback)
            return fallback
        except OSError as error:
            if not self._is_file_locked(error):
                raise
        # Both workbooks may be open: never overwrite them; use a distinct snapshot.
        fallback = self.folder / f'attendance_pending_{datetime.now():%Y%m%d_%H%M%S_%f}.xlsx'
        self._save_excel(data, fallback)
        return fallback

    def _publish(self, data, updated):
        try:
            self._save_excel(data)
        except OSError as error:
            if not self._is_file_locked(error):
                raise
            self._excel_pending = True
            # Save a new readable Excel file without modifying the user's open workbook.
            if updated:
                try:
                    self._save_locked_copy(data)
                except OSError as fallback_error:
                    self.messages.put(('warning',
                        'Ирц JSON-д хадгалагдсан. Excel болон нөөц Excel бичихэд алдаа: '
                        + str(fallback_error)))
            if not self._lock_notified:
                self.messages.put(('warning',
                    'attendance.xlsx Excel-д нээлттэй эсвэл түгжээтэй байна. '
                    'Ирц JSON-д хадгалагдсан; attendance_pending.xlsx-д хуулбарлахыг оролдов. '
                    'Excel-ийг хаахад үндсэн файл автоматаар шинэчлэгдэнэ.'))
                self._lock_notified = True
            return False
        else:
            was_locked = self._excel_pending or self._lock_notified
            self._excel_pending = False
            self._lock_notified = False
            if was_locked:
                self.messages.put(('ok', 'Excel-ийн түгжээ арилж, attendance.xlsx автоматаар шинэчлэгдлээ.'))
            return True

    def _run(self):
        while True:
            try:
                action, payload, timestamp = self._tasks.get(timeout=4)
            except queue.Empty:
                if self._excel_pending:
                    try:
                        self._publish(self._load(), updated=False)
                    except Exception as e:
                        self.messages.put(('error', f'Excel дахин шинэчлэх алдаа: {e}'))
                continue
            if action is None:
                self._tasks.task_done()
                break
            try:
                data = self._load()
                day_key = timestamp[:10]
                changed = False
                info = None
                if action != 'resync':
                    was_present = day_key in data['days']
                    day = self._day(data, day_key)
                    changed = not was_present
                    if action == 'present':
                        name, names = payload
                    elif action == 'rename':
                        old_name, new_name, names = payload
                        if old_name in day['present']:
                            # Preserve the same arrival time under the new name today.
                            arrival = day['present'].pop(old_name)
                            day['present'].setdefault(new_name, arrival)
                            changed = True
                    else:
                        names = payload
                    changed = self._sync_roster(day, names) or changed
                    if action == 'present':
                        if name not in day['students']:
                            day['students'].append(name)
                            day['students'].sort(key=str.casefold)
                            changed = True
                        if name not in day['present']:
                            arrived = timestamp[11:19]
                            day['present'][name] = arrived
                            changed = True
                            status = 'Хоцорсон' if self._is_late(arrived) else 'Ирсэн'
                            info = f'{name} — {status} ({arrived}) · Ирц бүртгэгдлээ'
                        else:
                            # Repeated face recognition should still clear the GUI's
                            # "saving..." status; keep the original first arrival.
                            arrived = day['present'][name]
                            status = 'Хоцорсон' if self._is_late(arrived) else 'Ирсэн'
                            info = f'{name} — {status} ({arrived}) · Өмнө бүртгэгдсэн байна'
                    elif action == 'finish':
                        if not day['finished']:
                            day['finished'] = True
                            changed = True
                        info = 'Өдрийн ирц дууслаа. Ирээгүй сурагчид улаанаар тэмдэглэгдлээ.'
                    elif action == 'rename':
                        info = f'{old_name} → {new_name}: өнөөдрийн нэр шинэчлэгдлээ'

                if changed:
                    self._save_json(data)  # Durable data first; Excel is a derived view.
                needs_excel = (changed or self._excel_pending or not self.excel_path.exists()
                               or action in ('roster', 'finish', 'resync'))
                excel_saved = self._publish(data, updated=True) if needs_excel else True
                if action == 'resync' and excel_saved:
                    info = f'Excel ирц шинэчлэгдлээ: {self.excel_path}'
                if info and excel_saved:
                    self.messages.put(('ok', info))
            except Exception as e:
                self.messages.put(('error', f'Ирцийн алдаа: {e}'))
            finally:
                self._tasks.task_done()

    def _save_excel(self, data, destination=None):
        self.folder.mkdir(parents=True, exist_ok=True)
        book = Workbook()
        first = True
        for day_key, day in sorted(data['days'].items()):
            ws = book.active if first else book.create_sheet()
            ws.title = day_key
            first = False
            self._format_day(ws, day_key, day)
        if first:
            ws = book.active
            ws.title = 'Эхлэх'
            ws['A1'] = 'Нүүр таних горимд орсноор өдрийн ирц үүснэ.'

        # Atomic replacement: an open workbook on Windows may block replacement.
        target = Path(destination) if destination is not None else self.excel_path
        handle, temporary = tempfile.mkstemp(prefix='.attendance_', suffix='.xlsx', dir=self.folder)
        os.close(handle)
        temp = Path(temporary)
        try:
            book.save(temp)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)

    @staticmethod
    def _format_day(ws, day_key, day):
        ws.sheet_view.showGridLines = False
        ws.merge_cells('A1:E1')
        title = ws['A1']
        title.value = 'FACEVISION  |  СУРАГЧДЫН ӨДРИЙН ИРЦ'
        title.font = Font(name='Calibri', size=16, bold=True, color=WHITE)
        title.fill = PatternFill('solid', fgColor=NAVY)
        title.alignment = Alignment(vertical='center', horizontal='left', indent=1)
        ws.row_dimensions[1].height = 36
        ws['A2'] = 'Огноо:'
        ws['B2'] = day_key
        ws['D2'] = 'Төлөв:'
        ws['E2'] = 'Дууссан' if day.get('finished') else 'Бүртгэл явагдаж байна'
        for cell in ws[2]:
            cell.font = Font(bold=True, color=NAVY)
        ws.row_dimensions[2].height = 24
        students = sorted(day.get('students', []), key=str.casefold)
        present = day.get('present', {})
        on_time = sum(1 for n in students if n in present and not AttendanceRecorder._is_late(present[n]))
        late_count = sum(1 for n in students if n in present and AttendanceRecorder._is_late(present[n]))
        count = on_time + late_count
        ws['A3'] = 'Нийт:'
        ws['B3'] = len(students)
        ws['C3'] = f'Цагтаа: {on_time}'
        ws['D3'] = f'Хоцорсон: {late_count}'
        ws['E3'] = f'Ирээгүй/хүлээгдэж буй: {len(students)-count}'
        for cell in ws[3]:
            cell.font = Font(bold=True, color=NAVY)
        ws.row_dimensions[3].height = 26
        ws.merge_cells('A4:E4')
        ws['A4'] = 'НОГООН: Цагтаа    |    ШАР: 09:15-аас хойш хоцорсон    |    СААРАЛ: Хүлээгдэж буй    |    УЛААН: Ирээгүй'
        ws['A4'].font = Font(color='52647A', italic=True, size=9)
        ws.row_dimensions[4].height = 23
        headers = ['№', 'Сурагчийн нэр', 'Ирцийн төлөв', 'Ирсэн цаг', 'Огноо']
        for col, value in enumerate(headers, start=1):
            cell = ws.cell(5, col, value)
            cell.font = Font(color=WHITE, bold=True)
            cell.fill = PatternFill('solid', fgColor=BLUE)
            cell.alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[5].height = 28
        for index, student in enumerate(students, start=1):
            row = index + 5
            arrived = student in present
            finished = bool(day.get('finished'))
            late = arrived and AttendanceRecorder._is_late(present[student])
            state = ('Хоцорсон' if late else 'Ирсэн') if arrived else ('Ирээгүй' if finished else 'Хүлээгдэж буй')
            bg = (YELLOW_BG if late else GREEN_BG) if arrived else (RED_BG if finished else PENDING_BG)
            fg = (YELLOW_TEXT if late else GREEN_TEXT) if arrived else (RED_TEXT if finished else PENDING_TEXT)
            data_values = [index, student, state, present.get(student, '—'), day_key]
            for col, value in enumerate(data_values, start=1):
                cell = ws.cell(row, col, value)
                cell.fill = PatternFill('solid', fgColor=bg)
                cell.font = Font(color=fg if col == 3 else NAVY, bold=(col == 3))
                cell.alignment = Alignment(vertical='center', horizontal='center' if col != 2 else 'left')
                cell.border = Border(bottom=Side(style='hair', color='DDE6F1'))
            ws.cell(row, 2).data_type = 's'  # Student names cannot become Excel formulas.
            ws.row_dimensions[row].height = 25
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 32
        ws.column_dimensions['C'].width = 24
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 30
        ws.freeze_panes = 'C6'
        if students:
            ws.auto_filter.ref = f'A5:E{len(students)+5}'


def open_attendance_folder(dataset_path):
    """Open the folder, not the Excel file (which may be write-locked by Excel)."""
    path = Path(dataset_path).parent
    path.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        os.startfile(str(path))
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', str(path)])
    else:
        subprocess.Popen(['xdg-open', str(path)])
