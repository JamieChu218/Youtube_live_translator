# ============================================================
#  subtitle_window.py  ─  置頂半透明字幕視窗 (CustomTkinter)
#
#  字幕顯示區沿用 tk.Text（tag 配色 + 串流逐字插入），
#  外層以 CTk 元件統一風格。
# ============================================================

import queue
import time
import ctypes
import logging
import threading
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

import config
import theme
from i18n import t
from pipeline import Pipeline

logger = logging.getLogger(__name__)

# ── Win32 點擊穿透 ────────────────────────────────────────
GWL_EXSTYLE       = -20
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
VK_CONTROL        = 0x11
VK_MENU           = 0x12   # Alt

NO_AUDIO_WARN_SECONDS = 30   # 超過此秒數無聲 → 提醒檢查路由


class SubtitleWindow:
    def __init__(self, result_queue: queue.Queue,
                 subtitle_only: threading.Event,
                 pipeline: Pipeline):
        self.result_queue  = result_queue
        self.subtitle_only = subtitle_only
        self.pipeline      = pipeline
        self._settings_win = None
        self._paused          = False
        self._click_through   = bool(config.CLICK_THROUGH)
        self._escape_held     = False   # 按住 Ctrl+Alt 暫時解除穿透中
        self._no_audio_warned = False

        theme.apply()
        self.root = ctk.CTk(fg_color=theme.BG)
        self.root.title(t("app.title"))

        # 記住的視窗位置(夾回螢幕範圍,避免螢幕配置改變後跑到畫面外)
        x = config.WINDOW_X if config.WINDOW_X is not None else 100
        y = config.WINDOW_Y if config.WINDOW_Y is not None else 800
        x = max(0, min(int(x), self.root.winfo_screenwidth()  - 200))
        y = max(0, min(int(y), self.root.winfo_screenheight() - 100))
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}+{x}+{y}")

        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", config.WINDOW_OPACITY)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── 工具列 ──
        toolbar = ctk.CTkFrame(self.root, fg_color=theme.PANEL, corner_radius=0)
        toolbar.pack(fill="x")

        self.title_lbl = title_lbl = ctk.CTkLabel(
            toolbar, text=t("app.header"),
            text_color=theme.TEXT_DIM,
            font=(theme.FONT_FAMILY, 13),
        )
        title_lbl.pack(side="left", padx=(12, 8), pady=6)

        self.mode_seg = ctk.CTkSegmentedButton(
            toolbar,
            values=[t("mode.translate"), t("mode.subtitle")],
            command=self._on_mode_change,
            font=(theme.FONT_FAMILY, 12),
            selected_color=theme.ACCENT,
            selected_hover_color=theme.ACCENT,
            unselected_color=theme.PANEL_2,
            fg_color=theme.PANEL_2,
            height=28,
        )
        self.mode_seg.set(t("mode.translate"))
        self.mode_seg.pack(side="left", padx=8, pady=6)

        self.pause_btn = ctk.CTkButton(
            toolbar, text="⏸", width=34, height=28,
            font=(theme.FONT_FAMILY, 14),
            fg_color=theme.PANEL_2, hover_color=theme.BORDER,
            command=self._toggle_pause,
        )
        self.pause_btn.pack(side="left", padx=4, pady=6)

        self.ct_btn = ctk.CTkButton(
            toolbar, text=t("btn.passthrough"), width=60, height=28,
            font=(theme.FONT_FAMILY, 12),
            fg_color=theme.ACCENT if self._click_through else theme.PANEL_2,
            hover_color=theme.BORDER,
            command=self._toggle_click_through,
        )
        self.ct_btn.pack(side="left", padx=4, pady=6)

        # 右側：⚙ 設定、清除、狀態、音訊指示燈
        self.settings_btn = ctk.CTkButton(
            toolbar, text="⚙", width=34, height=28,
            font=(theme.FONT_FAMILY, 14),
            fg_color=theme.PANEL_2, hover_color=theme.BORDER,
            command=self._open_settings,
        )
        self.settings_btn.pack(side="right", padx=(4, 12), pady=6)

        self.clear_btn = clear_btn = ctk.CTkButton(
            toolbar, text=t("btn.clear"), width=52, height=28,
            font=(theme.FONT_FAMILY, 12),
            fg_color=theme.PANEL_2, hover_color=theme.BORDER,
            command=self._clear,
        )
        clear_btn.pack(side="right", padx=4, pady=6)

        self.audio_dot = ctk.CTkLabel(
            toolbar, text="●", width=16,
            text_color=theme.TEXT_DIM, font=(theme.FONT_FAMILY, 14),
        )
        self.audio_dot.pack(side="right", padx=(0, 4), pady=6)

        self.status_var = tk.StringVar(value=t("status.waiting"))
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
        self._poll_audio_status()
        self._poll_modifier_escape()
        # HWND 要等視窗實際建立後才拿得到,延遲套用穿透狀態
        if self._click_through:
            self.root.after(300, self._apply_click_through)

    # ── 點擊穿透 ───────────────────────────────────────────
    def _hwnd(self):
        return ctypes.windll.user32.GetParent(self.root.winfo_id())

    def _set_click_through(self, enabled: bool):
        """對視窗設定/解除 WS_EX_TRANSPARENT(滑鼠事件穿過視窗)。"""
        try:
            hwnd = self._hwnd()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enabled:
                style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
            else:
                style &= ~WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            logger.exception("設定點擊穿透失敗")

    def _apply_click_through(self):
        self._set_click_through(self._click_through and not self._escape_held)
        self.ct_btn.configure(
            fg_color=theme.ACCENT if self._click_through else theme.PANEL_2)

    def _toggle_click_through(self):
        self._click_through = not self._click_through
        config.save({"CLICK_THROUGH": self._click_through})
        self._apply_click_through()
        if self._click_through:
            self.show_system_message(t("msg.passthrough_on"))
            logger.info("🖱 點擊穿透開啟")
        else:
            logger.info("🖱 點擊穿透關閉")

    def _poll_modifier_escape(self):
        """穿透開啟時:按住 Ctrl+Alt 暫時解除,放開恢復。"""
        try:
            if self._click_through:
                held = bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) \
                   and bool(ctypes.windll.user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                if held != self._escape_held:
                    self._escape_held = held
                    self._set_click_through(not held)
        finally:
            self.root.after(200, self._poll_modifier_escape)

    # ── 暫停/繼續 ──────────────────────────────────────────
    def _toggle_pause(self):
        if self._paused:
            ok, err = self.pipeline.start()
            if ok:
                self._paused = False
                self.pause_btn.configure(text="⏸", fg_color=theme.PANEL_2)
                self.status_var.set(t("status.resumed"))
                logger.info("▶ 使用者繼續辨識")
            else:
                self.show_system_message(f"❌ {err}")
        else:
            self._paused = True
            self.pause_btn.configure(text="▶", fg_color=theme.WARN,
                                     state="disabled")
            self.status_var.set(t("status.pausing"))
            logger.info("⏸ 使用者暫停辨識")

            def worker():   # stop 會 join 執行緒,放背景避免卡 UI
                self.pipeline.stop()
                self.root.after(0, lambda: (
                    self.pause_btn.configure(state="normal"),
                    self.status_var.set(t("status.paused")),
                ))

            threading.Thread(target=worker, daemon=True).start()

    # ── 音訊狀態指示 ───────────────────────────────────────
    def _poll_audio_status(self):
        try:
            status = None
            if not self._paused and self.pipeline.running:
                status = self.pipeline.audio_status()

            if status is None:
                self.audio_dot.configure(text_color=theme.TEXT_DIM)
            else:
                rms, last_audio = status
                silent_for = time.monotonic() - last_audio
                if silent_for >= NO_AUDIO_WARN_SECONDS:
                    self.audio_dot.configure(text_color=theme.DANGER)
                    if not self._no_audio_warned:
                        self._no_audio_warned = True
                        self.show_system_message(
                            t("msg.no_audio", seconds=NO_AUDIO_WARN_SECONDS))
                elif rms >= config.SILENCE_THRESHOLD:
                    self.audio_dot.configure(text_color=theme.GOOD)
                    self._no_audio_warned = False
                else:
                    self.audio_dot.configure(text_color=theme.TEXT_DIM)
        finally:
            self.root.after(500, self._poll_audio_status)

    # ── 關閉:記住視窗位置 ──────────────────────────────────
    def _on_close(self):
        try:
            config.save({
                "WINDOW_X":      self.root.winfo_x(),
                "WINDOW_Y":      self.root.winfo_y(),
                "WINDOW_WIDTH":  self.root.winfo_width(),
                "WINDOW_HEIGHT": self.root.winfo_height(),
            })
        except Exception:
            logger.exception("儲存視窗位置失敗")
        self.root.destroy()

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

    def apply_language(self):
        """介面語言變更後即時更新所有可見文字（不需重啟程式）。"""
        was_subtitle = self.subtitle_only.is_set()
        self.root.title(t("app.title"))
        self.title_lbl.configure(text=t("app.header"))
        self.mode_seg.configure(values=[t("mode.translate"), t("mode.subtitle")])
        self.mode_seg.set(t("mode.subtitle") if was_subtitle else t("mode.translate"))
        self.ct_btn.configure(text=t("btn.passthrough"))
        self.clear_btn.configure(text=t("btn.clear"))
        self.status_var.set(t("status.paused") if self._paused
                            else t("status.waiting"))

    # ── 模式切換 ───────────────────────────────────────────
    def _on_mode_change(self, value: str):
        if value == t("mode.subtitle"):
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

    def _on_settings_applied(self, needs_restart: bool, lang_changed: bool = False):
        self.apply_appearance()
        if lang_changed:
            self.apply_language()
        if needs_restart:
            if self._paused:
                # 暫停中不啟動管線;新設定會在按 ▶ 繼續時生效
                self.show_system_message(t("msg.settings_saved_paused"))
                return
            ok, err = self.pipeline.restart()
            if ok:
                self.show_system_message(t("msg.settings_applied"))
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
                self.status_var.set(t("status.updated", time=datetime.now().strftime("%H:%M:%S")))
        except queue.Empty:
            pass
        finally:
            self.root.after(config.POLL_INTERVAL_MS, self._poll_results)

    def run(self):
        self.root.mainloop()
