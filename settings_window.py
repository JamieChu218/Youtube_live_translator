# ============================================================
#  settings_window.py  ─  分頁式設定視窗 (CTkToplevel)
#
#  「儲存並套用」→ config.save() → on_apply(needs_restart)
#  needs_restart：變更的鍵是否影響管線（音訊/辨識/翻譯），
#  外觀類變更即時生效，不需重啟。
# ============================================================

import threading
import logging

import customtkinter as ctk

import config
import theme
from ui_common import device_choices, test_api_key

logger = logging.getLogger(__name__)

# 這些鍵變更後需要重啟管線
RESTART_KEYS = {
    "API_KEY", "CABLE_DEVICE_INDEX",
    "CHUNK_SECONDS", "SILENCE_THRESHOLD",
    "USE_DYNAMIC_SEGMENTATION", "PAUSE_SECONDS", "MIN_SPEECH_SECONDS",
    "STT_MODEL", "STT_WORKERS", "GPT_MODEL",
    "SOURCE_LANG", "TARGET_LANG",
}

STT_MODEL_OPTIONS = ["gpt-4o-mini-transcribe", "whisper-1"]
GPT_MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o"]


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, on_apply):
        super().__init__(master, fg_color=theme.BG)
        self.on_apply = on_apply

        self.title("⚙ 設定")
        self.geometry("600x560")
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self._device_map = {}    # 顯示文字 → 裝置索引(None=自動)

        tabs = ctk.CTkTabview(
            self, fg_color=theme.PANEL,
            segmented_button_selected_color=theme.ACCENT,
        )
        tabs.pack(fill="both", expand=True, padx=12, pady=(12, 4))
        tab_general    = tabs.add("一般")
        tab_engine     = tabs.add("辨識與翻譯")
        tab_segment    = tabs.add("斷句")
        tab_appearance = tabs.add("外觀")

        self._build_general(tab_general)
        self._build_engine(tab_engine)
        self._build_segment(tab_segment)
        self._build_appearance(tab_appearance)

        # ── 底部按鈕 ──
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkButton(
            btn_row, text="儲存並套用", width=120,
            font=(theme.FONT_FAMILY, 13),
            fg_color=theme.ACCENT, command=self._save,
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            btn_row, text="取消", width=80,
            font=(theme.FONT_FAMILY, 13),
            fg_color=theme.PANEL_2, hover_color=theme.BORDER,
            command=self.destroy,
        ).pack(side="right")

    # ── 小工具 ─────────────────────────────────────────────

    def _label(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, anchor="w",
                           font=(theme.FONT_FAMILY, 13),
                           text_color=theme.TEXT_MAIN)
        lbl.pack(fill="x", padx=12, pady=(10, 0))
        return lbl

    def _hint(self, parent, text):
        ctk.CTkLabel(parent, text=text, anchor="w", justify="left",
                     font=(theme.FONT_FAMILY, 11),
                     text_color=theme.TEXT_DIM, wraplength=520,
                     ).pack(fill="x", padx=12, pady=(0, 2))

    def _slider(self, parent, label, from_, to, steps, value, fmt):
        """
        建立「滑桿 + 可輸入數值欄」的調整列，回傳取值函式。
        - 滑桿拖動 → 欄位同步顯示
        - 欄位輸入（Enter 或失焦）→ 防呆後套用到滑桿：
            超出範圍夾到最大/最小值；整數欄四捨五入；小數欄固定兩位
        """
        is_int = fmt == "{:.0f}"
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(row, text=label, width=170, anchor="w",
                     font=(theme.FONT_FAMILY, 13)).pack(side="left")

        var = ctk.DoubleVar(value=value)
        entry = ctk.CTkEntry(row, width=64, justify="right",
                             font=(theme.FONT_FAMILY, 12),
                             fg_color=theme.PANEL_2, border_color=theme.BORDER)
        entry.pack(side="right")

        def set_entry(v):
            entry.delete(0, "end")
            entry.insert(0, fmt.format(v))

        set_entry(value)

        slider = ctk.CTkSlider(
            row, from_=from_, to=to, number_of_steps=steps,
            variable=var, progress_color=theme.ACCENT,
            command=set_entry,
        )
        slider.pack(side="left", fill="x", expand=True, padx=8)

        def commit(event=None):
            raw = entry.get().strip().replace("，", ".").replace(",", ".")
            try:
                v = float(raw)
            except ValueError:
                set_entry(var.get())    # 無效輸入 → 還原目前值
                return
            v = max(from_, min(to, v))              # 超界 → 夾到邊界
            v = float(round(v)) if is_int else round(v, 2)
            var.set(v)
            set_entry(v)

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)

        def getter():
            commit()   # 儲存時把「打了字但還沒按 Enter」的輸入也一併生效
            return var.get()

        return getter

    # ── 一般 ───────────────────────────────────────────────

    def _build_general(self, tab):
        # API Key
        self._label(tab, "OpenAI API Key")
        if config.api_key_from_env():
            self._hint(tab, "已從環境變數 / .env 讀取 API Key（優先於此處設定）。"
                            "如需更換請修改環境變數，或先移除後再於此填入。")
        self.api_entry = ctk.CTkEntry(
            tab, show="•", font=("Consolas", 12),
            placeholder_text="sk-...",
        )
        self.api_entry.pack(fill="x", padx=12, pady=(4, 0))
        if config._settings.get("API_KEY"):
            self.api_entry.insert(0, config._settings["API_KEY"])

        key_row = ctk.CTkFrame(tab, fg_color="transparent")
        key_row.pack(fill="x", padx=12, pady=(6, 0))
        self._show_key = False

        def toggle_show():
            self._show_key = not self._show_key
            self.api_entry.configure(show="" if self._show_key else "•")

        ctk.CTkButton(key_row, text="顯示/隱藏", width=80, height=26,
                      font=(theme.FONT_FAMILY, 12),
                      fg_color=theme.PANEL_2, hover_color=theme.BORDER,
                      command=toggle_show).pack(side="left")
        ctk.CTkButton(key_row, text="測試連線", width=80, height=26,
                      font=(theme.FONT_FAMILY, 12),
                      fg_color=theme.PANEL_2, hover_color=theme.BORDER,
                      command=self._test_key).pack(side="left", padx=6)
        self.key_status = ctk.CTkLabel(key_row, text="",
                                       font=(theme.FONT_FAMILY, 12),
                                       text_color=theme.TEXT_DIM)
        self.key_status.pack(side="left", padx=6)

        # 音訊裝置
        self._label(tab, "音訊輸入裝置")
        self._hint(tab, "選擇 VB-CABLE 的 CABLE Output；「自動偵測」會尋找名稱含 CABLE 的裝置。")
        dev_row = ctk.CTkFrame(tab, fg_color="transparent")
        dev_row.pack(fill="x", padx=12, pady=(4, 0))
        self.device_menu = ctk.CTkOptionMenu(
            dev_row, values=["載入中..."], width=420,
            font=(theme.FONT_FAMILY, 12),
            fg_color=theme.PANEL_2, button_color=theme.ACCENT,
        )
        self.device_menu.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dev_row, text="↻", width=34,
                      font=(theme.FONT_FAMILY, 13),
                      fg_color=theme.PANEL_2, hover_color=theme.BORDER,
                      command=self._refresh_devices).pack(side="left", padx=(6, 0))
        self._refresh_devices()

    def _refresh_devices(self):
        choices = device_choices()
        self._device_map = dict(choices)
        displays = [d for d, _ in choices]
        self.device_menu.configure(values=displays)
        # 選回目前設定值
        current = config.CABLE_DEVICE_INDEX
        for display, idx in choices:
            if idx == current:
                self.device_menu.set(display)
                return
        self.device_menu.set(displays[0])

    def _test_key(self):
        key = self.api_entry.get().strip() or (config.OPENAI_API_KEY or "")
        self.key_status.configure(text="測試中...", text_color=theme.TEXT_DIM)

        def worker():
            ok, msg = test_api_key(key)
            color = theme.GOOD if ok else theme.DANGER
            self.after(0, lambda: self.key_status.configure(text=msg, text_color=color))

        threading.Thread(target=worker, daemon=True).start()

    # ── 辨識與翻譯 ─────────────────────────────────────────

    def _build_engine(self, tab):
        self._label(tab, "語音辨識模型")
        self.stt_menu = ctk.CTkOptionMenu(
            tab, values=STT_MODEL_OPTIONS, font=("Consolas", 12),
            fg_color=theme.PANEL_2, button_color=theme.ACCENT)
        self.stt_menu.pack(fill="x", padx=12, pady=(4, 0))
        self.stt_menu.set(config.STT_MODEL)
        self._hint(tab, "gpt-4o-mini-transcribe 延遲較低；帳號無權限時可改回 whisper-1。")

        self.get_workers = self._slider(tab, "並行辨識 worker 數", 1, 5, 4,
                                        config.STT_WORKERS, "{:.0f}")
        self._hint(tab, "連續快速說話時清空積壓更快；調小可省 API 用量。")

        self._label(tab, "翻譯模型")
        self.gpt_menu = ctk.CTkOptionMenu(
            tab, values=GPT_MODEL_OPTIONS, font=("Consolas", 12),
            fg_color=theme.PANEL_2, button_color=theme.ACCENT)
        self.gpt_menu.pack(fill="x", padx=12, pady=(4, 0))
        self.gpt_menu.set(config.GPT_MODEL)

        lang_row = ctk.CTkFrame(tab, fg_color="transparent")
        lang_row.pack(fill="x", padx=12, pady=(12, 0))
        ctk.CTkLabel(lang_row, text="來源語言", font=(theme.FONT_FAMILY, 13)).pack(side="left")
        self.src_entry = ctk.CTkEntry(lang_row, width=110, font=(theme.FONT_FAMILY, 12))
        self.src_entry.pack(side="left", padx=(6, 16))
        self.src_entry.insert(0, config.SOURCE_LANG)
        ctk.CTkLabel(lang_row, text="目標語言", font=(theme.FONT_FAMILY, 13)).pack(side="left")
        self.tgt_entry = ctk.CTkEntry(lang_row, width=110, font=(theme.FONT_FAMILY, 12))
        self.tgt_entry.pack(side="left", padx=6)
        self.tgt_entry.insert(0, config.TARGET_LANG)

    # ── 斷句 ───────────────────────────────────────────────

    def _build_segment(self, tab):
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(row, text="動態斷句（VAD）",
                     font=(theme.FONT_FAMILY, 13)).pack(side="left")
        self.dyn_switch = ctk.CTkSwitch(row, text="", progress_color=theme.ACCENT)
        self.dyn_switch.pack(side="right")
        if config.USE_DYNAMIC_SEGMENTATION:
            self.dyn_switch.select()
        self._hint(tab, "偵測到停頓就立刻送出辨識；關閉則固定每「斷句上限」秒切一塊。")

        self.get_pause = self._slider(tab, "停頓斷句門檻（秒）", 0.3, 1.5, 24,
                                      config.PAUSE_SECONDS, "{:.2f}")
        self._hint(tab, "調大→句子更完整但延遲略增；調小→更即時但可能切碎。")

        self.get_min_speech = self._slider(tab, "最短語音長度（秒）", 0.2, 2.0, 18,
                                           config.MIN_SPEECH_SECONDS, "{:.2f}")
        self._hint(tab, "過短的聲音片段不送辨識；調小可保留短應答（如「うん」）。")

        self.get_chunk = self._slider(tab, "斷句上限（秒）", 3, 8, 5,
                                      config.CHUNK_SECONDS, "{:.0f}")
        self.get_silence = self._slider(tab, "靜音門檻（音量）", 50, 1000, 19,
                                        config.SILENCE_THRESHOLD, "{:.0f}")
        self._hint(tab, "低於此音量視為靜音；環境雜訊大時調高。")

    # ── 外觀 ───────────────────────────────────────────────

    def _build_appearance(self, tab):
        self.get_opacity = self._slider(tab, "視窗透明度", 0.3, 1.0, 14,
                                        config.WINDOW_OPACITY, "{:.2f}")
        self.get_font = self._slider(tab, "字級", 12, 32, 20,
                                     config.FONT_SIZE, "{:.0f}")
        self.get_lines = self._slider(tab, "最多顯示筆數", 3, 15, 12,
                                      config.MAX_LINES, "{:.0f}")
        self._hint(tab, "外觀變更立即生效，不需重啟管線。")

    # ── 儲存 ───────────────────────────────────────────────

    def _save(self):
        updates = {
            "API_KEY": self.api_entry.get().strip(),
            "CABLE_DEVICE_INDEX": self._device_map.get(self.device_menu.get()),
            "STT_MODEL": self.stt_menu.get(),
            "STT_WORKERS": int(round(self.get_workers())),
            "GPT_MODEL": self.gpt_menu.get(),
            "SOURCE_LANG": self.src_entry.get().strip() or "日文",
            "TARGET_LANG": self.tgt_entry.get().strip() or "繁體中文",
            "USE_DYNAMIC_SEGMENTATION": bool(self.dyn_switch.get()),
            "PAUSE_SECONDS": round(self.get_pause(), 2),
            "MIN_SPEECH_SECONDS": round(self.get_min_speech(), 2),
            "CHUNK_SECONDS": int(round(self.get_chunk())),
            "SILENCE_THRESHOLD": int(round(self.get_silence())),
            "WINDOW_OPACITY": round(self.get_opacity(), 2),
            "FONT_SIZE": int(round(self.get_font())),
            "MAX_LINES": int(round(self.get_lines())),
        }

        # 判斷是否需要重啟管線（有影響管線的鍵且值有變）
        needs_restart = any(
            key in RESTART_KEYS and getattr(config, key) != value
            for key, value in updates.items()
        )

        config.save(updates)
        logger.info(f"設定已儲存（重啟管線：{needs_restart}）")
        self.destroy()
        self.on_apply(needs_restart)
