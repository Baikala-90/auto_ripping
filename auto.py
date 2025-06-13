import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CONFIG_FILE = 'config.json'

class JDFGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to JDF 자동 변환기")
        self.rules = []

        self.load_config()
        self.create_widgets()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.rules = config.get('conditions', [])
        else:
            self.rules = []

    def save_config(self):
        config = {'conditions': self.rules}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def create_widgets(self):
        frm = tk.Frame(self.root)
        frm.pack(padx=10, pady=10)

        self.rule_entries = {}

        # 조건 입력 필드
        self.key_entry = tk.Entry(frm)
        self.key_entry.grid(row=0, column=0)
        self.val_entry = tk.Entry(frm)
        self.val_entry.grid(row=0, column=1)

        tk.Button(frm, text="조건 추가", command=self.add_condition).grid(row=0, column=2, padx=5)

        # 템플릿 선택
        tk.Button(frm, text="템플릿 선택", command=self.select_template).grid(row=1, column=0, pady=5)
        self.template_path = tk.StringVar()
        tk.Label(frm, textvariable=self.template_path).grid(row=1, column=1, columnspan=2, sticky="w")

        # 등록 버튼
        tk.Button(frm, text="조건 조합 등록", command=self.register_condition).grid(row=2, column=0, columnspan=3, pady=10)

        # 조건 리스트
        self.tree = ttk.Treeview(frm, columns=("keyvals", "template"), show="headings")
        self.tree.heading("keyvals", text="조건")
        self.tree.heading("template", text="템플릿 경로")
        self.tree.grid(row=3, column=0, columnspan=3)

        self.refresh_tree()

    def add_condition(self):
        key = self.key_entry.get().strip()
        val = self.val_entry.get().strip()
        if not key or not val:
            messagebox.showwarning("입력 오류", "조건 키와 값을 모두 입력하세요.")
            return
        if key not in self.rule_entries:
            self.rule_entries[key] = []
        self.rule_entries[key].append(val)
        self.key_entry.delete(0, tk.END)
        self.val_entry.delete(0, tk.END)
        messagebox.showinfo("조건 추가됨", f"{key}: {val} 조건이 추가되었습니다.")

    def select_template(self):
        path = filedialog.askopenfilename(filetypes=[("JDF Files", "*.jdf")])
        if path:
            self.template_path.set(path)

    def register_condition(self):
        if not self.template_path.get():
            messagebox.showwarning("템플릿 누락", "템플릿 파일을 선택하세요.")
            return
        combined = {
            'rules': {k: v[-1] for k, v in self.rule_entries.items()},
            'template': self.template_path.get()
        }
        self.rules.append(combined)
        self.save_config()
        self.rule_entries.clear()
        self.template_path.set("")
        self.refresh_tree()
        messagebox.showinfo("등록 완료", "조건 조합이 저장되었습니다.")

    def refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for rule in self.rules:
            rule_str = ", ".join(f"{k}:{v}" for k, v in rule['rules'].items())
            self.tree.insert('', 'end', values=(rule_str, rule['template']))


if __name__ == '__main__':
    root = tk.Tk()
    app = JDFGeneratorApp(root)
    root.mainloop()
