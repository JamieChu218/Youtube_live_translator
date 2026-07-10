# ============================================================
#  subtitle_window.py  ─  置頂半透明字幕視窗 (CustomTkinter)
#
#  字幕顯示區沿用 tk.Text（tag 配色 + 串流逐字插入），
#  外層以 CTk 元件統一風格。
# ============================================================

import queue
import logging
import threading
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

import config
import theme
from pipeline import Pipeline

logger = logging.getLogger(__name__)


class SubtitleWindow:
    def __init__(self, result_queue: queue.Queue,
                 subtitle_only: threading.Event,
                 pipeline: Pipeline):
        self.result_queue  = result_queue
        self.subtitle_only = subtitle_only
        self.pipeline      = pipeline
        self._settings_win = None

        theme.apply()
        self.root = ctk.CTk(fg_color=theme.BG)
        self.root.title("🎌 日文直播翻譯")
        self.root.geometry(
            f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}+100+800")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", config.WINDOW_OPACITY)
        self.root.resizable(True, True)

        # ── 工具列 ──
        toolbar = ctk.CTkFrame(self.root, fg_color=theme.PANEL, corner_radius=0)
        toolbar.pack(fill="x")

        title_lbl = ctk.CTkLabel(
            toolbar, text="🎌 日文直播即時翻譯",
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, 13),
        )
        title_lbl.pack(side="left", padx=(12, 8), pady=6)

        self.mode_seg = ctk.CTkSegmentedButton(
            toolbar,
            values=["翻譯模式", "字幕模式"],
            command=self._on_mode_change,
            font=(theme.FONT_FAMILY, 12),
            selected_color=theme.ACCENT,
            selected_hover_color=theme.ACCENT,
            unselected_color=theme.PANEL_2,
            fg_color=theme.PANEL_2,
            height=28,
        )
        self.mode_seg.set("翻譯模式")
        self.mode_seg.pack(side="left", padx=8, pady=6)

        # 右側：⚙ 設定、清除、狀態
        self.settings_btn = ctk.CTkButton(
            toolbar, text="⚙", width=34, height=28,
            font=(theme.FONT_FAMILY, 14),
            fg_color=theme.PANEL_2, hover_color=theme.BORDER,
            command=self._open_settings,
        )
        self.settings_btn.pack(side="right", padx=(4, 12), pady=6)

        clear_btn = ctk.CTkButton(
            toolbar, text="清除", width=52, height=28,
            font=(theme.FONT_FAMILY, 12),
            fg_color=theme.PANEL_2, hover_color=theme.BORDER,
            command=self._clear,
        )
        clear_btn.pack(side="right", padx=4, pady=6)

        self.status_var = tk.StringVar(value="⏳ 等待音訊...")
        ctk.CTkLabel(
            toolbar, textvariable=self.status_var,
            text_color=theme.TEXT_DIM, font=(theme.FONT_FAMILY, 12),
        ).pack(side="right", padx=8, pady=6)

        # ── 字幕文字框（沿用 tk.Text 以保留 tag/串流邏輯）──
        body = ctk.CTkFrame(self.root, fg_color=theme.BG, corner_radius=0)
        body.pack(fill="both", expand=True)

        self.text_widget = tk.Text(
            body,
            bg=theme.BG, fg=theme.TEXT_MAIN,
            font=(theme.FONT_FAMILY, config.FONT_SIZE),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=14, pady=8,
            cursor="arrow",
            highlightthickness=0,
            insertbackground=theme.TEXT_MAIN,
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=2, pady=(2, 4))

        self._config_tags()

        # 拖曳視窗（工具列與標題都可拖）
        for w in (toolbar, title_lbl):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>",     self._do_drag)

        self._poll_results()

    # ── 外觀 ───────────────────────────────────────────────
    def _config_tags(self):
        fs = config.FONT_SIZE
        self.text_widget.config(font=(theme.FONT_FAMILY, fs))
        self.text_widget.tag_config("time",           foreground=theme.TAG_TIME,        font=(theme.FONT_FAMILY, max(9, fs - 8)))
        self.text_widget.tag_config("japanese",       foreground=theme.TAG_JAPANESE,    font=(theme.FONT_FAMILY, fs - 2))
        self.text_widget.tag_config("japanese_large", foreground=theme.TAG_TRANSLATION, font=(theme.FONT_FAMILY, fs, "bold"))
        self.text_widget.tag_config("translation",    foreground=theme.TAG_TRANSLATION, font=(theme.FONT_FAMILY, fs, "bold"))
        self.text_widget.tag_config("system",         foreground=theme.TAG_SYSTEM,      font=(theme.FONT_FAMILY, fs - 4))
        self.text_widget.tag_config("separator",      foreground=theme.TAG_SEPARATOR)

    def apply_appearance(self):
        """設定視窗變更外觀後即時套用（不需重啟管線）。"""
        self.root.attributes("-alpha", config.WINDOW_OPACITY)
        self._config_tags()

    # ── 模式切換 ───────────────────────────────────────────
    def _on_mode_change(self, value: str):
        if value == "字幕模式":
            self.subtitle_only.set()
            self.mode_seg.configure(selected_color=theme.ACCENT_2,
                                    selected_hover_color=theme.ACCENT_2)
            logger.info("🔄 切換至字幕模式")
        else:
            self.subtitle_only.clear()
            self.mode_seg.configure(selected_color=theme.ACCENT,
                                    selected_hover_color=theme.ACCENT)
            logger.info("🔄 切換至翻譯模式")

    # ── 設定視窗 ───────────────────────────────────────────
    def _open_settings(self):
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.focus()
            return
        from settings_window import SettingsWindow   # 延遲載入，加快啟動
        self._settings_win = SettingsWindow(
            self.root,
            on_apply=self._on_settings_applied,
        )

    def _on_settings_applied(self, needs_restart: bool):
        self.apply_appearance()
        if needs_restart:
            ok, err = self.pipeline.restart()
            if ok:
                self.show_system_message("✅ 設定已套用，管線已重新啟動")
            else:
                self.show_system_message(f"❌ {err}")

    # ── 拖曳 ───────────────────────────────────────────────
    def _start_drag(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _do_drag(self, event):
        self.root.geometry(
            f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ── 字幕內容 ───────────────────────────────────────────
    def _clear(self):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def show_system_message(self, message: str):
        """在字幕區顯示系統訊息（錯誤 / 提示）。"""
        self.text_widget.config(state=tk.NORMAL)
        self._new_entry_prefix()
        self.text_widget.insert(tk.END, message, "system")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)

    def _new_entry_prefix(self):
        """若文字框已有內容，先插入分隔換行。"""
        if self.text_widget.get("1.0", tk.END).strip():
            self.text_widget.insert(tk.END, "\n", "separator")

    def _append_result(self, result: dict):
        """一次顯示完整一筆（日文，或日文+翻譯）。"""
        now = datetime.now().strftime("%H:%M:%S")
        self.text_widget.config(state=tk.NORMAL)
        self._new_entry_prefix()

        if result.get("translation") is None:
            # 字幕模式：只顯示日文
            self.text_widget.insert(tk.END, f"[{now}] ", "time")
            self.text_widget.insert(tk.END, result["original"], "japanese_large")
        else:
            # 完整翻譯（非串流路徑）
            self.text_widget.insert(tk.END, f"[{now}] ", "time")
            self.text_widget.insert(tk.END, f"{result['original']}\n", "japanese")
            self.text_widget.insert(tk.END, f"▶ {result['translation']}", "translation")

        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)
        self._trim_old_lines()

    # ── 串流翻譯：逐字顯示 ──────────────────────────────
    def _begin_streaming(self, original: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.text_widget.config(state=tk.NORMAL)
        self._new_entry_prefix()
        self.text_widget.insert(tk.END, f"[{now}] ", "time")
        self.text_widget.insert(tk.END, f"{original}\n", "japanese")
        self.text_widget.insert(tk.END, "▶ ", "translation")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)

    def _append_delta(self, text: str):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, text, "translation")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)

    def _end_streaming(self):
        self._trim_old_lines()

    def _trim_old_lines(self):
        total_lines = int(self.text_widget.index("end-1c").split(".")[0])
        max_display = config.MAX_LINES * 3
        if total_lines > max_display:
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete("1.0", f"{total_lines - max_display}.0")
            self.text_widget.config(state=tk.DISABLED)

    def _handle_msg(self, msg: dict):
        mtype = msg.get("type", "full")
        if mtype == "start":
            self._begin_streaming(msg["original"])
        elif mtype == "delta":
            self._append_delta(msg["text"])
        elif mtype == "end":
            self._end_streaming()
        else:  # "full"
            self._append_result(msg)

    def _poll_results(self):
        try:
            while True:
                msg = self.result_queue.get_nowait()
                self._handle_msg(msg)
                self.status_var.set(f"更新 {datetime.now().strftime('%H:%M:%S')}")
        except queue.Empty:
            pass
        finally:
            self.root.after(config.POLL_INTERVAL_MS, self._poll_results)

    def run(self):
        self.root.mainloop()
