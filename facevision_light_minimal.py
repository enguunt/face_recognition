import os
import time
import queue
import threading
import platform
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
from recognition_policy import match_identity, MultiFaceTracker
from facevision_config import DATASET
from camera_stream import CameraStream
from frame_metrics import FrameMetrics
from attendance_excel import AttendanceRecorder, open_attendance_folder
from student_manager import StudentStore, valid_name
from embedding_cache import FaceEmbeddingCache

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
        self.camera_restart_job = None
        self._exiting = False
        self._poll_job = None
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
        self.attendance = AttendanceRecorder(DATASET)
        self.student_store = StudentStore(DATASET)
        self.attendance.roster(self.student_store.names())
        self.register_window = None
        self.manager_window = None
        self.student_list = None
        self.deleted_list = None
        self.student_rows = []
        self.deleted_rows = []
        self._build_light_ui()
        self._poll_job = root.after(60, self.poll)
        root.protocol('WM_DELETE_WINDOW', self.exit)

    def _build_light_ui(self):
        """A scrolling sidebar and a separate enrollment window prevent clipped buttons."""
        self.root.configure(bg='#F5F8FF')
        self.root.geometry('1120x770')
        self.root.minsize(780, 570)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Blue.TButton', background='#1769FF', foreground='white',
                        font=('Segoe UI', 11, 'bold'), padding=(12, 9), borderwidth=0)
        style.map('Blue.TButton', background=[('active', '#0951CF')])
        style.configure('Pale.TButton', background='#E8EFFC', foreground='#16355F',
                        font=('Segoe UI', 11), padding=(12, 9), borderwidth=0)
        style.map('Pale.TButton', background=[('active', '#D7E5FC')])
        style.configure('Small.TButton', background='#EEF3FB', foreground='#173A70',
                        font=('Segoe UI', 10), padding=(9, 7), borderwidth=0)
        style.configure('Light.TEntry', padding=8, font=('Segoe UI', 11))

        header = tk.Frame(self.root, bg='white', padx=22, pady=12)
        header.pack(fill='x')
        title_group = tk.Frame(header, bg='white')
        title_group.pack(side='left')
        tk.Label(title_group, text='◉', font=('Segoe UI', 24, 'bold'),
                 fg='#1769FF', bg='white').pack(side='left', padx=(0, 12))
        titles = tk.Frame(title_group, bg='white')
        titles.pack(side='left')
        tk.Label(titles, text='FACEVISION', font=('Segoe UI', 23, 'bold'),
                 fg='#13233E', bg='white').pack(anchor='w')
        tk.Label(titles, text='Нүүр таних · сурагчдын ирц', font=('Segoe UI', 10),
                 fg='#64748B', bg='white').pack(anchor='w')
        ttk.Button(header, text='＋  Бүртгэх', style='Blue.TButton',
                   command=self.toggle_register_panel).pack(side='right')

        content = tk.Frame(self.root, bg='#F5F8FF', padx=18, pady=14)
        content.pack(fill='both', expand=True)
        camera_card = tk.Frame(content, bg='white', highlightbackground='#DEE6F2',
                               highlightthickness=1)
        camera_card.pack(side='left', fill='both', expand=True, padx=(0, 12))
        camera_head = tk.Frame(camera_card, bg='white', padx=14, pady=11)
        camera_head.pack(fill='x')
        tk.Label(camera_head, text='Шууд камер', bg='white', fg='#15243B',
                 font=('Segoe UI', 14, 'bold')).pack(side='left')
        self.fps_text = tk.StringVar(value='● LIVE')
        tk.Label(camera_head, textvariable=self.fps_text, bg='white', fg='#16A34A',
                 font=('Segoe UI', 10, 'bold')).pack(side='right')
        self.screen = tk.Label(camera_card, text='Камерын дүрс энд харагдана',
                               bg='#1F2937', fg='#D1D5DB', font=('Segoe UI', 13))
        self.screen.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        sidebar = tk.Frame(content, bg='#F5F8FF', width=288)
        sidebar.pack(side='right', fill='y')
        sidebar.pack_propagate(False)
        self.sidebar_canvas = tk.Canvas(sidebar, bg='#F5F8FF', highlightthickness=0,
                                        bd=0, width=270)
        scroll = ttk.Scrollbar(sidebar, orient='vertical', command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.sidebar_canvas.pack(side='left', fill='both', expand=True)
        sidebar_body = tk.Frame(self.sidebar_canvas, bg='#F5F8FF')
        inner_id = self.sidebar_canvas.create_window((0, 0), window=sidebar_body, anchor='nw')
        sidebar_body.bind('<Configure>', lambda e: self.sidebar_canvas.configure(
            scrollregion=self.sidebar_canvas.bbox('all')))
        self.sidebar_canvas.bind('<Configure>', lambda e: self.sidebar_canvas.itemconfigure(
            inner_id, width=e.width))
        self.sidebar_canvas.bind('<MouseWheel>', self._scroll_sidebar)
        sidebar_body.bind('<MouseWheel>', self._scroll_sidebar)

        actions = tk.Frame(sidebar_body, bg='white', padx=12, pady=12,
                           highlightbackground='#DEE6F2', highlightthickness=1)
        actions.pack(fill='x')
        tk.Label(actions, text='Удирдлага', bg='white', fg='#15243B',
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w', pady=(0, 10))
        controls = [
            ('▶  Камер нээх', 'Blue.TButton', self.open_camera),
            ('▢  Камер хаах', 'Pale.TButton', self.close_camera),
            ('◎  Нүүр таних', 'Pale.TButton', lambda: self.change_mode('recognize')),
            ('◯  Нүүр илрүүлэх', 'Pale.TButton', lambda: self.change_mode('detect')),
            ('👥  Сурагчдын бүртгэл', 'Pale.TButton', self.open_student_manager),
            ('Excel ирцийн хавтас', 'Small.TButton', self.open_attendance),
            ('Excel шинэчлэх', 'Small.TButton', self.refresh_attendance),
            ('Өдрийн ирц дуусгах', 'Small.TButton', self.finish_attendance),
        ]
        for label, button_style, callback in controls:
            btn = ttk.Button(actions, text=label, style=button_style, command=callback)
            btn.pack(fill='x', pady=3)
            btn.bind('<MouseWheel>', self._scroll_sidebar)

        status_card = tk.Frame(sidebar_body, bg='white', padx=12, pady=12,
                               highlightbackground='#DEE6F2', highlightthickness=1)
        status_card.pack(fill='x', pady=(10, 6))
        tk.Label(status_card, text='Системийн төлөв', bg='white', fg='#15243B',
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 8))
        label = tk.Label(status_card, textvariable=self.status, bg='white', fg='#475569',
                         font=('Segoe UI', 10), wraplength=245, justify='left')
        label.pack(anchor='w')
        label.bind('<MouseWheel>', self._scroll_sidebar)

        footer = tk.Frame(self.root, bg='white', padx=22, pady=9)
        footer.pack(fill='x')
        tk.Label(footer, text='FACEVISION • Light Minimal • Excel ирц', bg='white',
                 fg='#64748B', font=('Segoe UI', 10)).pack(side='left')
        tk.Label(footer, text=f'{platform.system()} • Python • FaceNet', bg='white',
                 fg='#64748B', font=('Segoe UI', 10)).pack(side='right')

    def _scroll_sidebar(self, event):
        if getattr(event, 'delta', 0):
            self.sidebar_canvas.yview_scroll(-int(event.delta / 120), 'units')
        elif getattr(event, 'num', None) == 4:
            self.sidebar_canvas.yview_scroll(-1, 'units')
        elif getattr(event, 'num', None) == 5:
            self.sidebar_canvas.yview_scroll(1, 'units')

    def toggle_register_panel(self):
        """Registration controls live in a separate, resizable window."""
        if self.register_window is not None and self.register_window.winfo_exists():
            self.register_window.lift()
            self.register_window.focus_force()
            return
        win = tk.Toplevel(self.root)
        self.register_window = win
        win.title('FACEVISION — Нүүр бүртгэх')
        win.configure(bg='#F5F8FF')
        win.geometry('430x520')
        win.minsize(360, 460)
        win.transient(self.root)
        panel = tk.Frame(win, bg='white', padx=24, pady=22)
        panel.pack(fill='both', expand=True, padx=14, pady=14)
        tk.Label(panel, text='Шинэ сурагч бүртгэх', bg='white', fg='#13233E',
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        tk.Label(panel, text='Камерын дүрс үндсэн цонхонд харагдана.',
                 bg='white', fg='#64748B', font=('Segoe UI', 10)).pack(anchor='w', pady=(6, 16))
        tk.Label(panel, text='Сурагчийн нэр', bg='white', fg='#334155',
                 font=('Segoe UI', 11)).pack(anchor='w', pady=(0, 5))
        entry = ttk.Entry(panel, textvariable=self.name, style='Light.TEntry')
        entry.pack(fill='x', pady=(0, 15))
        for label, style_name, callback in [
            ('1. Бүртгэл эхлүүлэх', 'Blue.TButton', self.register),
            ('2. Зураг авах', 'Pale.TButton', self.take_photos),
            ('3. Алгасах', 'Small.TButton', self.skip),
            ('Зогсоох', 'Small.TButton', lambda: self.change_mode('detect')),
        ]:
            ttk.Button(panel, text=label, style=style_name,
                       command=callback).pack(fill='x', pady=4)
        tk.Label(panel, textvariable=self.status, bg='white', fg='#475569',
                 font=('Segoe UI', 10), wraplength=345, justify='left').pack(
                     anchor='w', pady=(14, 0))
        entry.focus_set()
        win.protocol('WM_DELETE_WINDOW', win.destroy)

    def open_student_manager(self):
        """View enrollment, rename a student, remove and recover face images."""
        if self.manager_window is not None and self.manager_window.winfo_exists():
            self.manager_window.lift()
            return
        win = tk.Toplevel(self.root)
        self.manager_window = win
        win.title('FACEVISION — Сурагчдын бүртгэл')
        win.geometry('650x565')
        win.minsize(510, 480)
        win.configure(bg='#F5F8FF')
        win.transient(self.root)
        body = tk.Frame(win, bg='white', padx=18, pady=16)
        body.pack(fill='both', expand=True, padx=12, pady=12)
        tk.Label(body, text='Сурагчдын бүртгэл', bg='white', fg='#13233E',
                 font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        tk.Label(body, text='Устгах үед зургууд сэргээх хавтсанд хадгалагдана.',
                 bg='white', fg='#64748B', font=('Segoe UI', 10)).pack(anchor='w', pady=(4, 10))
        tk.Label(body, text='Идэвхтэй сурагчид (нэр · зургийн тоо)', bg='white',
                 fg='#334155', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        self.student_list = tk.Listbox(body, height=7, font=('Segoe UI', 11),
                                       selectmode=tk.SINGLE, exportselection=False)
        self.student_list.pack(fill='both', expand=True, pady=(5, 9))
        actions = tk.Frame(body, bg='white')
        actions.pack(fill='x')
        for label, command in [
            ('＋ Бүртгэх', self.toggle_register_panel),
            ('Нэр солих', self.rename_selected_student),
            ('Бүртгэлээс хасах', self.remove_selected_student),
            ('Шинэчлэх', self.refresh_student_lists),
        ]:
            ttk.Button(actions, text=label, style='Small.TButton',
                       command=command).pack(side='left', padx=(0, 5))
        tk.Label(body, text='Сэргээх боломжтой бүртгэлүүд', bg='white',
                 fg='#334155', font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(14, 0))
        self.deleted_list = tk.Listbox(body, height=5, font=('Segoe UI', 10),
                                       selectmode=tk.SINGLE, exportselection=False)
        self.deleted_list.pack(fill='both', expand=True, pady=(5, 7))
        ttk.Button(body, text='↩ Сонгосон сурагчийг сэргээх', style='Pale.TButton',
                   command=self.restore_selected_student).pack(fill='x')
        self.refresh_student_lists()
        win.protocol('WM_DELETE_WINDOW', win.destroy)

    def refresh_student_lists(self):
        self.student_rows = self.student_store.active()
        self.deleted_rows = self.student_store.removed()
        if self.student_list is not None and self.student_list.winfo_exists():
            self.student_list.delete(0, 'end')
            for name, count in self.student_rows:
                self.student_list.insert('end', f'{name}    —    {count} зураг')
        if self.deleted_list is not None and self.deleted_list.winfo_exists():
            self.deleted_list.delete(0, 'end')
            for key, name, removed_at in self.deleted_rows:
                self.deleted_list.insert('end', f'{name}    —    {removed_at}')

    def _selected_student(self):
        if self.student_list is None or not self.student_list.curselection():
            messagebox.showwarning('Сурагч', 'Эхлээд жагсаалтаас сурагч сонгоно уу.')
            return None
        return self.student_rows[self.student_list.curselection()[0]][0]

    def _ready_to_change_students(self):
        if self.busy or self.mode == 'register':
            messagebox.showwarning('Сурагч', 'Бүртгэл/танилт боловсруулж дууссаны дараа өөрчилнө үү.')
            return False
        return True

    def _on_student_data_changed(self, message):
        self.session += 1
        self.tracker.reset()
        self.known = {}
        self.mode = 'detect'
        self.results = []
        self.capture_time = None
        self.attendance.roster(self.student_store.names())
        self.refresh_student_lists()
        self.status.set(message + ' · Нүүр таних горимыг дахин сонгоорой.')

    def rename_selected_student(self):
        name = self._selected_student()
        if name is None or not self._ready_to_change_students():
            return
        new_name = simpledialog.askstring('Нэр солих', 'Шинэ нэр:',
                                           initialvalue=name, parent=self.manager_window)
        if new_name is None:
            return
        new_name = new_name.strip()
        if not valid_name(new_name):
            messagebox.showwarning('Нэр', 'Нэр үсэг, тоо, _ эсвэл - агуулна (40 хүртэл).')
            return
        try:
            self.student_store.rename(name, new_name)
            self.attendance.rename_student(name, new_name, self.student_store.names())
            self._on_student_data_changed(f'{name} → {new_name}: нэр өөрчлөгдлөө')
        except (ValueError, FileExistsError, OSError) as error:
            messagebox.showerror('Нэр солих', str(error))

    def remove_selected_student(self):
        name = self._selected_student()
        if name is None or not self._ready_to_change_students():
            return
        if not messagebox.askyesno('Бүртгэлээс хасах',
                f'"{name}" сурагчийг таних системээс хасах уу?\n'
                'Зургуудыг deleted_students хавтсанд нөөцлөөд сэргээж болно.',
                parent=self.manager_window):
            return
        try:
            self.student_store.remove(name)
            self._on_student_data_changed(f'{name}: идэвхтэй бүртгэлээс хасагдлаа')
        except (ValueError, FileNotFoundError, OSError) as error:
            messagebox.showerror('Бүртгэлээс хасах', str(error))

    def restore_selected_student(self):
        if self.deleted_list is None or not self.deleted_list.curselection():
            messagebox.showwarning('Сэргээх', 'Доод жагсаалтаас сурагч сонгоно уу.')
            return
        if not self._ready_to_change_students():
            return
        key = self.deleted_rows[self.deleted_list.curselection()[0]][0]
        try:
            name = self.student_store.restore(key)
            self._on_student_data_changed(f'{name}: бүртгэл сэргээгдлээ')
        except (FileNotFoundError, FileExistsError, ValueError, OSError) as error:
            messagebox.showerror('Сэргээх', str(error))

    def refresh_attendance(self):
        self.attendance.roster(self.student_store.names())
        self.attendance.resync()
        self.status.set('Excel ирц шинэчлэгдэж байна...')

    def open_attendance(self):
        try:
            open_attendance_folder(DATASET)
        except Exception as error:
            messagebox.showerror('Excel ирц', str(error))

    def finish_attendance(self):
        if not self.student_store.names():
            messagebox.showwarning('Ирц', 'Бүртгэлтэй сурагч алга байна.')
            return
        if messagebox.askyesno('Өдрийн ирц',
                               'Өнөөдрийн ирцийг дуусгах уу? Ирж амжаагүй сурагчид улаанаар тэмдэглэгдэнэ.'):
            self.attendance.finish_day(self.student_store.names())
            self.status.set('Excel ирцийг дуусгаж байна...')

    def open_camera(self):
        if self._exiting or self.running:
            return
        if self.stream is not None and self.stream.alive:
            # Do not open the webcam twice; reopen as soon as the old worker exits.
            self.status.set('Камер хаагдаж байна. Дуусмагц автоматаар нээнэ...')
            if self.camera_restart_job is None:
                self.camera_restart_job = self.root.after(180, self._finish_camera_restart)
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

    def _finish_camera_restart(self):
        self.camera_restart_job = None
        if not self._exiting:
            self.open_camera()

    def schedule_update(self, delay_ms):
        if self.running and self.update_job is None:
            self.update_job = self.root.after(delay_ms, self.update)

    def close_camera(self):
        if self.camera_restart_job is not None:
            self.root.after_cancel(self.camera_restart_job)
            self.camera_restart_job = None
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
        # First run computes FaceNet embeddings; later runs reuse unchanged photos.
        return FaceEmbeddingCache(DATASET, self.embedding).load_people()

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
                    self.attendance.roster(self.student_store.names())
                    self.status.set(f'Танихад бэлэн: {len(value)} хүн')
                elif kind == 'recognize' and self.mode == 'recognize':
                    names = self.tracker.apply(value, captured_at, time.monotonic())
                    if names:
                        for confirmed_name in names:
                            if confirmed_name in self.known:
                                self.attendance.present(confirmed_name, self.known.keys())
                        self.status.set('Танигдсан: ' + ', '.join(names) + ' · Ирц хадгалж байна...')
        except queue.Empty:
            pass
        try:
            while True:
                level, message = self.attendance.messages.get_nowait()
                self.status.set(message)
        except queue.Empty:
            pass
        if not self._exiting:
            self._poll_job = self.root.after(60, self.poll)

    def register(self):
        if self.busy:
            messagebox.showwarning('Түр хүлээнэ үү', 'Нүүр таних мэдээлэл ачаалж дууссаны дараа бүртгээрэй.')
            return
        name = self.name.get().strip()
        if not valid_name(name):
            messagebox.showwarning('Нэр', 'Зөв нэр оруулна уу (үсэг, тоо, _ эсвэл -).')
            return
        if not self.running:
            messagebox.showwarning('Камер', 'Эхлээд камер нээнэ үү.')
            return
        self.session += 1
        self.tracker.reset()
        self.results = []
        for existing in self.student_store.names():
            if existing.casefold() == name.casefold():
                if existing != name:
                    messagebox.showwarning('Нэр давхцлаа',
                        f'"{existing}" нэртэй сурагч байна. Ижил нэрийг дахин үүсгэхгүй.')
                    return
                if not messagebox.askyesno('Нэмэлт зураг',
                        f'"{existing}" өмнө нь бүртгэлтэй. Нэмэлт зураг авах уу?'):
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
        if self.stage == len(STAGES):
            self.attendance.roster(self.student_store.names())
            if self.manager_window is not None and self.manager_window.winfo_exists():
                self.refresh_student_lists()
            if self.total:
                self.session += 1
                self.tracker.reset()
                self.mode = 'recognize'
                self.known = {}
                self.status.set(f'{self.person}: {self.total} зураг хадгаллаа. Таних мэдээлэл шинэчилж байна...')
                self.background('load', self.load_people)
            else:
                self.mode = 'detect'
                self.status.set('Зураг хадгалагдаагүй. Бүртгэл дууслаа.')
        else:
            self.status.set(STAGES[self.stage] + ' — Зураг авах дарна уу')

    def save_photo(self, crop):
        folder = DATASET / self.person
        folder.mkdir(parents=True, exist_ok=True)
        i = 1
        while (folder / f'{self.person}_new_{i}.jpg').exists():
            i += 1
        path = folder / f'{self.person}_new_{i}.jpg'
        try:
            ok, encoded = cv2.imencode('.jpg', crop)
            if ok:
                encoded.tofile(str(path))  # Unicode paths on Windows.
                return True
        except (OSError, cv2.error) as error:
            self.status.set('Зураг хадгалах алдаа: ' + str(error))
        return False

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
        unicode_labels = []
        for person in visible:
            x1,y1,x2,y2 = person.display_box
            label, color = 'Face Detected', (0, 200, 255)
            if self.mode == 'register':
                label = STAGES[self.stage]
            elif self.mode == 'recognize':
                label, color = person.label()
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            if label.isascii():
                cv2.putText(frame, label, (x1,max(25,y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            else:
                unicode_labels.append((label, x1, max(3, y1-27), (color[2], color[1], color[0])))
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if unicode_labels:
            try:
                fonts = ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
                font_file = next((path for path in fonts if Path(path).exists()), None)
                font = ImageFont.truetype(font_file, 20) if font_file else ImageFont.load_default()
                draw = ImageDraw.Draw(img)
                for label, x, y, color in unicode_labels:
                    draw.text((x, y), label, fill=color, font=font, stroke_width=1,
                              stroke_fill=(10, 15, 25))
            except (OSError, UnicodeError):
                pass
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
        self._exiting = True
        self.close_camera()
        if self._poll_job is not None:
            self.root.after_cancel(self._poll_job)
            self._poll_job = None
        self.attendance.close()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
