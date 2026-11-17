# FACEVISION

Huuchin facevision.py interface-iig shine Light Minimal app-aar solison. Odoo `python facevision.py` gej ajilluulahad shine minimal tsonh neegdene. Tanih, burtgeh, FPS bolon saijruulsan buh ajil ter shine app-aar yavna.

## Yaj ajilluulah ve?

Python san-uudaa suulgasan orchindoo Terminal deer:

```bash
python facevision.py
```

`python facevision_light_minimal.py` gej neesen ch ijil app ajillana. Hoyor tusdaa huvilbar bish: facevision.py ni minimal app-iin App class-iig ashigladag jijig ehluulegch. Ingej 2 file deer ijil 450 mor code huulahgui, daraagiin zasvar neg gazart hiigdej hoyulaa shinechlegdene.

Camera neeh -> Nuur tanih. Shine hun burtgeh bol Burtgeh tovch deer ner oruulaad burtgel ehluulj Zurag avah darna.

`>>>` Python prompt dotor command bichihgui. Mac camera permission asuuval camera ashiglah erh ogno.

## Huuchin app-aas yu saijirsan be?

| Oorchlolt | Yagaad hiisen, odoo yaj ajillah ve? |
|---|---|
| Light Minimal interface | Tovchluur, camera, burtgeliin panel-iig tsegtstei neg tsonhond haruulna. |
| Neg dataset zam | Register, recognize, app bugd Documents/FACEVISION/dataset ashiglana. Oor havtast burtguuleed tanihgui baih asuudliig bagasgasn. |
| Nuur bur tusdaa track | Hajuugaas shine hun orj irhed omnoh hunii tanilt bugdeeree dahin ehlehgui. |
| Bogino tasaldliin huleelt | Nuur 0.3 second hurtel tur tasarval neriig hadgalna. Nuur haragdahgui ued huuchin huree zuragdahgui. |
| Hurdan anhnii batalgaajuulalt | Hamgiin bagadaa 2 tanilt, 0.3 second ongorsnii daraa neriig batalgaajuulna. Model-iin bodoh hugatsaanaas hamaarna. |
| Togtvortoi ner | Gants Unknown hariunaas bolj batalgaajsan neriig shuud arilgakhgui. Huvi, second haruulahgui. |
| Davtan batalgaajuulalt | 1.5 second-iin zavsartai dahin shalgana. Daraalsan 3 hariu taarahgui bol huuchin neriig tsutslana; anh buruu tanigdsan ner uurd uldehgui. |
| Davhar ner | Neg neriig 2 track deer zereg batalgaajuulahgui. Gehdee ene durem anh tanigdsan hun yag mon gedgiig batalahgui. |
| Camera haagdahgui | Huniig tanisnii daraa camera shuud haagdahgui, app-iin tovchluuraar udirdana. |
| Camera/detection tusdaa thread | Camera huleeh, MediaPipe bodoh ajil UI thread-iig shuud huleelgehgui. |
| Suuliin frame | Huuchin frame-uud queue bolj tsuglarahgui; delgets suuliin belen frame-iig avna. |
| FPS hemjilt | LIVE-iin hajuud shineer haruulsan frame-uudiin bodit FPS haragdana. |
| Register-iin tsever zurag | register.py hadgalah zurgaa delgetsiin bichig zurahaas omnoh frame-aas avna. |
| Mac app build | FACEVISION.spec minimal app, shaardlagatai san, Facenet model-iig neg FACEVISION.app bolgoj bagtsalna. |

## Ali file yu hiideg ve?

- facevision.py: huuchin neriig hadgalsan shine app-iin ehluulegch.
- facevision_light_minimal.py: interface, burtgel, taniltiin ajliig holboh undsen app.
- camera_stream.py: camera bolon MediaPipe detection-iin background worker.
- frame_metrics.py: delgetsend haruulsan FPS, millisecond-iin hemjilt.
- recognition_policy.py: nuur dagah, ner batalgaajuulah, Unknown, davhar ner, davtan shalgalt.
- facevision_config.py: program-uudiin niitleg dataset zam.
- register.py / recognize.py: tusdaa Terminal-aas ajilluulj boloh burtgel, taniltiin program.
- FACEVISION.spec: macOS app build-iin tohirgoo.

## Test bolon FPS-iin hemjilt

```bash
python -m unittest discover -s tests -v
```

Delgerengui hugatsaanii hemjiltiig Terminal deer harah:

```bash
FACEVISION_PROFILE=1 python facevision.py
```

Camera, Tk, OpenCV, MediaPipe, NumPy, Pillow, DeepFace bolon tuunii backend ni Python orchind suusan baih shaardlagatai. Hugjuuleltiin test-uud camera neehgui; bodit taniltiin nariivchlaliig tusad ni humuuseer turshina.

## Mac app build

Python orchind PyInstaller bolon deerh san-uud baih ystoi. Facenet-iig omno ni neg udaa ajilluulsan, ~/.deepface/weights/facenet_weights.onnx ni belen baih shaardlagatai.

```bash
python -m PyInstaller --noconfirm FACEVISION.spec
```

Ur dun: dist/FACEVISION.app. App ni model-oo dotoroo avna, burtgeliin zurguudiig Documents/FACEVISION/dataset dotor tusad ni hadgalna. Dataset, venv, model-iin tom file, build, dist-iig ene repo-d push hiigeegui.

## Delgerengui tailbaruud

- [3 gol zasvariin shaltgaan, ur dun](FIXES_EXPLAINED.md)
- [FPS zasvar bolon hemjiltiin delgerengui tailbar](FPS_EXPLAINED.md)
- [Register, recognize-iin omnoh oorchloltuud](RECOGNITION_CHANGES.md)

## Shalgasan zuil bolon hyazgaar

Avtomat test-uud ni code-iin tolov shiljilt, bogino/urt tasaldal, hoyor nuur, davhar ner, camera worker, resource cleanup zergiig shalgana. Bodit camera/detection-iin 30 frame-iin sample 23.3 delivered FPS garsan; ene ni Tk + DeepFace hamtdaa ajillah delgetsiin FPS bish, camera bolgon deer ijil too garna gesen batalgaa bish.

Tostei hun, gerel, budeg zurag, nuurnii bairlal zergees tanilt aldaj bolno. Huuchin neriig tur hadgalah baidliig davtan shalgalt bagasgah zorilgotoi ch buren aldaagui tanina gej batalahgui.
