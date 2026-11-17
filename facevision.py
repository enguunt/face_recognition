import os
import time
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

# Mac app доторх биш, хэрэглэгчийн Documents дотор зураг хадгална.
DATASET = Path.home() / 'Documents' / 'FACEVISION' / 'dataset'
STAGES = ['Front - No Glasses', 'Front - With Glasses', 'Turn Head Right', 'Turn Head Left']
LIMIT = 0.36

class App:
    def __init__(self, root):
        self.root = root
        root.title('FACEVISION')
        root.geometry('850x700')
        self.cam = None
        self.detector = None
        self.mode = 'detect'
        self.running = False
        self.busy = False
        self.q = queue.Queue()
        self.known = {}
        self.results = []
        self.last_check = 0
        self.name = tk.StringVar()
        self.status = tk.StringVar(value='Камер хаалттай')
        self.stage = 0
        self.count = 0
        self.total = 0
        self.capture_time = None
        self.next_photo = 0
        self.person = ''
        self.photo = None
        self.deepface = None
        tk.Label(root, text='FACEVISION', font=('Helvetica', 26, 'bold')).pack(pady=12)
        self.screen = tk.Label(root, text='Камерын дүрс', bg='#1e293b', fg='white')
        self.screen.pack(fill='both', expand=True, padx=18, pady=8)
        bar = tk.Frame(root)
        bar.pack(pady=5)
        for label, action in [('Камер нээх', self.open_camera), ('Камер хаах', self.close_camera),
                              ('Нүүр илрүүлэх', lambda: self.change_mode('detect')),
                              ('Нүүр таних', lambda: self.change_mode('recognize'))]:
            ttk.Button(bar, text=label, command=action).pack(side='left', padx=4)
        bar2 = tk.Frame(root)
        bar2.pack(pady=6)
        tk.Label(bar2, text='Нэр:').pack(side='left')
        ttk.Entry(bar2, textvariable=self.name, width=17).pack(side='left', padx=5)
        ttk.Button(bar2, text='Бүртгэх', command=self.register).pack(side='left', padx=4)
        ttk.Button(bar2, text='Зураг авах', command=self.take_photos).pack(side='left', padx=4)
        ttk.Button(bar2, text='Алгасах', command=self.skip).pack(side='left', padx=4)
        ttk.Button(bar2, text='Зогсоох', command=lambda: self.change_mode('detect')).pack(side='left', padx=4)
        tk.Label(root, textvariable=self.status, wraplength=760).pack(pady=10)
        root.after(60, self.poll)
        root.protocol('WM_DELETE_WINDOW', self.exit)

    def open_camera(self):
        if self.running:
            return
        try:
            import mediapipe as mp
            self.detector = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.6)
            self.cam = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
            if not self.cam.isOpened():
                raise RuntimeError('Камер нээгдсэнгүй. Mac Camera permission шалгана уу.')
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.running = True
            self.status.set('Камер ажиллаж байна')
            self.root.after(10, self.update)
        except Exception as e:
            messagebox.showerror('Алдаа', str(e))
            self.close_camera()

    def close_camera(self):
        self.running = False
        if self.cam:
            self.cam.release()
            self.cam = None
        if self.detector:
            self.detector.close()
            self.detector = None
        self.photo = None
        self.screen.configure(image='', text='Камер хаалттай')
        self.status.set('Камер хаалттай')

    def change_mode(self, mode):
        self.mode = mode
        self.results = []
        self.capture_time = None
        if mode == 'recognize':
            self.status.set('Бүртгэлтэй нүүрний мэдээллийг уншиж байна...')
            self.background('load', self.load_people)
        else:
            self.status.set('Нүүр илрүүлэх горим')

    def embedding(self, image):
        if self.deepface is None:
            from deepface import DeepFace
            self.deepface = DeepFace
        result = self.deepface.represent(img_path=image, model_name='Facenet',
                                         detector_backend='skip', enforce_detection=False, align=False)
        v = np.array(result[0]['embedding'], dtype=np.float32)
        norm = np.linalg.norm(v)
        return v / norm if norm else None

    def load_people(self):
        known = {}
        if DATASET.exists():
            for folder in sorted(DATASET.iterdir()):
                if not folder.is_dir():
                    continue
                vectors = []
                for file in folder.iterdir():
                    if file.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                        try:
                            v = self.embedding(str(file))
                            if v is not None:
                                vectors.append(v)
                        except Exception as e:
                            print('Зургийн алдаа:', file, e)
                if vectors:
                    known[folder.name] = np.stack(vectors)
        return known

    def recognize(self, items):
        output = []
        for box, crop in items:
            name, best = 'Unknown', float('inf')
            try:
                v = self.embedding(crop)
                if v is not None:
                    for person, vectors in self.known.items():
                        distances = np.sort(1 - vectors @ v)
                        score = float(np.mean(distances[:min(3, len(distances))]))
                        if score < LIMIT and score < best:
                            best, name = score, person
            except Exception as e:
                print('Таних алдаа:', e)
            output.append((box, name))
        return output

    def background(self, kind, fn, *args):
        if self.busy:
            return False
        self.busy = True
        def work():
            try:
                self.q.put((kind, fn(*args), None))
            except Exception as e:
                self.q.put((kind, None, str(e)))
        threading.Thread(target=work, daemon=True).start()
        return True

    def poll(self):
        try:
            while True:
                kind, value, error = self.q.get_nowait()
                self.busy = False
                if error:
                    self.status.set('Алдаа: ' + error)
                elif kind == 'load':
                    self.known = value
                    self.status.set(f'Бүртгэлтэй хүн: {len(value)}')
                elif kind == 'recognize' and self.mode == 'recognize':
                    self.results = value
        except queue.Empty:
            pass
        self.root.after(60, self.poll)

    def register(self):
        name = self.name.get().strip()
        if not name or len(name) > 40 or not all(c.isalnum() or c in '_-' for c in name):
            messagebox.showwarning('Нэр', 'Зөв нэр оруулна уу (үсэг, тоо, _ эсвэл -).')
            return
        if not self.running:
            messagebox.showwarning('Камер', 'Эхлээд камер нээнэ үү.')
            return
        self.person = name
        self.stage = self.count = self.total = 0
        self.capture_time = None
        self.mode = 'register'
        self.status.set(STAGES[0] + ' — Зураг авах дарна уу')

    def take_photos(self):
        if self.mode == 'register' and self.capture_time is None:
            self.capture_time = time.monotonic() + 3
            self.next_photo = self.capture_time
            self.status.set('3 секундын дараа зураг авна')

    def skip(self):
        if self.mode == 'register':
            self.next_stage()

    def next_stage(self):
        self.stage += 1
        self.count = 0
        self.capture_time = None
        if self.stage == 4:
            self.mode = 'detect'
            self.status.set(f'{self.person}: нийт {self.total} зураг хадгаллаа')
        else:
            self.status.set(STAGES[self.stage] + ' — Зураг авах дарна уу')

    def save_photo(self, crop):
        folder = DATASET / self.person
        folder.mkdir(parents=True, exist_ok=True)
        i = 1
        while (folder / f'{self.person}_new_{i}.jpg').exists():
            i += 1
        return cv2.imwrite(str(folder / f'{self.person}_new_{i}.jpg'), crop)

    def update(self):
        if not self.running:
            return
        ok, frame = self.cam.read()
        if not ok:
            self.close_camera()
            return
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        result = self.detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        boxes = []
        for detection in (result.detections or []):
            b = detection.location_data.relative_bounding_box
            x1, y1 = max(0, int(b.xmin*w)), max(0, int(b.ymin*h))
            x2, y2 = min(w, int((b.xmin+b.width)*w)), min(h, int((b.ymin+b.height)*h))
            if x2 > x1 and y2 > y1:
                boxes.append((x1, y1, x2, y2))
        if self.mode == 'recognize' and boxes and not self.busy and time.monotonic()-self.last_check >= 0.7:
            items = []
            for box in boxes:
                x1,y1,x2,y2 = box
                pad = int((x2-x1)*0.15)
                crop = frame[max(0,y1-pad):min(h,y2+pad), max(0,x1-pad):min(w,x2+pad)].copy()
                if crop.size:
                    items.append((box, crop))
            if items and self.background('recognize', self.recognize, items):
                self.last_check = time.monotonic()
        if not boxes:
            self.results = []
        if self.mode == 'register' and self.capture_time is not None:
            now = time.monotonic()
            if now < self.capture_time:
                cv2.putText(frame, str(int(self.capture_time-now)+1), (w//2,h//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0,255,255), 3)
            elif now >= self.next_photo:
                if len(boxes) == 1:
                    x1,y1,x2,y2 = boxes[0]
                    pad = int((x2-x1)*0.15)
                    crop = frame[max(0,y1-pad):min(h,y2+pad), max(0,x1-pad):min(w,x2+pad)].copy()
                    quality = crop.size and min(crop.shape[:2]) >= 90
                    if quality:
                        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                        quality = cv2.Laplacian(gray, cv2.CV_64F).var() >= 35
                    if quality and self.save_photo(crop):
                        self.count += 1
                        self.total += 1
                        self.status.set(f'{STAGES[self.stage]}: {self.count}/3')
                        self.next_photo = now + 0.8
                        if self.count == 3:
                            self.next_stage()
                    else:
                        self.status.set('Нүүр тод харагдах ёстой')
                        self.next_photo = now + 0.3
                else:
                    self.status.set('Зөвхөн нэг нүүр харагдах ёстой')
                    self.next_photo = now + 0.3
        for box in boxes:
            x1,y1,x2,y2 = box
            label = 'Face Detected'
            if self.mode == 'register':
                label = STAGES[self.stage]
            elif self.mode == 'recognize':
                label = 'Searching...'
                cx, cy = (x1+x2)/2, (y1+y2)/2
                best = 80
                for old, person in self.results:
                    ox, oy = (old[0]+old[2])/2, (old[1]+old[3])/2
                    distance = ((cx-ox)**2+(cy-oy)**2)**0.5
                    if distance < best:
                        best, label = distance, person
            color = (0,0,255) if label in ('Unknown','Searching...') else (0,255,0)
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(frame, label, (x1,max(25,y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img.thumbnail((max(320,self.screen.winfo_width()-16), max(220,self.screen.winfo_height()-16)))
        self.photo = ImageTk.PhotoImage(img)
        self.screen.configure(image=self.photo, text='')
        self.root.after(20, self.update)

    def exit(self):
        self.close_camera()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
