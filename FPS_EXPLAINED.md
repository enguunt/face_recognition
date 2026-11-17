# FPS bolon camera-iin gatsaltiin zasvar

## Omno ni yag yu bolj baisan be?

facevision_light_minimal.py-iin update() neg udaa ajillahdaa bugdiig daraallaar hiideg baisan:

1. Camera-aas daraagiin frame-iig huleej avna.
2. MediaPipe-aar ter frame deer nuur haana baigaag bodno.
3. Huree, ner, zurag avah zaavriig zurj tsonhond haruulna.
4. Ene buh ajil duussanii DARAA nemelt 20 millisecond huleene.

Ene ajluud tsonhnii UI thread deer baisan. UI thread gedeg ni tovchluur daralt, tsonhnii hodolgoon, delgets shinechleltiig hariutsdag undsen ajil. Camera read udaan huleevel esvel detector udaan bodvol tsonh ch bas huleedeg baisan. DeepFace tanilt ni omnoosoo tusdaa thread deer baisan; eniig anhnaasaa UI deer baisan gej tailbarlaagui.

Nemelt 20ms ni frame-iin buh hugatsaa bish. Jishee ni ajil ni 30ms bol +20ms = niit 50ms, ooroor helbel deed tal ni 20 FPS orchim bolno. Bodit toonuud camera bolon computer-oos hamaarch oor baina.

## Odoo yaj ajilladag bolson be?

### 1. Camera bolon nuur ilruulelt tusdaa ajillana

Shine camera_stream.py camera-aas frame avah, MediaPipe-aar nuur ilruuleh ajliig tusdaa thread deer hiine. Tsonhnii thread zuvhun belen zurag, belen nuurnii bairlaluudiig avch delgetsend zurdag.

Ingesneer camera hariugaa huleeh esvel nuur ilruulelt bodoj baih uyd tovchluur, tsonhnii ajliig shuud ter huleelttei hamt zogsoohgui. Gehdee CPU buren achaalaltai bolson ued GIL, OS scheduling, TensorFlow-iin CPU hereglee zeregees gatsalt buren arilna gesen batalgaa bish.

### 2. Huuchin frame-uud urt daraalal bolj tsuglarahgui

Worker zuvhun neg suuliin belen frame-iig hadgalna. Delgets udaan bolood frame #10-aas #15 hurtelh frame belen bolson baihad #11, #12, #13, #14-iig zaaval bugdiig ni uzehgui; #15-iig avna.

Ingesneer dursnii hotsrol urt queue-noos bolj nemegdehgui. Shine frame baihgui bol huuchin frame-iig dahin dahin resize hiij, shine PhotoImage uusgehgui. Ene ni app-iin queue-gui baidliig helj bgaa; camera backend-iin dotood buffering-iig hemjij oorchloogui.

### 3. Nemelt 20ms-iin huleeltiig niit frame-iin hugatsaatai tohiruulsan

Delgetsend 30 FPS orchim zorij, neg frame-d 33.3ms-iin hugatsaa tootsono. Jishee ni UI deer zurah ajil 5ms bol uldsen 28ms orchim huleene. UI deerh ajil 33ms-ees urt bol dahin 20ms nemj huleehgui.

Camera esvel detector 30 FPS gargaj chadahgui bol delgets 30 FPS bolohgui. 30 gedeg ni zorilt/deed hyazgaar, hiimel amlalt bish.

### 4. Bodit haruulsan FPS-iig delgetsend gargana

Camera-iin deed tald LIVE-iin hajuud FPS haragdana. Ene ni suuliin 60 hurtelh SHINEER haruulsan frame-iin hoorond ongorson hugatsaagaar bodogdono. Neg frame-iig olon udaa davtaj tolood FPS usguhgui. FPS-iin bichgiig 0.5 second tutamd shinechilne.

Camera, detection, frame-iin nas, UI render, DeepFace taniltiin millisecond-iin hemjilt bas nemsen. Engiin ashiglaltad ed nar console ruu bainga hevlegdehgui.

### 5. Camera haah uyd UI camera read duusahiig huleehgui

Haah tovch worker-t zogsoh huselt ogno. Worker camera bolon detector-oo ooriin thread deer chuluulnu. Huuchin worker buren duusaagui baihad shine camera worker davhar ehluulehgui. Davhardsan update callback tsuglarahgui baidlaar after callback-iig bas zohitsuulsan.

## Yamar file-uud oorchlogdson be?

- facevision_light_minimal.py: camera/detection-iig worker-t holboson, update-iin huleelt, FPS, hemjilt nemsen.
- camera_stream.py: shine; camera bolon detector-iin ajil, latest frame, error, resource cleanup.
- frame_metrics.py: shine; FPS bolon millisecond-iin rolling hemjilt.
- tests/test_camera_pipeline.py: shine; camera thread, frame queue uusgehgui baih, UI, timestamp, error cleanup-iin 8 test.
- tests/test_recognition.py: worker-iin hariund hugatsaanii hemjilt nemegdsentei ni taaruulsan; taniltiin shalgaltiig heveer hadgalsan.
- scripts/benchmark_video_pipeline.py: camera shaardahgui, huuchin/shine scheduling-iig hiimel nohtsold haritsuulah script.

Minimal-iin tovchluur, panel, ungu, ner tanih bosgo, dataset, burtgeliin bairlaluudiig ene udaa oorchloogui. Zuvhun LIVE bichgiin hajuud FPS nemsen. recognize.py-iin tusdaa OpenCV tsonh ene FPS shinechlelted oroogui; ene zasvar chinii minimal app-d zoriulagdsan. Shine app-iig daraa ni FACEVISION.spec-eer dist/FACEVISION.app bolgoj build hiisen. GitHub ruu push hiigeegui.

## Yu hemjsen be? Yund batalgaa ogch chadahgui ve?

Ehleed sandbox dotroos camera neeh gehed access denied, MediaPipe turshihad OpenGL service-iin hyazgaarlalt garsan. Chinii app-iin camera permission-iig oorchloogui. Normal orchind dahin shalgahad hoyulaa ajillasan.

Bodit camera-aas 30 frame avsan shine worker-iin headless sample: 23.3 delivered FPS, camera read dundaj 37.9ms, mirror/RGB/MediaPipe detection dundaj 4.0ms. Zurag hadgalaagui. Ene ni camera bolon detection-iin belen frame damjuulah hurd; Tk + DeepFace hamtdaa ajillah uyiin delgetsiin FPS bish. Huuchin app-iin bodit FPS-iig ijil nohtsold hemjeegui tul camera-iin hurd heden huviar nemegdseniig ene hemjilteer batalj helehgui.

Bodit MediaPipe-g 10 hiimel hooson 640x480 frame deer ajilluulahad detection dundaj 2.96ms garsan. Ene bas bodit nuur tanih nariivchlal esvel DeepFace-iin hurdnii hemjilt bish.

Harin 30 FPS-iin hiimel source, 20ms detection, 4ms render-tei haritsuulalt hiisen. Neg udaagiin ur dun:

| Hemjilt | Huuchin daraalsan loop | Shine worker loop |
|---|---:|---:|
| Hiimel delgets shinechleh hurd | 18.7 FPS | 25.9 FPS |
| UI callback dotor zartsuulsan dundaj hugatsaa | 29.8ms | 4.9ms |

Ene bol shine scheduling udaan camera/detection-ii huleeltiig UI-aas salgaj chadaj bgaag haruulsan turshilt. Chinii bodit camera yag 25.9 FPS bolno gesen ug bish. Hiimel benchmark ni sleep ashigladag, DeepFace-iin CPU achaalal, Tk-iin bodit zurah hugatsaag duuraigaagui. Ur dun dahin ajilluulahad baga zereg oor garna.

23 avtomat test tentsen. Omnoh 15 taniltiin test deer camera pipeline-iin 8 shalgalt nemegdsen. Python syntax shalgalt hiisen.

## Yaj ajilluulah, hemjiltiig yaj harah ve?

Huuchin camera-iin tsonhoo haagaad Terminal deer:

```bash
source venv/bin/activate
python facevision_light_minimal.py
```

Camera neegeed LIVE-iin hajuud FPS-iig harna. Nuur ilruuleh gorim, Nuur tanih gorim hoyriig adilhan tsonhnii hemjeetei ued haritsuulbal iluu oilgomjtoi. Nuur tanih gorim ehnii udaa zurguudaa achaalj duustal achaalal ih baij bolno.

Iluu delgerengui hemjilt heregtei bol:

```bash
FACEVISION_PROFILE=1 python facevision_light_minimal.py
```

Camera ajillaj baih uyd Terminal deer 5 second orchim tutamd:

- display_fps: shineer haruulsan frame-uudiin bodit hurd.
- camera_read: camera-aas frame huleej avah dundaj ms; undur baih ni camera-iin frame cadence-iig huleej bgaa heviin shaltgaantai ch baij bolno.
- detect: mirror, RGB huvirgalt, MediaPipe detection-d zartsuulsan dundaj ms.
- frame_age: camera-aas avsnaas UI bolovsruulalt ehelh hurtelh hugatsaa. Detection-iin hugatsaag bas bagtaana.
- ui_render: tracker, crop, overlay, Pillow/Tk image shinechleltiin callback dotorh dundaj ms. Tk/OS delgets deer fizik pixel haruulah hurtelh buh hugatsaa bish.
- recognize: background deer neg taniltiin batch-d zartsuulsan dundaj ms; neg esvel heden nuur bagtaj bolno.
- load: burtgeliin zurguud/model achaalakh ajliin hugatsaa.

Test:

```bash
venv/bin/python -m unittest discover -s tests -v
```

Hiimel haritsuulalt:

```bash
venv/bin/python scripts/benchmark_video_pipeline.py
```
