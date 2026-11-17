"""Local FACEVISION student enrollment management with recoverable removals.

Only active dataset subdirectories are used for recognition. Deleting here moves a
person's photographs to Documents/FACEVISION/deleted_students; it never silently
removes biometric photos or older attendance records.
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path


PHOTO_TYPES = {'.jpg', '.jpeg', '.png'}


def valid_name(name):
    return (isinstance(name, str) and 0 < len(name) <= 40
            and all(ch.isalnum() or ch in '_-' for ch in name)
            and name not in ('.', '..'))


class StudentStore:
    def __init__(self, dataset_path):
        self.dataset = Path(dataset_path)
        self.archive = self.dataset.parent / 'deleted_students'

    def active(self):
        if not self.dataset.exists():
            return []
        students = []
        for folder in self.dataset.iterdir():
            if folder.is_dir() and not folder.is_symlink() and valid_name(folder.name):
                photos = sum(1 for f in folder.iterdir()
                             if f.is_file() and f.suffix.lower() in PHOTO_TYPES)
                students.append((folder.name, photos))
        return sorted(students, key=lambda item: item[0].casefold())

    def names(self):
        return [name for name, _ in self.active()]

    def _active_path(self, name):
        if not valid_name(name):
            raise ValueError('Нэр зөвхөн үсэг, тоо, _ болон - агуулна (40 хүртэл тэмдэгт).')
        path = self.dataset / name
        if path.is_symlink():
            raise ValueError('Симболик холбоосын зургийн хавтас өөрчлөхгүй.')
        return path

    def _check_no_duplicate(self, name, exclude=None):
        for existing, _ in self.active():
            if existing.casefold() == name.casefold() and existing != exclude:
                raise FileExistsError(f'"{existing}" гэсэн нэр бүртгэлтэй байна.')

    def rename(self, old, new):
        source = self._active_path(old)
        dest = self._active_path(new)
        if not source.is_dir():
            raise FileNotFoundError(f'"{old}" сурагч олдсонгүй.')
        if old == new:
            return
        self._check_no_duplicate(new, exclude=old)
        if dest.exists() or old.casefold() == new.casefold():
            raise FileExistsError('Ижил нэртэй эсвэл зөвхөн том/жижиг үсгээр ялгаатай нэр байна.')
        source.rename(dest)

    def remove(self, name):
        """Move a student from active enrollment to a recoverable local archive."""
        source = self._active_path(name)
        if not source.is_dir():
            raise FileNotFoundError(f'"{name}" сурагч олдсонгүй.')
        self.archive.mkdir(parents=True, exist_ok=True)
        now = datetime.now().isoformat(timespec='seconds')
        key = f'{name}__{datetime.now():%Y%m%d_%H%M%S}__{uuid.uuid4().hex[:8]}'
        destination = self.archive / key
        shutil.move(str(source), str(destination))
        (destination / '.facevision_removed.json').write_text(
            json.dumps({'name': name, 'removed_at': now}, ensure_ascii=False, indent=2),
            encoding='utf-8')
        return destination

    def removed(self):
        if not self.archive.exists():
            return []
        out = []
        for folder in self.archive.iterdir():
            if not folder.is_dir() or folder.is_symlink():
                continue
            manifest = folder / '.facevision_removed.json'
            if not manifest.is_file():
                continue
            try:
                info = json.loads(manifest.read_text(encoding='utf-8'))
                if valid_name(info['name']):
                    out.append((folder.name, info['name'], info.get('removed_at', '')))
            except (KeyError, ValueError, UnicodeError, OSError):
                continue
        return sorted(out, key=lambda entry: entry[2], reverse=True)

    def restore(self, archive_key):
        records = {key: original for key, original, _ in self.removed()}
        if archive_key not in records:
            raise FileNotFoundError('Сэргээх бүртгэл олдсонгүй.')
        name = records[archive_key]
        self._check_no_duplicate(name)
        target = self._active_path(name)
        if target.exists():
            raise FileExistsError(f'"{name}" гэсэн бүртгэл аль хэдийн байна.')
        self.dataset.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.archive / archive_key), str(target))
        (target / '.facevision_removed.json').unlink(missing_ok=True)
        return name
