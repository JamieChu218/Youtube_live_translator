# ============================================================
#  main.py  ─  主程式入口 + 即時字幕顯示視窗 (Tkinter)
#
#  資料流：
#    AudioCapture → audio_queue
#    Transcriber  → text_queue
#    Router       → translate_queue（翻譯模式）或 result_queue（字幕模式）
#    Translator   → result_queue
#
#  使用方式：
#    python main.py              # 正常啟動
#    python main.py --list-devices  # 列出所有音訊裝置
# ============================================================

import queue
import logging
import argparse
import threading
import tkinter as tk
from datetime import datetime

import config
from audio_capture import AudioCapture, list_devices
from transcriber import Transcriber
from translator import Translator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("translator.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
#  Router：唯一讀取 text_queue 的模組，根據模式分流
# ══════════════════════════════════════════════════════════

class Router:
    """
    從 text_queue 取出日文文字，根據目前模式：
    - 翻譯模式 → 放入 translate_queue（給 Translator 處理）
    - 字幕模式 → 直接放入 result_queue（跳過翻譯）
    """

    def __init__(self,
                 text_queue: queue.Queue,
                 translate_queue: queue.Queue,
                 result_queue: queue.Queue,
                 subtitle_only: threading.Event):
        self.text_queue     = text_queue
        self.translate_queue = translate_queue
        self.result_queue   = result_queue
        self.subtitle_only  = subtitle_only
        self._stop_event    = threading.Event()
        self._thread        = None

    def _route_loop(self):
        logger.info("🔀 Router 啟動")
        while not self._stop_event.is_set():
            try:
                text = self.text_queue.get(timeout=1)
            except queue.Empty:
                continue

            if self.subtitle_only.is_set():
                # 字幕模式：直接顯示日文，不翻譯
                logger.info(f"[字幕模式] {text}")
                self.result_queue.put({"type": "full", "original": text, "translation": None})
            else:
                # 翻譯模式：送給 Translator
                self.translate_queue.put(text)

    def start(self):
        self._thread = threading.Thread(target=self._route_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)


# ══════════════════════════════════════════════════════════
#  字幕視窗
# ══════════════════════════════════════════════════════════

class SubtitleWindow:
    def __init__(self, result_queue: queue.Queue, subtitle_only: threading.Event):
        self.result_queue  = result_queue
        self.subtitle_only = subtitle_only

        self.root = tk.Tk()
        self.root.title("🎌 日文直播翻譯")
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}+100+800")
        self.root.configure(bg="black")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", config.WINDOW_OPACITY)
        self.root.resizable(True, True)

        # ── 工具列 ──
        toolbar = tk.Frame(self.root, bg="#1a1a1a", pady=2)
        toolbar.pack(fill=tk.X)

        tk.Label(
            toolbar, text="🎌 日文直播即時翻譯",
            bg="#1a1a1a", fg="#aaaaaa", font=("微軟正黑體", 10)
        ).pack(side=tk.LEFT, padx=8)

        self.mode_btn = tk.Button(
            toolbar,
            text="切換：字幕模式",
            command=self._toggle_mode,
            bg="#1a5276", fg="white",
            relief=tk.FLAT, padx=10, pady=1,
            font=("微軟正黑體", 10),
            cursor="hand2",
        )
        self.mode_btn.pack(side=tk.LEFT, padx=8)

        self.mode_label = tk.Label(
            toolbar, text="● 翻譯模式",
            bg="#1a1a1a", fg="#2ecc71",
            font=("微軟正黑體", 10, "bold")
        )
        self.mode_label.pack(side=tk.LEFT, padx=4)

        self.status_var = tk.StringVar(value="⏳ 等待音訊...")
        tk.Label(
            toolbar, textvariable=self.status_var,
            bg="#1a1a1a", fg="#aaaaaa", font=("微軟正黑體", 10)
        ).pack(side=tk.RIGHT, padx=8)

        tk.Button(
            toolbar, text="清除", command=self._clear,
            bg="#333", fg="white", relief=tk.FLAT, padx=6,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=4)

        # ── 字幕文字框 ──
        self.text_widget = tk.Text(
            self.root,
            bg="black", fg="white",
            font=("微軟正黑體", config.FONT_SIZE),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=10, pady=6,
            cursor="arrow",
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        self.text_widget.tag_config("time",           foreground="#666666", font=("微軟正黑體", 10))
        self.text_widget.tag_config("japanese",       foreground="#aaddff", font=("微軟正黑體", config.FONT_SIZE - 2))
        self.text_widget.tag_config("japanese_large", foreground="#ffffff", font=("微軟正黑體", config.FONT_SIZE, "bold"))
        self.text_widget.tag_config("translation",    foreground="#ffffff", font=("微軟正黑體", config.FONT_SIZE, "bold"))
        self.text_widget.tag_config("separator",      foreground="#333333")

        toolbar.bind("<ButtonPress-1>", self._start_drag)
        toolbar.bind("<B1-Motion>",     self._do_drag)

        self._poll_results()

    def _toggle_mode(self):
        if self.subtitle_only.is_set():
            self.subtitle_only.clear()
            self.mode_btn.config(text="切換：字幕模式", bg="#1a5276")
            self.mode_label.config(text="● 翻譯模式", fg="#2ecc71")
            logger.info("🔄 切換至翻譯模式")
        else:
            self.subtitle_only.set()
            self.mode_btn.config(text="切換：翻譯模式", bg="#6e2fa1")
            self.mode_label.config(text="● 字幕模式", fg="#a855f7")
            logger.info("🔄 切換至字幕模式")

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _clear(self):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.config(state=tk.DISABLED)

    def _new_entry_prefix(self):
        """若文字框已有內容，先插入分隔換行。"""
        if self.text_widget.get("1.0", tk.END).strip():
            self.text_widget.insert(tk.END, "\n", "separator")

    def _append_result(self, result: dict):
        """字幕模式：一次顯示完整一筆（日文，或日文+翻譯）。"""
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


# ══════════════════════════════════════════════════════════
#  主程式
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="YouTube 日文直播即時翻譯")
    parser.add_argument("--list-devices", action="store_true", help="列出所有音訊裝置")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    logger.info("=" * 50)
    logger.info("🚀 YouTube 日文直播翻譯器 啟動")
    logger.info("=" * 50)

    subtitle_only = threading.Event()   # 未設定 = 翻譯模式

    # ── 三條獨立 Queue，各司其職 ──
    audio_queue    = queue.Queue(maxsize=config.AUDIO_QUEUE_MAXSIZE)
    text_queue     = queue.Queue()        # Transcriber → Router
    translate_queue = queue.Queue()       # Router → Translator（翻譯模式專用）
    result_queue   = queue.Queue()        # → SubtitleWindow

    capture     = AudioCapture(audio_queue)
    transcriber = Transcriber(audio_queue, text_queue)
    translator  = Translator(translate_queue, result_queue)   # 讀 translate_queue
    router      = Router(text_queue, translate_queue, result_queue, subtitle_only)

    capture.start()
    transcriber.start()
    translator.start()
    router.start()

    logger.info("✅ 所有模組已啟動")

    try:
        window = SubtitleWindow(result_queue, subtitle_only)
        window.run()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("🛑 正在關閉...")
        capture.stop()
        transcriber.stop()
        translator.stop()
        router.stop()
        logger.info("👋 程式結束")


if __name__ == "__main__":
    main()
