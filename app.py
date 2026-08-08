# -*- coding: utf-8 -*-
"""
app.py
------
Qaimə (PDF) -> Excel (.xlsx) çevirici — Windows masaüstü tətbiqi.

İstifadə:
    - PDF faylını pəncərəyə sürüşdürüb buraxın (drag & drop), VƏ YA
    - "Fayl seçin" düyməsi ilə seçin.
    - "Excel-ə çevir" düyməsinə basın, saxlama yerini seçin.
"""

import os
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from invoice_parser import parse_invoice, InvoiceParseError
from excel_exporter import export_to_excel
from widgets import RoundedButton, RoundedPanel

APP_TITLE = "Qaimə → Excel"

# ---- Yumşaq, modern rəng palitrası ----
BG = "#F5F6FB"
CARD_BG = "#FFFFFF"
BORDER = "#DDE2F5"
BORDER_HOVER = "#5B6EF5"
TEXT_MAIN = "#2B2E4A"
TEXT_MUTED = "#8B8FA8"
PRIMARY = "#5B6EF5"
PRIMARY_HOVER = "#4A5CE0"
SUCCESS = "#34C77B"
SUCCESS_HOVER = "#28AD68"
ERROR = "#E5566D"

if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_ICO = os.path.join(BASE_DIR, "app_icon.ico")
ICON_PNG = os.path.join(BASE_DIR, "app_icon.png")


class QaimeApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("540x480")
        self.root.minsize(480, 440)
        self.root.configure(bg=BG)
        self._set_window_icon()

        self.selected_file = None

        self._build_ui()

        if DND_AVAILABLE:
            self.drop_panel.drop_target_register(DND_FILES)
            self.drop_panel.dnd_bind('<<Drop>>', self._on_drop)
            self.drop_panel.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.drop_panel.dnd_bind('<<DragLeave>>', self._on_drag_leave)

    # ---------------------------------------------------------- İKON
    def _set_window_icon(self):
        try:
            if sys.platform.startswith("win") and os.path.exists(ICON_ICO):
                self.root.iconbitmap(ICON_ICO)
            elif os.path.exists(ICON_PNG):
                img = tk.PhotoImage(file=ICON_PNG)
                self.root.iconphoto(True, img)
                self._icon_ref = img  # qarbage-collect olunmasın deyə referans saxla
        except Exception:
            pass

    # ---------------------------------------------------------- UI QURULUŞU
    def _build_ui(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=28, pady=26)

        # Drop zone (dəyirmi künc, kəsik-xətli panel)
        self.drop_panel = RoundedPanel(outer, width=480, height=250, radius=22,
                                        bg=CARD_BG, border=BORDER, dashed=True)
        self.drop_panel.pack(pady=(6, 18))
        self.drop_panel.pack_propagate(False)

        content = tk.Frame(self.drop_panel, bg=CARD_BG)
        self.drop_panel.create_window(240, 125, window=content)

        icon_lbl = tk.Label(content, text="⬆", font=("Segoe UI", 30),
                             bg=CARD_BG, fg=PRIMARY)
        icon_lbl.pack(pady=(4, 6))

        hint_text = "PDF faylını buraya sürüşdürün" if DND_AVAILABLE else \
                    "Aşağıdakı düymədən PDF seçin"
        hint_lbl = tk.Label(content, text=hint_text, font=("Segoe UI", 11),
                             bg=CARD_BG, fg=TEXT_MAIN)
        hint_lbl.pack(pady=(0, 2))

        or_lbl = tk.Label(content, text="və ya", font=("Segoe UI", 9),
                           bg=CARD_BG, fg=TEXT_MUTED)
        or_lbl.pack(pady=(2, 12))

        self.browse_btn = RoundedButton(
            content, text="Fayl seçin", command=self._browse_file,
            bg=PRIMARY, hover_bg=PRIMARY_HOVER, width=170, height=42, radius=21
        )
        self.browse_btn.pack()

        self.file_label = tk.Label(content, text="Fayl seçilməyib",
                                    font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_MUTED)
        self.file_label.pack(pady=(14, 0))

        # Çevir düyməsi
        self.convert_btn = RoundedButton(
            outer, text="Excel-ə çevir", command=self._convert,
            bg=SUCCESS, hover_bg=SUCCESS_HOVER, width=220, height=48, radius=24,
            disabled_bg="#BFE9D3"
        )
        self.convert_btn.pack(pady=(4, 14))
        self.convert_btn.set_enabled(False)

        self.status_label = tk.Label(
            outer, text="", font=("Segoe UI", 9), bg=BG, fg=TEXT_MAIN,
            wraplength=460, justify="center"
        )
        self.status_label.pack(pady=(0, 4))

        # Aşağıda incə imza
        footer = tk.Label(outer, text="hsnmhrrmli", font=("Segoe UI", 8),
                           bg=BG, fg="#C3C7DE")
        footer.pack(side="bottom", pady=(6, 0))

    # ---------------------------------------------------------- FAYL SEÇİMİ
    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Qaimə PDF faylını seçin",
            filetypes=[("PDF faylları", "*.pdf")]
        )
        if path:
            self._set_file(path)

    def _on_drag_enter(self, event):
        self.drop_panel.set_colors(bg="#EEF1FE", border=BORDER_HOVER)

    def _on_drag_leave(self, event):
        self.drop_panel.set_colors(bg=CARD_BG, border=BORDER)

    def _on_drop(self, event):
        self.drop_panel.set_colors(bg=CARD_BG, border=BORDER)
        paths = self.root.tk.splitlist(event.data)
        if not paths:
            return
        path = paths[0]
        if not path.lower().endswith(".pdf"):
            messagebox.showerror("Səhv fayl növü", "Zəhmət olmasa yalnız PDF faylı seçin.")
            return
        self._set_file(path)

    def _set_file(self, path):
        self.selected_file = path
        filename = os.path.basename(path)
        self.file_label.config(text=f"✓ {filename}", fg=PRIMARY)
        self.convert_btn.set_enabled(True)
        self.status_label.config(text="", fg=TEXT_MAIN)

    # ---------------------------------------------------------- ÇEVİRMƏ
    def _convert(self):
        if not self.selected_file:
            return

        self.status_label.config(text="Emal edilir, zəhmət olmasa gözləyin...", fg=PRIMARY)
        self.root.update_idletasks()

        try:
            header, rows, columns = parse_invoice(self.selected_file)
        except InvoiceParseError as e:
            self.status_label.config(text="", fg=TEXT_MAIN)
            messagebox.showerror("Çıxarma xətası", str(e))
            return
        except Exception as e:
            self.status_label.config(text="", fg=TEXT_MAIN)
            messagebox.showerror(
                "Gözlənilməz xəta",
                f"PDF oxunarkən xəta baş verdi:\n{e}\n\n{traceback.format_exc()}"
            )
            return

        default_name = os.path.splitext(os.path.basename(self.selected_file))[0] + ".xlsx"
        save_path = filedialog.asksaveasfilename(
            title="Excel faylını harada saxlamaq istəyirsiniz?",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel faylı", "*.xlsx")]
        )
        if not save_path:
            self.status_label.config(text="Saxlama ləğv edildi.", fg=ERROR)
            return

        try:
            export_to_excel(header, rows, columns, save_path)
        except Exception as e:
            messagebox.showerror(
                "Excel yazma xətası",
                f"Excel faylı yaradılarkən xəta baş verdi:\n{e}"
            )
            return

        self.status_label.config(
            text=f"✔ Uğurla çevrildi: {len(rows)} sətir yazıldı → {os.path.basename(save_path)}",
            fg=SUCCESS_HOVER
        )
        messagebox.showinfo(
            "Hazırdır",
            f"{len(rows)} mal sətri uğurla Excel faylına yazıldı:\n{save_path}"
        )


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = QaimeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
