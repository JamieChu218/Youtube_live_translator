# ============================================================
#  main.py  ─  主程式入口 + 即時字幕顯示視窗 (Tkinter)
#
#  使用方式：
#    python main.py              # 正常啟動
#    python main.py --list-devices  # 列出所有音訊裝置
# ============================================================

import sys
import queue
import logging
import argparse
import threading
import tkinter as tk
from datetime import datetime
from collections import deque

import config
from audio_capture import AudioCapture, list_devices
from transcriber import Transcriber
from translator import Translator

# ── 日誌設定 ──────────────────────────────────────────────
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
#  字幕視窗（始終在最上層的半透明黑色視窗）
# ══════════════════════════════════════════════════════════

class SubtitleWindow:
    def __init__(self, result_queue: queue.Queue):
        self.result_queue = result_queue
        self.lines = deque(maxlen=config.MAX_LINES)

        # 建立主視窗
        self.root = tk.Tk()
        self.root.title("🎌 日文直播翻譯")
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}+100+800")
        self.root.configure(bg="black")
        self.root.attributes("-topmost", True)          # 固定在最上層
        self.root.attributes("-alpha", config.WINDOW_OPACITY)
        self.root.resizable(True, True)

        # ── 工具列 ──
        toolbar = tk.Frame(self.root, bg="#1a1a1a", pady=2)
        toolbar.pack(fill=tk.X)

        tk.Label(
            toolbar, text="🎌 日文直播即時翻譯",
            bg="#1a1a1a", fg="#aaaaaa", font=("微軟正黑體", 10)
        ).pack(side=tk.LEFT, padx=8)

        self.status_var = tk.StringVar(value="⏳ 等待音訊...")
        tk.Label(
            toolbar, textvariable=self.status_var,
            bg="#1a1a1a", fg="#55cc55", font=("微軟正黑體", 10)
        ).pack(side=tk.RIGHT, padx=8)

        tk.Button(
            toolbar, text="清除", command=self._clear,
            bg="#333", fg="white", relief=tk.FLAT, padx=6
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

        # 標籤顏色設定
        self.text_widget.tag_config("time",        foreground="#666666", font=("微軟正黑體", 10))
        self.text_widget.tag_config("japanese",    foreground="#aaddff", font=("微軟正黑體", config.FONT_SIZE - 2))
        self.text_widget.tag_config("translation", foreground="#ffffff", font=("微軟正黑體", config.FONT_SIZE, "bold"))
        self.text_widget.tag_config("separator",   foreground="#333333")

        # 允許拖曳視窗
        toolbar.bind("<ButtonPress-1>",   self._start_drag)
        toolbar.bind("<B1-Motion>",       self._do_drag)

        # 開始輪詢翻譯結果
        self._poll_results()

    # ── 拖曳視窗 ──────────────────────────────────────────
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    # ── 清除字幕 ──────────────────────────────────────────
    def _clear(self):
        self.lines.clear()
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.config(state=tk.DISABLED)

    # ── 新增一筆翻譯到畫面 ────────────────────────────────
    def _append_result(self, result: dict):
        now = datetime.now().strftime("%H:%M:%S")
        self.text_widget.config(state=tk.NORMAL)

        if self.text_widget.get("1.0", tk.END).strip():
            self.text_widget.insert(tk.END, "\n", "separator")

        self.text_widget.insert(tk.END, f"[{now}] ", "time")
        self.text_widget.insert(tk.END, f"{result['original']}\n", "japanese")
        self.text_widget.insert(tk.END, f"▶ {result['translation']}", "translation")

        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)   # 自動捲動到最下方

        # 超過行數限制時刪除最舊的內容
        total_lines = int(self.text_widget.index("end-1c").split(".")[0])
        max_display = config.MAX_LINES * 3  # 每筆約佔3行
        if total_lines > max_display:
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete("1.0", f"{total_lines - max_display}.0")
            self.text_widget.config(state=tk.DISABLED)

    # ── 輪詢 queue，將結果送到 UI ─────────────────────────
    def _poll_results(self):
        try:
            while True:
                result = self.result_queue.get_nowait()
                self._append_result(result)
                self.status_var.set(f"✅ 最後更新 {datetime.now().strftime('%H:%M:%S')}")
        except queue.Empty:
            pass
        finally:
            # 每 200ms 再次檢查
            self.root.after(200, self._poll_results)

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

    # 建立各模組之間的 Queue（溝通管道）
    audio_queue  = queue.Queue(maxsize=5)   # 防止堆積太多音訊片段
    text_queue   = queue.Queue()
    result_queue = queue.Queue()

    # 初始化各模組
    capture    = AudioCapture(audio_queue)
    transcriber = Transcriber(audio_queue, text_queue)
    translator  = Translator(text_queue, result_queue)

    # 啟動背景執行緒
    capture.start()
    transcriber.start()
    translator.start()

    logger.info("✅ 所有模組已啟動，開始監聽 CABLE 音訊...")

    # 建立並執行字幕視窗（主執行緒）
    try:
        window = SubtitleWindow(result_queue)
        window.run()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("🛑 正在關閉所有模組...")
        capture.stop()
        transcriber.stop()
        translator.stop()
        logger.info("👋 程式結束")


if __name__ == "__main__":
    main()
