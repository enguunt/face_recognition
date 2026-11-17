# Taniltiin 3 asuudliin zasvar

## 1. Burtgel bolon tanilt neg dataset ashiglana

Omno ni register.py Terminal-iin ajillaj bgaa havtas dotor dataset uusgedeg, recognize.py ooriin file-iin hajuud dataset haidag, minimal app Documents/FACEVISION/dataset ashigladag baisan. App deer burtguulsen hun Terminal-iin tanih program deer haragdahgui baih bolomjtoi baisan.

Odoo facevision_config.py dotor DATASET-iin zamiig neg udaa todorhoilson. register.py, recognize.py, facevision_light_minimal.py gurvuulaa ter tohirgoog ashiglana. Neg gazar burtguulsen zurag bugded adilhan hereglegdene; recognize-iig dahin ehluuleh, app deer Nuur tanih gorimiig dahin songohod shine burtgel unshigdana.

Shalgah ued Documents/FACEVISION/dataset dotor 60 zurag baisan, project dotor dataset havtas baigaagui. Zurag huulah, zooh, ustgah hiigeegui. Odoo bgaa zurguudiin zamiig program-uudtai taaruulsan.

## 2. Neg frame tasrahad ner arilahgui

Omno ni detector neg frame deer nuur olohgui bol tuhain hunii track shuud ustaj baisan. Daraagiin frame deer ter hun butsaj haragdahad shine hun gej uzdeg tul Searching... dahin gardag baisan.

Odoo 0.3 second hurtel bogino tasaldliin uyd track-iig tur hadgalna. Nuur dahin oir bairlald haragdval ner ni urgeljilne. Nuur haragdahgui ued huuchin huree delgets deer zuragdahgui. Haragdahgui nuurnii hotsorson taniltiin hariug ashiglahgui.

0.3 second-ees urt alga bolvol dahin tanina. Hoyor hureenii davhtsal yalgahad ergelzeetei bol huuchin neriig hamaagui hund shiljuulehgui, shineer shalgana. Bogino tasaldliin daraa yag ter bairlald oor hun soligdvol zuvhun bairlalaas hunii identity-g batalj chadahgui; doorh davtan shalgalt ene ersdeliig bagasgah zorilgotoi.

## 3. Anh buruu tanigdsan ner uurd hadgalagdahgui

Omno ni neg udaa Carlo bolson track-iig DeepFace-aar dahin shalgahgui baisan. Anh buruu tanisan bol ter ner nuur alga boltol heveer ulddeg baisan.

Odoo tanigdsan nuuriig 1.5 second-iin zavsartai background deer dahin shalgah bolomjtoi bolgoson. Shalgalt tusdaa thread deer hiigdeh heveer; UI thread deer DeepFace ajilluulahgui.

- Hariu omnoh nertei taarval ner ni heveer, aldaanii daraalal 0 bolno.
- Gants esvel hoyor Unknown/esvel oor ner garval omnoh neriig shuud arilgakhgui.
- Daraalsan 3 shalgalt omnoh nertei taarahgui bol huuchin batalgaajuulaltiig tsutslaj Unknown bolgono. Daraa ni shine tanilt ehelne.
- Jishee: Carlo -> Unknown -> Carlo bol ner heveer uldene.
- Jishee: buruu Carlo -> Other -> Other -> Other bol Carlo ner tsutslagdana. Other neriig shineer batalgaajuulj baij haruulna.

1.5 second ni ajil ehluuleh zavsar; model-iin bodoh hugatsaa, busad nuurnii achaallaas hamaarch hariu iluu udaan irj bolno. Ene bol bodit FPS-iin saijralt hemjsen oorchlolt bish. Davtan shalgalt tootsoolol nemne, gehdee frame bur deer tanihgui.

## Heveer uldsen zuils

Minimal UI-iin bairlal, ongo, tovchluuruudiig oorchloogui. Huvi, second-iin bichig nemeegui. Anhnii batalgaajuulalt hamgiin bagadaa 0.3 second ba 2 tanilt; model udaanaas hamaaran iluu urt baij bolno. Tanih bosgo 0.36 heveer. Neg neriig hoyor track deer zereg batalgaajuulahgui. Tanisnii daraa camera haagdahgui.

## Shalgalt

15 avtomat test tentsen. Uund dataset-iin neg tohirgoo ashiglah, bogino/urt tasaldal, hoyor hun, davhar ner, hotsorson hariu, davtan shalgalt, gants Unknown-d ner hadgalah, 3 daraalsan taarahgui hariund huuchin neriig tsutslah, shine neriig dahin batalgaajuulah nohtsoluud orson. Buh Python file-iin syntax shalgalt tentsen.

Bodit camera deer FPS bolon nuur taniltiin nariivchlaliig ene shalgaltad hemjeegui. Hiimel test tentsen ni buh bodit nuuriig aldaagui tanina gesen batalgaa bish.

Ajilluulah:

```bash
source venv/bin/activate
python facevision_light_minimal.py
```

Test:

```bash
venv/bin/python -m unittest discover -s tests -v
```

recognize.py-g oor repo ruu huulah bol recognition_policy.py bolon shine facevision_config.py-g hamt avna. Shine app-iig FACEVISION.spec-eer dist/FACEVISION.app bolgoj build hiisen. App-iin tsonh bolon bagts dotorh model/dependency shalgalt tentsen. Camera permission-iig ehnii heregleen deer macOS asuuj bolno. GitHub ruu push hiigeegui.


FPS-iin daraagiin zasvar bolon hemjiltiin tailbar: [FPS_EXPLAINED.md](FPS_EXPLAINED.md).
