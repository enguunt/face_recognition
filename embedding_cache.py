"""Incremental FaceNet embeddings cache for FACEVISION.

The cache remains in Documents/FACEVISION, *outside* the source tree.
It contains biometric vectors; treat it as sensitive local data.
"""
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from student_manager import PHOTO_TYPES, valid_name

# Change this when DeepFace model or preprocessing settings change.
CACHE_VERSION = 'Facenet_skip_noalign_v1'


class FaceEmbeddingCache:
    def __init__(self, dataset, embedder):
        self.dataset = Path(dataset)
        self.cache_path = self.dataset.parent / 'face_embeddings_cache.json'
        self.embedder = embedder

    def _read(self):
        try:
            payload = json.loads(self.cache_path.read_text(encoding='utf-8'))
            if payload.get('version') == CACHE_VERSION and isinstance(payload.get('files'), dict):
                return payload['files']
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return {}

    def _write(self, entries):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmpname = tempfile.mkstemp(prefix='.face_cache_', suffix='.json',
                                            dir=self.cache_path.parent)
        try:
            with os.fdopen(handle, 'w', encoding='utf-8') as f:
                json.dump({'version': CACHE_VERSION, 'files': entries}, f,
                          ensure_ascii=False, separators=(',', ':'))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmpname, self.cache_path)
        finally:
            Path(tmpname).unlink(missing_ok=True)

    def load_people(self):
        old = self._read()
        fresh = {}
        known = {}
        if self.dataset.is_dir():
            for folder in sorted(self.dataset.iterdir(), key=lambda p: p.name.casefold()):
                if not folder.is_dir() or folder.is_symlink() or not valid_name(folder.name):
                    continue
                vectors = []
                for photo in sorted(folder.iterdir(), key=lambda p: p.name):
                    if not photo.is_file() or photo.is_symlink() or photo.suffix.lower() not in PHOTO_TYPES:
                        continue
                    try:
                        st = photo.stat()
                        key = f'{folder.name}/{photo.name}'
                        previous = old.get(key)
                        if (isinstance(previous, dict)
                            and previous.get('size') == st.st_size
                            and previous.get('mtime_ns') == st.st_mtime_ns):
                            raw = previous.get('vector')
                            v = np.asarray(raw, dtype=np.float32) if raw is not None else None
                        else:
                            v = self.embedder(str(photo))
                        if v is None or getattr(v, 'ndim', 0) != 1 or not v.size:
                            continue
                        norm = float(np.linalg.norm(v))
                        if not np.isfinite(norm) or norm <= 0:
                            continue
                        v = (v / norm).astype(np.float32)
                        vectors.append(v)
                        fresh[key] = {'size': st.st_size, 'mtime_ns': st.st_mtime_ns,
                                      'vector': v.tolist()}
                    except Exception as error:
                        print('Нүүрний зураг боловсруулахад алдаа:', photo, error)
                if vectors:
                    # A person's photos must use the same embedding model / dimension.
                    dimensions = vectors[0].shape
                    compatible = [v for v in vectors if v.shape == dimensions]
                    if compatible:
                        known[folder.name] = np.stack(compatible)
        if fresh != old or not self.cache_path.exists():
            try:
                self._write(fresh)
            except OSError as error:
                # Failure to save an optimization must not prevent recognition.
                print('Векторын кэш хадгалах боломжгүй:', error)
        return known
