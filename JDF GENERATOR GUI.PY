
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CONFIG_FILE = "config.json"

class TemplateManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.templates = self.load_templates()

    def load_templates(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_templates(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)

    def add_template(self, key, data):
        self.templates[key] = data
        self.save_templates()

    def delete_template(self, key):
        if key in self.templates:
            del self.templates[key]
            self.save_templates()

    def update_template(self, key, new_data):
        self.templates[key] = new_data
        self.save_templates()

    def copy_template(self, key):
        if key in self.templates:
            count = 1
            new_key = f"{key}_복사본"
            while new_key in self.templates:
                count += 1
                new_key = f"{key}_복사본{count}"
            self.templates[new_key] = self.templates[key].copy()
            self.save_templates()
            return new_key
        return None

class TemplateGUI:
    def __init__(self, root, manager):
        self.manager = manager
        self.root = root
        self.root.title("JDF 템플릿 관리자")

        self.entries = {}

        frame = tk.Frame(root)
        frame.pack(pady=10)

        for idx, label in enumerate(["규격", "제본", "표지재질", "내지재질", "내지형식"]):
            tk.Label(frame, text=label).grid(row=0, column=idx)
            entry = tk.Entry(frame, width=12)
            entry.grid(row=1, column=idx)
            self.entries[label] = entry

        tk.Label(frame, text="JDF 템플릿 파일").grid(row=0, column=5)
        self.file_entry = tk.Entry(frame, width=60)  # 경로 넓이 확장
        self.file_entry.grid(row=1, column=5)
        tk.Button(frame, text="파일 선택", command=self.browse_file).grid(row=1, column=6)

        tk.Label(frame, text="치환 패턴").grid(row=2, column=0)
        self.pattern_entry = tk.Entry(frame, width=20)
        self.pattern_entry.insert(0, "@@COPIES@@")
        self.pattern_entry.grid(row=2, column=1, columnspan=2)

        tk.Label(frame, text="치환 방식").grid(row=2, column=3)
        self.replace_method = ttk.Combobox(frame, values=["attribute", "tag"], width=15)
        self.replace_method.current(0)
        self.replace_method.grid(row=2, column=4)

        tk.Button(frame, text="템플릿 추가", command=self.add_template).grid(row=2, column=5)

        self.listbox = tk.Listbox(root, width=100)
        self.listbox.pack(pady=10)
        self.listbox.bind("<<ListboxSelect>>", self.load_selected_template)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="선택 수정", command=self.modify_template).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="선택 삭제", command=self.delete_template).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="선택 복사", command=self.copy_template).grid(row=0, column=2, padx=5)

        self.refresh_listbox()

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JDF Files", "*.jdf")])
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)

    def get_key(self):
        return "_".join(self.entries[label].get().strip() for label in ["규격", "제본", "표지재질", "내지재질", "내지형식"])

    def get_data(self):
        return {
            "file": self.file_entry.get(),
            "pattern": self.pattern_entry.get(),
            "method": self.replace_method.get()
        }

    def add_template(self):
        key = self.get_key()
        data = self.get_data()
        if key and data["file"]:
            self.manager.add_template(key, data)
            self.refresh_listbox()

    def modify_template(self):
        selection = self.listbox.curselection()
        if selection:
            key = self.listbox.get(selection[0])
            new_key = self.get_key()
            new_data = self.get_data()
            if key != new_key:
                self.manager.delete_template(key)
            self.manager.update_template(new_key, new_data)
            self.refresh_listbox()

    def delete_template(self):
        selection = self.listbox.curselection()
        if selection:
            key = self.listbox.get(selection[0])
            self.manager.delete_template(key)
            self.refresh_listbox()

    def copy_template(self):
        selection = self.listbox.curselection()
        if selection:
            key = self.listbox.get(selection[0])
            new_key = self.manager.copy_template(key)
            if new_key:
                self.refresh_listbox()

    def load_selected_template(self, event):
        selection = self.listbox.curselection()
        if selection:
            key = self.listbox.get(selection[0])
            values = key.split("_")
            for i, label in enumerate(["규격", "제본", "표지재질", "내지재질", "내지형식"]):
                self.entries[label].delete(0, tk.END)
                if i < len(values):
                    self.entries[label].insert(0, values[i])

            data = self.manager.templates[key]
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, data.get("file", ""))
            self.pattern_entry.delete(0, tk.END)
            self.pattern_entry.insert(0, data.get("pattern", "@@COPIES@@"))
            self.replace_method.set(data.get("method", "attribute"))

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for key in sorted(self.manager.templates):
            self.listbox.insert(tk.END, key)

if __name__ == "__main__":
    root = tk.Tk()
    manager = TemplateManager(CONFIG_FILE)
    app = TemplateGUI(root, manager)
    root.mainloop()
