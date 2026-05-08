"""
画像ファイル一括リネームツール
ドラッグ＆ドロップで画像を追加し、指定ファイル名+連番でリネーム（作成日時の古い順）
"""

import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# tkinterdnd2 が使えればD&D対応、なければファイル選択ダイアログで代替
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tiff",
    ".tif",
    ".svg",
    ".heic",
    ".heif",
    ".avif",
}


def get_creation_time(filepath):
    """ファイルの作成日時を取得（Windows: st_ctime）"""
    stat = os.stat(filepath)
    return stat.st_ctime


class ImageRenamer:
    def __init__(self):
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("画像一括リネーム")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        self.files = []  # [(filepath, creation_time), ...]
        self.topmost = False

        self._build_ui()

    def _build_ui(self):
        # --- ファイル名入力エリア ---
        name_frame = ttk.Frame(self.root, padding=10)
        name_frame.pack(fill=tk.X)

        ttk.Label(name_frame, text="ファイル名:", font=("", 14)).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(name_frame, font=("", 14))
        self.name_entry.pack(side=tk.LEFT, padx=(5, 10), fill=tk.X, expand=True)
        self.name_entry.insert(0, "image")
        self.name_entry.bind("<Return>", lambda e: self._execute_rename())

        ttk.Label(name_frame, text="桁数:", font=("", 14)).pack(side=tk.LEFT)
        self.digits_var = tk.StringVar(value="3")
        digits_spin = ttk.Spinbox(
            name_frame,
            from_=1,
            to=6,
            width=3,
            textvariable=self.digits_var,
            font=("", 14),
        )
        digits_spin.pack(side=tk.LEFT, padx=(5, 10))

        ttk.Button(
            name_frame,
            text="リネーム実行",
            style="Big.TButton",
            command=self._execute_rename,
        ).pack(side=tk.LEFT)

        # --- ドロップエリア / ファイル選択ボタン ---
        drop_frame = ttk.LabelFrame(
            self.root,
            text="画像ファイル（ドラッグ＆ドロップまたはボタンで追加）",
            padding=10,
        )
        drop_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 作成日時チェックボックス（右上）
        opt_frame = ttk.Frame(drop_frame)
        opt_frame.pack(fill=tk.X, anchor=tk.E)
        self.show_created_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opt_frame,
            text="作成日時を表示",
            variable=self.show_created_var,
            command=self._toggle_created,
        ).pack(side=tk.RIGHT)

        # ファイルリスト
        list_frame = ttk.Frame(drop_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        style.configure("Treeview", font=("", 12), rowheight=28)
        style.configure("Treeview.Heading", font=("", 12, "bold"))
        style.configure("Big.TButton", font=("", 12), padding=6)

        columns = ("no", "filename", "created", "new_name")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=0)
        self.tree.heading("no", text="#")
        self.tree.heading("filename", text="元ファイル名")
        self.tree.heading("created", text="作成日時")
        self.tree.heading("new_name", text="リネーム後")
        self.tree.column("no", width=40, stretch=False)
        self.tree.column("filename", width=300)
        self.tree.column("created", width=0, stretch=False, minwidth=0)
        self.tree.column("new_name", width=200)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # D&D登録
        if HAS_DND:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", self._on_drop)

        # --- ボタンエリア ---
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="ファイル追加", style="Big.TButton", command=self._add_files
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="クリア", style="Big.TButton", command=self._clear_files
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="プレビュー更新",
            style="Big.TButton",
            command=self._update_preview,
        ).pack(side=tk.LEFT, padx=5)

        self.topmost_btn = ttk.Button(
            btn_frame,
            text="最前面: OFF",
            style="Big.TButton",
            command=self._toggle_topmost,
        )
        self.topmost_btn.pack(side=tk.RIGHT, padx=5)

        # --- ステータスバー ---
        self.status_var = tk.StringVar(
            value="画像ファイルをドラッグ＆ドロップしてください"
            if HAS_DND
            else "「ファイル追加」ボタンから画像を選択してください"
        )
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            padding=5,
            font=("", 11),
        ).pack(fill=tk.X, side=tk.BOTTOM)

    def _toggle_created(self):
        if self.show_created_var.get():
            self.tree.column("created", width=150, stretch=True, minwidth=50)
        else:
            self.tree.column("created", width=0, stretch=False, minwidth=0)

    def _toggle_topmost(self):
        self.topmost = not self.topmost
        self.root.attributes("-topmost", self.topmost)
        self.topmost_btn.config(text=f"最前面: {'ON' if self.topmost else 'OFF'}")

    def _parse_dropped_data(self, data):
        """D&Dデータからファイルパスのリストを取得"""
        paths = []
        in_brace = False
        current = []
        for char in data:
            if char == "{":
                in_brace = True
            elif char == "}":
                in_brace = False
                paths.append("".join(current))
                current = []
            elif char == " " and not in_brace:
                if current:
                    paths.append("".join(current))
                    current = []
            else:
                current.append(char)
        if current:
            paths.append("".join(current))
        return paths

    def _on_drop(self, event):
        paths = self._parse_dropped_data(event.data)
        self._add_paths(paths)

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="画像ファイルを選択",
            filetypes=[
                ("画像ファイル", " ".join(f"*{ext}" for ext in IMAGE_EXTENSIONS)),
                ("すべて", "*.*"),
            ],
        )
        if paths:
            self._add_paths(paths)

    def _add_paths(self, paths):
        existing = {f[0] for f in self.files}
        added = 0
        for p in paths:
            p = os.path.normpath(p)
            if p in existing:
                continue
            ext = os.path.splitext(p)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            if not os.path.isfile(p):
                continue
            ctime = get_creation_time(p)
            self.files.append((p, ctime))
            existing.add(p)
            added += 1

        if added:
            self.files.sort(key=lambda x: x[1])
            self._update_preview()
            self.status_var.set(f"{added}件追加 / 合計{len(self.files)}件")
        else:
            self.status_var.set("追加できる画像ファイルがありませんでした")

    def _clear_files(self):
        self.files.clear()
        self.tree.delete(*self.tree.get_children())
        self.status_var.set("クリアしました")

    def _get_new_names(self):
        """リネーム後のファイル名リストを生成"""
        base_name = self.name_entry.get().strip()
        if not base_name:
            base_name = "image"
        digits = int(self.digits_var.get())

        result = []
        for i, (filepath, _) in enumerate(self.files, start=1):
            ext = os.path.splitext(filepath)[1].lower()
            new_name = f"{str(i).zfill(digits)}_{base_name}{ext}"
            result.append(new_name)
        return result

    def _update_preview(self):
        self.tree.delete(*self.tree.get_children())
        new_names = self._get_new_names()

        for i, ((filepath, ctime), new_name) in enumerate(
            zip(self.files, new_names), start=1
        ):
            dt = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")
            original = os.path.basename(filepath)
            self.tree.insert("", tk.END, values=(i, original, dt, new_name))

    def _execute_rename(self):
        if not self.files:
            messagebox.showwarning("警告", "ファイルが追加されていません。")
            return

        base_name = self.name_entry.get().strip()
        if not base_name:
            messagebox.showwarning("警告", "ファイル名を入力してください。")
            return

        new_names = self._get_new_names()

        # 確認ダイアログ
        if not messagebox.askyesno(
            "確認", f"{len(self.files)}件のファイルをリネームしますか？"
        ):
            return

        # 衝突回避のため一旦テンポラリ名にリネーム
        temp_map = []
        try:
            for i, (filepath, _) in enumerate(self.files):
                dirpath = os.path.dirname(filepath)
                temp_name = os.path.join(
                    dirpath, f"__temp_rename_{i}_{os.path.basename(filepath)}"
                )
                os.rename(filepath, temp_name)
                temp_map.append((temp_name, os.path.join(dirpath, new_names[i])))

            for temp_path, final_path in temp_map:
                if os.path.exists(final_path):
                    messagebox.showerror(
                        "エラー",
                        f"ファイルが既に存在します: {os.path.basename(final_path)}\nリネームを中断します。",
                    )
                    # ロールバック
                    for t, _ in temp_map:
                        if os.path.exists(t):
                            orig_name = t.split("__temp_rename_")[1].split("_", 1)[1]
                            os.rename(t, os.path.join(os.path.dirname(t), orig_name))
                    return
                os.rename(temp_path, final_path)

        except Exception as e:
            messagebox.showerror("エラー", f"リネーム中にエラーが発生しました:\n{e}")
            return

        first = new_names[0]
        last = new_names[-1]
        if len(new_names) == 1:
            self.status_var.set(f"リネーム完了: {first}")
        else:
            self.status_var.set(
                f"リネーム完了: {first} ... {last}（{len(self.files)}件）"
            )
        self.files.clear()
        self.tree.delete(*self.tree.get_children())

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ImageRenamer()
    app.run()
