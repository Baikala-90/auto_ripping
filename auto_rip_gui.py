import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import threading
import auto_rip_executor as executor
import main

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
        self.folder_buttons = {}
        self.progress_bars = {}
        self.status_labels = {}
        self.time_labels = {}

        self.pdf_source = ""
        self.pdf_dest = ""
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
        setting_menu.add_command(label="PDF 복사 경로 설정", command=self.set_pdf_source)
        setting_menu.add_command(label="PDF 저장 경로 설정", command=self.set_pdf_destination)
        menu.add_cascade(label="설정", menu=setting_menu)
        menu.add_command(label="발주서 업로드", command=self.upload_order)
        menu.add_command(label="PDF 복사", command=self.copy_pdfs)
        self.master.config(menu=menu)

    def toggle_all_auto(self, state):
        for folder in self.folder_names:
            self.auto_trigger[folder].set(1 if state else 0)

    def upload_order(self):
        file_path = filedialog.askopenfilename(
            title="발주서 선택", filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not file_path:
            return
        try:
            os.makedirs(main.UPLOAD_FOLDER, exist_ok=True)
            for f in os.listdir(main.UPLOAD_FOLDER):
                if f.lower().endswith((".xls", ".xlsx")):
                    try:
                        os.remove(os.path.join(main.UPLOAD_FOLDER, f))
                    except Exception:
                        pass
            dest_path = os.path.join(main.UPLOAD_FOLDER, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)
            messagebox.showinfo("업로드 완료", f"{dest_path} 에 저장했습니다.")
            main.main()
            messagebox.showinfo("완료", "JDF 파일 생성이 완료되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"업로드 실패: {e}")

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

        save_btn = tk.Button(self.master, text="\U0001f504 설정 저장", command=self.save_config)
        save_btn.grid(row=len(self.folder_names), column=0, pady=10)

        run_btn = tk.Button(self.master, text="▶️ 전체 전송 시작", command=self.run_all_folders_thread)
        run_btn.grid(row=len(self.folder_names) + 1, column=0, pady=5)

        pause_btn = tk.Button(self.master, text="⏸ 전체 일시정지", command=self.toggle_global_pause)
        pause_btn.grid(row=len(self.folder_names) + 2, column=0, pady=5)

        refresh_btn = tk.Button(self.master, text="\U0001f504 수량 새로고침", command=self.update_file_counts)
        refresh_btn.grid(row=len(self.folder_names) + 3, column=0, pady=5)

        self.log_text = tk.Text(self.master, height=10, width=90, bg="#f2f2f2")
        self.log_text.grid(row=len(self.folder_names) + 4, column=0, padx=5, pady=5)

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
        if folder in self.threads and self.threads[folder].is_alive():
            self.pause_flags[folder].clear()
            self.append_log(f"⏸ {folder} 일시정지됨")
        else:
            self.pause_flags[folder].set()
            t = threading.Thread(target=self.send_single_folder, args=(folder,))
            self.threads[folder] = t
            t.start()

    def send_single_folder(self, folder):
        self.append_log(f"📦 {folder} 전송 시작")
        executor.start_auto_transfer(
            base_folder=self.base_folder,
            folder_names=[folder],
            hotfolder_paths=self.hotfolder_paths,
            auto_trigger={folder: self.auto_trigger.get(folder, False)},
            log_callback=self.append_log,
            sort_orders={folder: self.sort_orders[folder].get()},
            pause_flag=self.pause_flags_global,
            folder_stop=self.folder_stop
        )
        self.update_file_counts()

    def append_log(self, message):
        def update_text():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.master.after(0, update_text)

    def set_hotfolder(self, folder):
        selected = filedialog.askdirectory(title=f"'{folder}'의 HOTFOLDER 선택")
        if selected:
            self.hotfolder_paths[folder] = selected
            self.check_vars[folder].config(text=selected)
            messagebox.showinfo("경로 설정 완료", f"{folder} 의 HOTFOLDER를 설정했습니다.")

    def set_pdf_source(self):
        selected = filedialog.askdirectory(title="PDF 복사 경로 선택")
        if selected:
            self.pdf_source = selected
            messagebox.showinfo("설정 완료", "PDF 복사 경로가 설정되었습니다.")

    def set_pdf_destination(self):
        selected = filedialog.askdirectory(title="PDF 저장 경로 선택")
        if selected:
            self.pdf_dest = selected
            messagebox.showinfo("설정 완료", "PDF 저장 경로가 설정되었습니다.")

    def copy_pdfs(self):
        if not self.pdf_source or not self.pdf_dest:
            messagebox.showwarning("경로 미설정", "PDF 복사 경로와 저장 경로를 먼저 설정하세요.")
            return
        try:
            for root_dir, dirs, files in os.walk(self.pdf_source):
                rel = os.path.relpath(root_dir, self.pdf_source)
                dest_dir = os.path.join(self.pdf_dest, rel)
                os.makedirs(dest_dir, exist_ok=True)
                for f in files:
                    if f.lower().endswith('.pdf'):
                        shutil.copy2(os.path.join(root_dir, f), os.path.join(dest_dir, f))
            messagebox.showinfo("완료", "PDF 파일 복사가 완료되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"PDF 복사 실패: {e}")

    def load_config(self):
        self.hotfolder_configs = {}
        config_path = os.path.join(self.base_folder, "hotfolder_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.hotfolder_configs = {k: v for k, v in data.items() if k in self.folder_names}
            self.pdf_source = data.get("pdf_source", "")
            self.pdf_dest = data.get("pdf_dest", "")

    def save_config(self):
        config = {}
        for folder in self.folder_names:
            config[folder] = {
                "hotfolder": self.hotfolder_paths.get(folder, self.DEFAULT_HOTFOLDER),
                "auto": bool(self.auto_trigger[folder].get())
            }
        config["pdf_source"] = self.pdf_source
        config["pdf_dest"] = self.pdf_dest
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
