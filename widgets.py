# -*- coding: utf-8 -*-
"""
widgets.py
----------
Tkinter üçün yumşaq, dəyirmi künclü (rounded) modern düymə widget-i.
Tkinter-in öz Button-u kəskin küncli olduğu üçün Canvas üzərində əl ilə çəkilir.
"""

import tkinter as tk


def _round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None,
                 bg="#5B6EF5", hover_bg="#4A5CE0", fg="white",
                 font=("Segoe UI", 10, "bold"), width=200, height=44,
                 radius=14, disabled_bg="#C7CBEF", **kwargs):
        super().__init__(parent, width=width, height=height,
                          highlightthickness=0, bd=0,
                          bg=parent["bg"], **kwargs)
        self.command = command
        self.bg = bg
        self.hover_bg = hover_bg
        self.disabled_bg = disabled_bg
        self.fg = fg
        self.font = font
        self.radius = radius
        self.width = width
        self.height = height
        self.text = text
        self._state = "normal"

        self._shape = _round_rect(self, 2, 2, width - 2, height - 2,
                                   radius, fill=bg, outline="")
        self._label = self.create_text(width / 2, height / 2, text=text,
                                        fill=fg, font=font)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _event):
        if self._state == "normal":
            self.itemconfig(self._shape, fill=self.hover_bg)
            self.config(cursor="hand2")

    def _on_leave(self, _event):
        if self._state == "normal":
            self.itemconfig(self._shape, fill=self.bg)

    def _on_click(self, _event):
        if self._state == "normal" and self.command:
            self.command()

    def set_enabled(self, enabled: bool):
        self._state = "normal" if enabled else "disabled"
        fill = self.bg if enabled else self.disabled_bg
        text_fill = self.fg if enabled else "#FFFFFF"
        self.itemconfig(self._shape, fill=fill)
        self.itemconfig(self._label, fill=text_fill)
        self.config(cursor="hand2" if enabled else "arrow")

    def set_text(self, text):
        self.text = text
        self.itemconfig(self._label, text=text)


class RoundedPanel(tk.Canvas):
    """Yumşaq, dəyirmi künclü, kəsik-xətli (dashed) drop-zone paneli."""

    def __init__(self, parent, width=460, height=220, radius=22,
                 bg="#FFFFFF", border="#D6DCF5", dashed=True, **kwargs):
        super().__init__(parent, width=width, height=height,
                          highlightthickness=0, bd=0,
                          bg=parent["bg"], **kwargs)
        self.width = width
        self.height = height
        self.radius = radius
        self.bg = bg
        self.border = border
        self.dashed = dashed
        self._shape = None
        self._draw()

    def _draw(self):
        if self._shape:
            self.delete(self._shape)
        dash = (6, 4) if self.dashed else None
        self._shape = _round_rect(
            self, 3, 3, self.width - 3, self.height - 3, self.radius,
            fill=self.bg, outline=self.border, width=2
        )
        if dash:
            self.itemconfig(self._shape, dash=dash)

    def set_colors(self, bg=None, border=None):
        if bg is not None:
            self.bg = bg
        if border is not None:
            self.border = border
        self._draw()
