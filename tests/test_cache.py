import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from embedding_cache import FaceEmbeddingCache

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dataset = Path(self.temp.name) / 'dataset'
        self.dataset.mkdir()
        (self.dataset/'Tugsuu').mkdir()
        self.image = self.dataset/'Tugsuu'/'1.jpg'
        self.image.write_bytes(b'photo-one')
        self.calls = []
        def embedding(path):
            self.calls.append(path)
            return np.array([3,4,0], dtype=np.float32)
        self.cache = FaceEmbeddingCache(self.dataset, embedding)

    def test_repeat_cache_and_modify(self):
        one=self.cache.load_people()
        self.assertEqual(len(self.calls),1)
        two=self.cache.load_people()
        self.assertEqual(len(self.calls),1)
        np.testing.assert_allclose(one['Tugsuu'],two['Tugsuu'])
        self.image.write_bytes(b'photo-two-new')
        self.cache.load_people()
        self.assertEqual(len(self.calls),2)
        self.image.unlink()
        self.assertEqual(self.cache.load_people(),{})
        stored=json.loads(self.cache.cache_path.read_text(encoding='utf-8'))
        self.assertEqual(stored['files'],{})

    def test_corrupt_cache_is_recomputed(self):
        self.cache.cache_path.write_text('{corrupted',encoding='utf-8')
        self.assertIn('Tugsuu',self.cache.load_people())

if __name__=='__main__':
    unittest.main()
