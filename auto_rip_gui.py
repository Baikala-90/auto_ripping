import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import threading
import auto_rip_executor as executor

class HotFolderManager:
    DEFAULT_HOTFOLDER = r"\\Oc-nblbmmdl7gpq\123"
    SORT_ORDER_FILE = "folder_sort_order.json"

    def __init__(self, master):
        self.master = master
        self.master.title("자동 립핑 핫폴더 매니저")

        self.base_folder = r"C:\\제작폴더\\@자동립핑"
        self.folder_names = [
            "면지 결과파일_컬날46", "면지 결과파일_컬날A5", "면지 결과파일_컬날B5",
            "면지 결과파일_컬단46", "면지 결과파일_컬단A4", "면지 결과파일_컬단A5", "면지 결과파일_컬단B5",
            "면지 결과파일_흑날46", "면지 결과파일_흑날A5", "면지 결과파일_흑날B5",
            "면지 결과파일_흑단46", "면지 결과파일_흑단A4", "면지 결과파일_흑단A5", "면지 결과파일_흑단B5",
            "표지검사_정상"
        ]
        self.hotfolder_paths = {}
        self.check_vars = {}
        self.auto_trigger = {}
        self.file_count_labels = {}
        self.sort_orders = {}
        self.pause_flags = {folder: threading.Event() for folder in self.folder_names}
        self.pause_flags_global = threading.Event()
        self.pause_flags_global.set()
        self.folder_stop = {"stop": False}
        self.threads = {}
        self.status_items = {}
        self.folder_buttons = {}
        self.progress_bars = {}

        self.remaining_label = None

        self.load_config()
        self.load_sort_order()
        self.build_menu()
        self.build_ui()

    def build_menu(self):
        menu = tk.Menu(self.master)
        setting_menu = tk.Menu(menu, tearoff=0)
        setting_menu.add_command(label="전체 자동 전송 켜기", command=lambda: self.toggle_all_auto(True))
        setting_menu.add_command(label="전체 자동 전송 끄기", command=lambda: self.toggle_all_auto(False))
        setting_menu.add_command(label="\U0001f504 수량 새로고침", command=self.update_file_counts)
        menu.add_cascade(label="설정", menu=setting_menu)
        self.master.config(menu=menu)

    def toggle_all_auto(self, state):
        for folder in self.folder_names:
            self.auto_trigger[folder].set(1 if state else 0)

    def build_ui(self):
        for idx, folder in enumerate(self.folder_names):
            full_path = os.path.join(self.base_folder, folder)
            os.makedirs(full_path, exist_ok=True)

            frame = tk.Frame(self.master)
            frame.grid(row=idx, column=0, sticky='w', pady=2)

            label = tk.Label(frame, text=folder, width=25, anchor='w')
            label.pack(side=tk.LEFT)

            btn = tk.Button(frame, text="\U0001f517 경로 설정", command=lambda f=folder: self.set_hotfolder(f))
            btn.pack(side=tk.LEFT, padx=5)

            default_path = self.hotfolder_configs.get(folder, {}).get("hotfolder", self.DEFAULT_HOTFOLDER)
            self.hotfolder_paths[folder] = default_path
            path_label = tk.Label(frame, text=default_path, width=40, anchor='w', fg='gray')
            path_label.pack(side=tk.LEFT)
            self.check_vars[folder] = path_label

            auto = tk.IntVar(value=1 if self.hotfolder_configs.get(folder, {}).get("auto") else 0)
            self.auto_trigger[folder] = auto
            auto_check = tk.Checkbutton(frame, text="자동 전송", variable=auto)
            auto_check.pack(side=tk.LEFT, padx=5)

            jdf_pdf_label = tk.Label(frame, text="", width=20)
            jdf_pdf_label.pack(side=tk.LEFT)
            self.file_count_labels[folder] = jdf_pdf_label

            self.sort_orders[folder] = tk.StringVar(value=self.sort_orders.get(folder, "오름차순"))
            sort_menu = tk.OptionMenu(frame, self.sort_orders[folder], "오름차순", "내림차순")
            sort_menu.pack(side=tk.LEFT, padx=3)

            send_btn = tk.Button(frame, text="▶️", command=lambda f=folder: self.toggle_folder_execution(f))
            send_btn.pack(side=tk.LEFT, padx=5)
            self.folder_buttons[folder] = send_btn

            bar = ttk.Progressbar(frame, length=100)
            bar.pack(side=tk.LEFT, padx=5)
            self.progress_bars[folder] = bar

        save_btn = tk.Button(self.master, text="\U0001f504 설정 저장", command=self.save_config)
        save_btn.grid(row=len(self.folder_names), column=0, pady=10)

        run_btn = tk.Button(self.master, text="▶️ 전체 전송 시작", command=self.run_all_folders_thread)
        run_btn.grid(row=len(self.folder_names) + 1, column=0, pady=5)

        pause_btn = tk.Button(self.master, text="⏸ 전체 일시정지", command=self.toggle_global_pause)
        pause_btn.grid(row=len(self.folder_names) + 2, column=0, pady=5)

        refresh_btn = tk.Button(self.master, text="\U0001f504 수량 새로고침", command=self.update_file_counts)
        refresh_btn.grid(row=len(self.folder_names) + 3, column=0, pady=5)

        self.tree = ttk.Treeview(self.master, columns=("folder", "status"), show="headings")
        self.tree.heading("folder", text="폴더")
        self.tree.heading("status", text="상태")
        for f in self.folder_names:
            item = self.tree.insert("", tk.END, values=(f, "대기"))
            self.status_items[f] = item

        self.tree.tag_configure("running", background="#ffeeba")
        self.tree.grid(row=len(self.folder_names) + 4, column=0, padx=5, pady=5)

        self.remaining_label = tk.Label(self.master, text="예상 남은 시간: -")
        self.remaining_label.grid(row=len(self.folder_names) + 5, column=0, pady=2)

        self.log_text = tk.Text(self.master, height=10, width=90, bg="#f2f2f2")
        self.log_text.grid(row=len(self.folder_names) + 6, column=0, padx=5, pady=5)

        self.update_file_counts()

    def run_all_folders_thread(self):
        for folder in self.folder_names:
            if folder not in self.threads or not self.threads[folder].is_alive():
                self.toggle_folder_execution(folder)

    def toggle_global_pause(self):
        if self.pause_flags_global.is_set():
            self.pause_flags_global.clear()
            self.append_log("⏸ 전체 일시정지 됨")
        else:
            self.pause_flags_global.set()
            self.append_log("▶️ 전체 재시작됨")

    def toggle_folder_execution(self, folder):
        btn = self.folder_buttons.get(folder)
        if folder in self.threads and self.threads[folder].is_alive():
            if self.pause_flags[folder].is_set():
                self.pause_flags[folder].clear()
                if btn:
                    btn.config(text="▶️")
                self.append_log(f"⏸ {folder} 일시정지됨")
                self.update_status(folder, "일시정지")
            else:
                self.pause_flags[folder].set()
                if btn:
                    btn.config(text="⏸")
                self.append_log(f"▶️ {folder} 재시작됨")
                self.update_status(folder, "전송 중")
        else:
            self.pause_flags[folder].set()
            if btn:
                btn.config(text="⏸")
            t = threading.Thread(target=self.send_single_folder, args=(folder,))
            self.threads[folder] = t
            t.start()

    def send_single_folder(self, folder):
        self.append_log(f"📦 {folder} 전송 시작")
        self.update_status(folder, "전송 중")
        executor.start_auto_transfer(
            base_folder=self.base_folder,
            folder_names=[folder],
            hotfolder_paths=self.hotfolder_paths,
            auto_trigger={folder: self.auto_trigger.get(folder, False)},
            log_callback=self.append_log,
            sort_orders={folder: self.sort_orders[folder].get()},
            pause_flag=self.pause_flags_global,
            folder_stop=self.folder_stop,
            status_callback=self.update_status,
            folder_pause_flag=self.pause_flags[folder]
        )
        self.update_file_counts()
        btn = self.folder_buttons.get(folder)
        if btn:
            btn.config(text="▶️")

    def append_log(self, message):
        def update_text():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.master.after(0, update_text)

    def update_status(self, folder, status, progress=None, remaining=None):
        def _update():
            item = self.status_items.get(folder)
            if item:
                self.tree.set(item, "status", status)
                if "전송 중" in status:
                    self.tree.item(item, tags=("running",))
                else:
                    self.tree.item(item, tags=())
            bar = self.progress_bars.get(folder)
            if bar is not None and progress is not None:
                bar['value'] = progress
            if remaining is not None and self.remaining_label:
                mins = remaining // 60
                secs = remaining % 60
                self.remaining_label.config(text=f"예상 남은 시간: {mins}분 {secs}초")
        self.master.after(0, _update)

    def set_hotfolder(self, folder):
        selected = filedialog.askdirectory(title=f"{folder}의 HOTFOLDER 선택")
        if selected:
            self.hotfolder_paths[folder] = selected
            self.check_vars[folder].config(text=selected)
            messagebox.showinfo("경로 설정 완료", f"{folder} 의 HOTFOLDER를 설정했습니다.")

    def load_config(self):
        self.hotfolder_configs = {}
        config_path = os.path.join(self.base_folder, "hotfolder_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.hotfolder_configs = json.load(f)

    def save_config(self):
        config = {}
        for folder in self.folder_names:
            config[folder] = {
                "hotfolder": self.hotfolder_paths.get(folder, self.DEFAULT_HOTFOLDER),
                "auto": bool(self.auto_trigger[folder].get())
            }
        config_path = os.path.join(self.base_folder, "hotfolder_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        sort_order_path = os.path.join(self.base_folder, self.SORT_ORDER_FILE)
        with open(sort_order_path, "w", encoding="utf-8") as f:
            json.dump({f: self.sort_orders[f].get() for f in self.folder_names}, f, indent=4, ensure_ascii=False)

        messagebox.showinfo("저장 완료", f"설정이 저장되었습니다:\n{config_path}\n정렬 설정 저장됨: {sort_order_path}")

    def load_sort_order(self):
        sort_order_path = os.path.join(self.base_folder, self.SORT_ORDER_FILE)
        if os.path.exists(sort_order_path):
            with open(sort_order_path, "r", encoding="utf-8") as f:
                self.sort_orders = json.load(f)

    def update_file_counts(self):
        for folder in self.folder_names:
            folder_path = os.path.join(self.base_folder, folder)
            jdf_count = len([f for f in os.listdir(folder_path) if f.lower().endswith(".jdf")])
            pdf_count = len([f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")])
            label = self.file_count_labels[folder]
            label.config(text=f"JDF: {jdf_count} | PDF: {pdf_count}")

if __name__ == "__main__":
    root = tk.Tk()
    app = HotFolderManager(root)
    root.mainloop()
