# -*- mode: python ; coding: utf-8 -*-
"""Build the existing minimal UI as one macOS app; generated files stay in build/."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

project = Path(SPECPATH)
weights = Path.home() / '.deepface' / 'weights' / 'facenet_weights.onnx'
if not weights.is_file():
    raise SystemExit('Facenet weights missing. Run Facenet once in the venv before building.')

# A generated launcher configures bundled resources without changing the app UI.
launcher = project / 'build' / 'FACEVISION_bootstrap.py'
launcher.parent.mkdir(parents=True, exist_ok=True)
launcher.write_text('''import os
import sys
from pathlib import Path
import tempfile

resources = Path(sys._MEIPASS)
os.environ['DEEPFACE_BACKEND_ENGINE'] = 'onnx'
os.environ['DEEPFACE_HOME'] = str(resources / 'model_store')
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'FACEVISION-matplotlib'))

# Headless bundle verification: never opens a camera or loads enrollment images.
if '--verify-bundle' in sys.argv:
    import json
    import traceback
    report = {'ok': False}
    try:
        import tkinter
        import numpy as np
        import cv2
        import mediapipe as mp
        from deepface import DeepFace
        from facevision_config import DATASET
        import facevision_light_minimal
        assert (resources / 'model_store/.deepface/weights/facenet_weights.onnx').is_file()
        interpreter = tkinter.Tcl()
        report['tcl_version'] = interpreter.eval('info patchlevel')
        with mp.solutions.face_detection.FaceDetection(model_selection=0) as detector:
            detector.process(np.zeros((480, 640, 3), dtype=np.uint8))
        representation = DeepFace.represent(
            img_path=np.zeros((160, 160, 3), dtype=np.uint8), model_name='Facenet',
            detector_backend='skip', enforce_detection=False, align=False)
        report.update(ok=True, embedding_dimensions=len(representation[0]['embedding']),
                      opencv=cv2.__version__, mediapipe=mp.__version__, dataset=str(DATASET))
    except Exception:
        report['error'] = traceback.format_exc()
    output = Path(sys.argv[sys.argv.index('--verify-bundle') + 1])
    output.write_text(json.dumps(report, indent=2))
    raise SystemExit(0 if report['ok'] else 1)

import runpy
runpy.run_module('facevision_light_minimal', run_name='__main__')
''')

datas = collect_data_files('mediapipe')
datas += collect_data_files('deepface')
datas += [(str(weights), 'model_store/.deepface/weights')]
for package in ('deepface', 'onnxruntime', 'opencv-python', 'gdown'):
    datas += copy_metadata(package)

a = Analysis(
    [str(launcher)],
    pathex=[str(project)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'facevision_light_minimal', 'camera_stream', 'frame_metrics',
        'facevision_config', 'recognition_policy', 'deepface.DeepFace',
        'deepface.models.facial_recognition.onnx.Facenet',
        'mediapipe.python.solutions.face_detection', 'onnxruntime',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['tensorflow', 'torch', 'keras', 'tf_keras', 'jax', 'jaxlib', 'pytest', 'IPython'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='FACEVISION', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FACEVISION')
app = BUNDLE(
    coll, name='FACEVISION.app', icon=None,
    bundle_identifier='com.carlo.facevision', version='1.0.0',
    info_plist={
        'CFBundleDisplayName': 'FACEVISION',
        'NSCameraUsageDescription': 'FACEVISION nuur burtgeh, ilruuleh bolon tanihad camera ashiglana.',
        'NSDocumentsFolderUsageDescription': 'FACEVISION burtgeliin zurguudiig Documents/FACEVISION/dataset dotor hadgalna.',
        'NSHighResolutionCapable': True,
    },
)
