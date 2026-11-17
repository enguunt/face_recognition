# FACEVISION — Carlo-iin odoogiin local huvilbar

Collab-iin main source-iig Carlo-iin ajillaj bgaa local project-iin snapshot-toi taaruulsan. Local-iin 21 source/tohirgoo/tailbar file-iig byte-for-byte ijil huulsan. `facevision.py` ni minimal app-iig neeh jijig ehluulegch; taniltiin ooriin tusdaa huuchin code aguulahgui.

## Ajilluulah

Ajilladag Python orchnoo idevhjuuleed Terminal deer:

```bash
python facevision.py
```

Esvel yag local entry point:

```bash
python facevision_light_minimal.py
```

Camera neeh -> Nuur tanih. Burtgeh hesgees ner oruulj, burtgel ehluulj, zurag avna. Python-iin `>>>` dotor deerh command-uudiig bichihgui.

## Ene huvilbariin feature-uud

- Light Minimal UI, camera/detection tusdaa thread, latest frame, display FPS hemjilt.
- Nuur buriin tusdaa tracking, bogino tasaldliin 0.3 second-iin huleelt.
- Anhnii minimum 2 tanilt / 0.3 second-iin batalgaajuulalt; model-iin hurdnaas hamaaran iluu udaan baij bolno.
- Tanigdsan neriig 1.5 second-iin zavsartai dahin shalgaj, daraalsan 3 taarahgui hariund huuchin neriig tsutslana.
- Shared dataset: Documents/FACEVISION/dataset.
- Tanigdsan hunii odor buriin anhnii irts, Ulaanbaatar-iin ognoo/tsagaar SQLite-d hadgalna. Davhar odor/hun burtgehgui.
- Irtsiin tsonh: onoodor/buh tuuh, CSV export.
- Burtgeltei humuusiin tsonh: hun ustgah, ustgasniig sergeeh, taniltiin cache tseverleh. Irtsiin tuuh heveer uldene.
- Mac app build: FACEVISION.spec, bundled Facenet ONNX model.

## Test ba hemjilt

```bash
python -m unittest discover -s tests -v
FACEVISION_PROFILE=1 python facevision.py
python scripts/benchmark_video_pipeline.py
```

Restore hiihdee ene source deer local-iin ajilladag venv-eer 34 test shalgasan. Avtomat test ni bodit buh nuuriig aldaagui tanina gesen batalgaa bish. Benchmark ni hiimel nohtsoltoi scheduling haritsuulalt, bodit Tk+DeepFace FPS bish.

Python orchind NumPy, Pillow, OpenCV, MediaPipe, DeepFace bolon tuunii backend heregtei. Mac app build-d PyInstaller heregtei. Odoo bgaa local build ni Facenet ONNX backend/model ashigladag; FACEVISION.spec build hiihdee ~/.deepface/weights/facenet_weights.onnx belen baih shaardlagatai.

```bash
python -m PyInstaller --noconfirm FACEVISION.spec
```

Ur dun: dist/FACEVISION.app. Built app, model weights, venv, zurag, irtsiin database-g ene repo-d oruulaagui.

## Delgerengui tailbar

- [Buh file, import, function, test-iin delgerengui guide](FACEVISION_CODE_GUIDE.md)
- [Dataset, tracking, irts, ustgah/sergeeh zasvar](FIXES_EXPLAINED.md)
- [FPS pipeline bolon hemjilt](FPS_EXPLAINED.md)
- [Local huvilbar ruu butsaasan tailbar](RECOGNITION_CHANGES.md)

## Omnoh collab code-iin backup

Solihyn omnoh 01b49f7 commit backup/before-local-restore-20261117-01b49f7 branch deer hadgalagdsan. Git history-g rewrite/force push hiigeegui; shine restore commit nemsen.

Omnoh Windows/Excel/JSON/embedding-cache nemelt-uud ene local huvilbart baihgui tul main-aas hasagdsan. Ene huvilbariin camera ni macOS AVFoundation ashiglana, Windows EXE esvel universal OS demjleg gej oilgohgui. Hereglegchiin Documents dotorh huuchin zurag, Excel, JSON zereg file-uudiig ene Git oorchlolt ustgahgui; ene app-iin irts SQLite ashiglana.
