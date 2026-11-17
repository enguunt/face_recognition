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
from recognition_policy import match_identity, MultiFaceTracker
from facevision_config import DATASET
from camera_stream import CameraStream
from frame_metrics import FrameMetrics

# Mac app доторх биш, хэрэглэгчийн Documents дотор зураг хадгална.
STAGES = ['Front - No Glasses', 'Front - With Glasses', 'Turn Head Right', 'Turn Head Left']
LIMIT = 0.36

class App:
    def __init__(self, root):
        self.root = root
        root.title('FACEVISION')
        root.geometry('850x700')
        self.stream = None
        self.update_job = None
        self.last_sequence = 0
        self.frame_time = 0
        self.metrics = FrameMetrics()
        self.last_metrics_update = 0
        self.profile = os.environ.get('FACEVISION_PROFILE') == '1'
        self.last_profile_report = 0
        self.mode = 'detect'
        self.running = False
        self.busy = False
        self.q = queue.Queue()
        self.known = {}
        self.results = []
        self.last_check = 0
        self.tracker = MultiFaceTracker()
        self.session = 0
        self.boxes = []
        self.result_time = 0
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
        self._build_light_ui()
        root.after(60, self.poll)
        root.protocol('WM_DELETE_WINDOW', self.exit)

    def _build_light_ui(self):
        """Light Minimal загвар: цагаан фон, цэнхэр товч, тусдаа бүртгэлийн самбар."""
        self.root.configure(bg="#F5F8FF")
        self.root.geometry("1000x760")
        self.root.minsize(760, 620)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Blue.TButton", background="#1769FF", foreground="white",
                        font=("Helvetica", 12, "bold"), padding=(16, 12),
                        borderwidth=0)
        style.map("Blue.TButton", background=[("active", "#0951CF")])
        style.configure("Pale.TButton", background="#E8EFFC", foreground="#16355F",
                        font=("Helvetica", 12), padding=(16, 12), borderwidth=0)
        style.map("Pale.TButton", background=[("active", "#D7E5FC")])
        style.configure("Small.TButton", background="#EEF3FB", foreground="#173A70",
                        font=("Helvetica", 11), padding=(10, 8), borderwidth=0)
        style.configure("Light.TEntry", padding=9, font=("Helvetica", 12))

        header = tk.Frame(self.root, bg="white", padx=24, pady=16)
        header.pack(fill="x")
        title_group = tk.Frame(header, bg="white")
        title_group.pack(side="left")
        tk.Label(title_group, text="◉", font=("Helvetica", 27, "bold"),
                 fg="#1769FF", bg="white").pack(side="left", padx=(0, 12))
        title_text = tk.Frame(title_group, bg="white")
        title_text.pack(side="left")
        tk.Label(title_text, text="FACEVISION", font=("Helvetica", 23, "bold"),
                 fg="#13233E", bg="white").pack(anchor="w")
        tk.Label(title_text, text="Нүүр таних систем", font=("Helvetica", 11),
                 fg="#64748B", bg="white").pack(anchor="w")
        ttk.Button(header, text="＋  Бүртгэх", style="Blue.TButton",
                   command=self.toggle_register_panel).pack(side="right")

        content = tk.Frame(self.root, bg="#F5F8FF", padx=22, pady=18)
        content.pack(fill="both", expand=True)

        self.camera_card = tk.Frame(content, bg="white", highlightbackground="#DEE6F2",
                                    highlightthickness=1)
        self.camera_card.pack(side="left", fill="both", expand=True, padx=(0, 14))
        camera_header = tk.Frame(self.camera_card, bg="white", padx=16, pady=13)
        camera_header.pack(fill="x")
        tk.Label(camera_header, text="Шууд камер", bg="white", fg="#15243B",
                 font=("Helvetica", 15, "bold")).pack(side="left")
        self.fps_text = tk.StringVar(value="● LIVE")
        tk.Label(camera_header, textvariable=self.fps_text, bg="white", fg="#16A34A",
                 font=("Helvetica", 11, "bold")).pack(side="right")

        self.screen = tk.Label(self.camera_card, text="Камерын дүрс энд харагдана",
                               bg="#1F2937", fg="#D1D5DB",
                               font=("Helvetica", 14))
        self.screen.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        sidebar = tk.Frame(content, bg="#F5F8FF", width=260)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        actions = tk.Frame(sidebar, bg="white", padx=16, pady=16,
                           highlightbackground="#DEE6F2", highlightthickness=1)
        actions.pack(fill="x")
        tk.Label(actions, text="Удирдлага", bg="white", fg="#15243B",
                 font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Button(actions, text="▶  Камер нээх", style="Blue.TButton",
                   command=self.open_camera).pack(fill="x", pady=4)
        ttk.Button(actions, text="▢  Камер хаах", style="Pale.TButton",
                   command=self.close_camera).pack(fill="x", pady=4)
        ttk.Button(actions, text="◎  Нүүр таних", style="Pale.TButton",
                   command=lambda: self.change_mode("recognize")).pack(fill="x", pady=4)
        ttk.Button(actions, text="◯  Нүүр илрүүлэх", style="Pale.TButton",
                   command=lambda: self.change_mode("detect")).pack(fill="x", pady=4)

        self.register_panel = tk.Frame(sidebar, bg="white", padx=16, pady=16,
                                       highlightbackground="#DEE6F2", highlightthickness=1)
        tk.Label(self.register_panel, text="Нүүр бүртгэх", bg="white",
                 fg="#15243B", font=("Helvetica", 16, "bold")).pack(anchor="w")
        tk.Label(self.register_panel, text="Бүртгүүлэх хүний нэр", bg="white",
                 fg="#64748B", font=("Helvetica", 10)).pack(anchor="w", pady=(12, 5))
        ttk.Entry(self.register_panel, textvariable=self.name,
                  style="Light.TEntry").pack(fill="x")
        ttk.Button(self.register_panel, text="Бүртгэл эхлүүлэх", style="Blue.TButton",
                   command=self.register).pack(fill="x", pady=(12, 5))
        ttk.Button(self.register_panel, text="Зураг авах", style="Pale.TButton",
                   command=self.take_photos).pack(fill="x", pady=4)
        ttk.Button(self.register_panel, text="Алгасах", style="Small.TButton",
                   command=self.skip).pack(fill="x", pady=4)
        ttk.Button(self.register_panel, text="Зогсоох", style="Small.TButton",
                   command=lambda: self.change_mode("detect")).pack(fill="x", pady=4)
        # Анх бүртгэлийн самбар нуугдсан байна.

        status_card = tk.Frame(sidebar, bg="white", padx=16, pady=16,
                               highlightbackground="#DEE6F2", highlightthickness=1)
        status_card.pack(fill="x", pady=(12, 0))
        tk.Label(status_card, text="Системийн төлөв", bg="white", fg="#15243B",
                 font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(0, 8))
        tk.Label(status_card, textvariable=self.status, bg="white", fg="#475569",
                 font=("Helvetica", 11), wraplength=220,
                 justify="left").pack(anchor="w")

        footer = tk.Frame(self.root, bg="white", padx=24, pady=11)
        footer.pack(fill="x")
        tk.Label(footer, text="FACEVISION  •  Light Minimal", bg="white",
                 fg="#64748B", font=("Helvetica", 10)).pack(side="left")
        tk.Label(footer, text="Mac • Python • FaceNet", bg="white",
                 fg="#64748B", font=("Helvetica", 10)).pack(side="right")

    def toggle_register_panel(self):
        if self.register_panel.winfo_manager():
            self.register_panel.pack_forget()
        else:
            self.register_panel.pack(fill="x", pady=(12, 0),
                                     before=self.register_panel.master.winfo_children()[-1])

    def open_camera(self):
        if self.running:
            return
        if self.stream is not None and self.stream.alive:
            self.status.set('Camera haagdaj baina, tur huleegeed dahin neene uu.')
            return
        self.stream = CameraStream()
        self.last_sequence = 0
        self.metrics = FrameMetrics()
        self.last_metrics_update = 0
        self.last_profile_report = 0
        self.running = True
        self.status.set('Camera neegdej baina...')
        self.stream.start()
        self.schedule_update(10)

    def schedule_update(self, delay_ms):
        if self.running and self.update_job is None:
            self.update_job = self.root.after(delay_ms, self.update)

    def close_camera(self):
        self.session += 1
        self.tracker.reset()
        self.results = []
        self.running = False
        if self.update_job is not None:
            self.root.after_cancel(self.update_job)
            self.update_job = None
        if self.stream is not None:
            self.stream.stop()
        self.photo = None
        self.screen.configure(image='', text='Камер хаалттай')
        self.fps_text.set('● LIVE')
        self.status.set('Камер хаалттай')

    def change_mode(self, mode):
        if self.busy:
            self.status.set('Түр хүлээнэ үү, боловсруулж байна...')
            return
        self.session += 1
        self.tracker.reset()
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
            name = 'Unknown'
            try:
                if min(crop.shape[:2]) >= 90:
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    if cv2.Laplacian(gray, cv2.CV_64F).var() >= 35:
                        v = self.embedding(crop)
                        if v is not None:
                            name = match_identity(v, self.known, threshold=LIMIT)
            except Exception as e:
                print('Таних алдаа:', e)
            output.append((box, name))
        return output

    def background(self, kind, fn, *args):
        if self.busy:
            return False
        self.busy = True
        session = self.session
        captured_at = self.frame_time if kind == 'recognize' else time.monotonic()
        def work():
            started = time.monotonic()
            try:
                result = fn(*args)
                self.q.put((kind, result, None, session, captured_at,
                            (time.monotonic()-started)*1000))
            except Exception as e:
                self.q.put((kind, None, str(e), session, captured_at,
                            (time.monotonic()-started)*1000))
        threading.Thread(target=work, daemon=True).start()
        return True

    def poll(self):
        try:
            while True:
                kind, value, error, session, captured_at, elapsed_ms = self.q.get_nowait()
                self.busy = False
                if session != self.session:
                    continue
                self.metrics.record(kind, elapsed_ms)
                if error:
                    self.status.set('Алдаа: ' + error)
                elif kind == 'load':
                    self.known = value
                    self.status.set(f'Бүртгэлтэй хүн: {len(value)}')
                elif kind == 'recognize' and self.mode == 'recognize':
                    names = self.tracker.apply(value, captured_at, time.monotonic())
                    if names:
                        self.status.set('Танигдсан: ' + ', '.join(names))
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
        self.session += 1
        self.tracker.reset()
        self.results = []
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
        self.update_job = None
        if not self.running:
            return
        started = time.monotonic()
        if self.stream.error:
            error = self.stream.error
            self.close_camera()
            self.status.set('Алдаа: ' + error)
            return
        packet = self.stream.latest(self.last_sequence)
        if packet is None:
            self.schedule_update(8)
            return
        if self.last_sequence == 0:
            self.status.set('Камер ажиллаж байна')
        self.last_sequence = packet.sequence
        self.frame_time = packet.captured_at
        self.metrics.record('camera_read', packet.read_ms)
        self.metrics.record('detect', packet.detect_ms)
        self.metrics.record('frame_age', (started-packet.captured_at)*1000)
        # Worker owns its frame; draw overlays only on this UI copy.
        frame = packet.image.copy()
        h, w = frame.shape[:2]
        boxes = list(packet.boxes)
        self.boxes = boxes
        now = time.monotonic()
        visible = self.tracker.update(boxes, now)
        if self.mode == 'recognize' and visible and not self.busy and now-self.last_check >= 0.15:
            items = []
            for person in visible:
                if not person.needs_recognition(now):
                    continue
                box = person.box
                x1,y1,x2,y2 = box
                pad = int((x2-x1)*0.15)
                crop = frame[max(0,y1-pad):min(h,y2+pad), max(0,x1-pad):min(w,x2+pad)].copy()
                if crop.size:
                    items.append((person.id, crop))
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
        for person in visible:
            x1,y1,x2,y2 = person.display_box
            label, color = 'Face Detected', (0, 200, 255)
            if self.mode == 'register':
                label = STAGES[self.stage]
            elif self.mode == 'recognize':
                label, color = person.label()
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(frame, label, (x1,max(25,y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img.thumbnail((max(320,self.screen.winfo_width()-16), max(220,self.screen.winfo_height()-16)))
        self.photo = ImageTk.PhotoImage(img)
        self.screen.configure(image=self.photo, text='')
        finished = time.monotonic()
        self.metrics.record('ui_render', (finished-started)*1000)
        self.metrics.present(finished)
        if finished - self.last_metrics_update >= 0.5:
            self.fps_text.set(f'● LIVE · {self.metrics.fps:.0f} FPS')
            self.last_metrics_update = finished
        if self.profile and finished-self.last_profile_report >= 5:
            print(self.metrics.report())
            self.last_profile_report = finished
        # Aim for 30 displayed FPS; processing time is part of the frame budget.
        self.schedule_update(max(1, int(1000/30 - (finished-started)*1000)))

    def exit(self):
        self.close_camera()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
