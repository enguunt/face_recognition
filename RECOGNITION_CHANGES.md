# Register bolon recognize deer yu oorchilsn be — 2026-11-17

Omnoh latin usgeer bichsen huvilbar (7f0f107)-aas hoish hiisen oorchlolt.

## register.py

- Delgets deer zaavar, bichig zurahaas omno tsever frame-iig huuldag bolgosn.
- Nuurnii zurgiig ter tsever frame-aas tasalj hadgalna. Ingeseer hadgalsan zurag deer delgetsiin bichig davhar orohgui.
- Zurag avah 3 second-iin beltgel, bairlal bur deer 3 zurag avah bolon chanariin shalgaltiig heveer uldeesen.

## recognize.py

- Nuur buriig tusdaa ID, neriiin tolovtei dagadag bolgosn. Hajuugaas oor hun orj irhed omnoh hunii tanilt dahin ehlehgui.
- Shine nuur tanih ajil ehluuleh zavsriig 0.7-oos 0.15 second bolgosn. Gehdee model ooroo 0.15 second dotor bodno gesen ug bish.
- Neg tanigdsan nuuriig dahin dahin DeepFace-aar bodohgui, frame bur deer hureeg ni dagana. Ingeseer davtan tootsoolol bagasna.
- Burtgeliin zurguudiig program ehlehed neg udaa vector bolgodog heveer.
- Jijig (90px-ees baga) esvel budeg (Laplacian variance < 35) nuuriig Unknown gej uzne.
- Dataset-iin zamiig recognize.py baigaa havtastai ni holboj togtoodog bolgosn.
- Huniig tanisnii daraa camera shuud haagdahgui. Camera-iin tsonh deer Q darj garna.

## recognition_policy.py — shine file, zaaval hamt baih ystoi

- Neg hunii hamgiin oir 3 hurtelh zurgiin cosine distance-iin dundjiig ashiglana.
- Distance bosgo 0.36 heveer. Hamgiin oir 2 neriin onoonii zoruu 0.08-aas baga bol Unknown bolgono.
- Neg nertei daraalsan hamgiin bagadaa 2 tanilt, niit 0.3 second ongorson uyd neriig batalgaajuulna. Model udaan bol bodit hugatsaa urt baina.
- Huvi, second-iin bichgiig hasaasn: shalgaj baih uyd Searching..., tanigdsan bol zuvhun ner, taarahgui bol Unknown gej haruulna.
- Tanigdsan nuur nogoon, shalgaj bgaa nuur shar, Unknown nuur ulaan hureetei.
- Tanigdsan neriig tuhain nuurnii track urgeljilj bgaa hugatsaand hadgalna. Nuur alga boloh esvel hureenuud davhtsaj yalgahad ergelzeetei bol dahin tanina.
- Neg neriig 2 haragdaj bgaa nuur deer zereg batalgaajuulahgui. Hureenii hodolgooniig zoolruulj chichirgeeg bagasgasn.
- Frame-aas alga bolson nuurnii hotsorson hariug shine nuur deer onoohgui.

## Yaj ajilluulah ve

Ene 3 Python file-iig neg havtast bailgana. Odoo ashiglaj bgaa Python orchindoo Terminal deer:

```bash
python register.py
python recognize.py
```

`>>>` Python prompt dotor ene command-uudiig bichihgui. Shine GUI san shaardahgui; customtkinter ene shinechlelted oroogui.

## Yu shalgasn, yu anhaarah ve

Python syntax, hurdan batalgaajuulalt, 2 dahi hun orj irhed omnoh neriig hadgalah, davhar ner, hotsorson hariu bolon Unknown-iin logikiig hiimel ogogdloor shalgasn. Bodit camera deer hurd, taniltiin nariivchlal hemjeegui.

Neriig track deer hadgalah ni tur zuuryn savlagaag arilgana. Gehdee anh buruu tanisan bol ter neriig bas hadgalj bolno. Huree dagaj bgaa ni ter huniig dahin tanij batalgaajuulj bgaa gesen ug bish. Neg l Carlo haragdah durem ni anh tanigdsan hun yag Carlo mon gedgiig batalahgui. Tostei bolon burtgelgui humuuseer boditoor turshih heregtei.
