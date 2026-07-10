# ============================================================
#  pipeline.py  ─  翻譯管線：Router 分流 + Pipeline 生命週期管理
#
#  資料流：
#    AudioCapture → audio_queue
#    Transcriber  → text_queue
#    Router       → translate_queue（翻譯模式）或 result_queue（字幕模式）
#    Translator   → result_queue
# ============================================================

import queue
import logging
import threading

import config
from audio_capture import AudioCapture
from transcriber import Transcriber
from translator import Translator

logger = logging.getLogger(__name__)


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


class Pipeline:
    """
    包裝 AudioCapture / Transcriber / Translator / Router 的生命週期。
    設定變更後呼叫 restart() 以新設定重建所有模組。
    result_queue 由外部（字幕視窗）持有，重啟時不重建。
    """

    def __init__(self, result_queue: queue.Queue, subtitle_only: threading.Event):
        self.result_queue  = result_queue
        self.subtitle_only = subtitle_only
        self._modules = []
        self.running = False

    def start(self):
        """回傳 (成功與否, 錯誤訊息)。"""
        if self.running:
            return True, None
        if not config.OPENAI_API_KEY:
            return False, "尚未設定 OpenAI API Key，請開啟「⚙ 設定」填入。"

        try:
            audio_queue     = queue.Queue(maxsize=config.AUDIO_QUEUE_MAXSIZE)
            text_queue      = queue.Queue()
            translate_queue = queue.Queue()

            capture     = AudioCapture(audio_queue)   # 找不到裝置會 raise RuntimeError
            transcriber = Transcriber(audio_queue, text_queue)
            translator  = Translator(translate_queue, self.result_queue)
            router      = Router(text_queue, translate_queue,
                                 self.result_queue, self.subtitle_only)
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            logger.exception("管線初始化失敗")
            return False, f"管線初始化失敗：{e}"

        self._modules = [capture, transcriber, translator, router]
        for m in self._modules:
            m.start()
        self.running = True
        logger.info("✅ 管線已啟動")
        return True, None

    def stop(self):
        for m in self._modules:
            try:
                m.stop()
            except Exception:
                logger.exception("模組停止時發生錯誤")
        self._modules = []
        self.running = False
        logger.info("🛑 管線已停止")

    def restart(self):
        """以目前 config 重建整條管線。回傳 (成功與否, 錯誤訊息)。"""
        self.stop()
        return self.start()
