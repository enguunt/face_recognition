"""Attendance history and recoverable enrollment removal; no camera dependencies."""
import csv
from contextlib import closing
from datetime import datetime
from pathlib import Path
import json
import shutil
import sqlite3
import uuid
from zoneinfo import ZoneInfo

from facevision_config import DATASET

TIMEZONE = ZoneInfo('Asia/Ulaanbaatar')


class AttendanceStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else DATASET.parent / 'attendance.sqlite3'

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.execute('CREATE TABLE IF NOT EXISTS attendance '
                           '(name TEXT NOT NULL, day TEXT NOT NULL, arrived_at TEXT NOT NULL, '
                           'PRIMARY KEY (name, day))')
        return connection

    def record(self, name, now=None):
        now = now or datetime.now(TIMEZONE)
        if now.tzinfo is None:
            raise ValueError('Attendance timestamps must include a timezone')
        now = now.astimezone(TIMEZONE)
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute('INSERT OR IGNORE INTO attendance VALUES (?, ?, ?)',
                                        (name, now.date().isoformat(), now.isoformat(timespec='seconds')))
            return cursor.rowcount == 1

    def rows(self, today=True):
        with closing(self._connect()) as connection, connection:
            if today:
                result = connection.execute('SELECT name, day, arrived_at FROM attendance '
                                            'WHERE day=? ORDER BY arrived_at DESC',
                                            (datetime.now(TIMEZONE).date().isoformat(),))
            else:
                result = connection.execute('SELECT name, day, arrived_at FROM attendance '
                                            'ORDER BY arrived_at DESC')
            return list(result)

    @staticmethod
    def export(path, rows):
        with open(path, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(['Name', 'Date', 'Arrival time (Asia/Ulaanbaatar)', 'Status'])
            for name, day, stamp in rows:
                writer.writerow([name, day, datetime.fromisoformat(stamp).strftime('%H:%M:%S'), 'Present'])


class EnrollmentStore:
    def __init__(self, dataset=DATASET):
        self.dataset = Path(dataset)
        self.archive = self.dataset.parent / 'deleted_people'

    def _person_path(self, name):
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            raise ValueError('Invalid person name')
        path = self.dataset / name
        if path.is_symlink() or path.resolve().parent != self.dataset.resolve():
            raise ValueError('Invalid person folder')
        return path

    def people(self):
        if not self.dataset.exists():
            return []
        return [(p.name, sum(f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.png')
                             for f in p.iterdir()))
                for p in sorted(self.dataset.iterdir()) if p.is_dir() and not p.is_symlink()]

    def remove(self, name):
        source = self._person_path(name)
        if not source.is_dir():
            raise FileNotFoundError(name)
        token = uuid.uuid4().hex
        target = self.archive / token
        target.mkdir(parents=True)
        try:
            (target / 'person.json').write_text(json.dumps({'name': name}, ensure_ascii=False))
            shutil.move(str(source), str(target / 'photos'))
        except Exception:
            shutil.rmtree(target)
            raise
        return token

    def removed(self):
        output = []
        if self.archive.exists():
            for folder in sorted(self.archive.iterdir()):
                try:
                    if folder.is_symlink() or not (folder / 'photos').is_dir():
                        continue
                    name = json.loads((folder / 'person.json').read_text())['name']
                    self._person_path(name)
                    output.append((folder.name, name))
                except (OSError, ValueError, KeyError, TypeError):
                    continue
        return output

    def restore(self, token):
        if token not in dict(self.removed()):
            raise ValueError('Invalid removed person')
        folder = self.archive / token
        name = json.loads((folder / 'person.json').read_text())['name']
        target = self._person_path(name)
        if target.exists():
            raise FileExistsError('Ijil nertei burtgel baina. Davhar darj bichihgui.')
        self.dataset.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder / 'photos'), str(target))
        return name
