# ============================================================
#  translator.py  ─  GPT 日文 → 繁體中文 翻譯
# ============================================================

import queue
import threading
import logging

from openai import OpenAI
import config

logger = logging.getLogger(__name__)

class Translator:
    """
    從 text_queue 取出日文文字，
    透過 GPT 翻譯後放入 result_queue。
    """

    def __init__(self, text_queue: queue.Queue, result_queue: queue.Queue):
        self.text_queue = text_queue
        self.result_queue = result_queue
        self._stop_event = threading.Event()
        self._thread = None
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

        # 提示詞在建構時組建（而非模組載入時），
        # 這樣設定視窗變更語言 → 管線重啟後才會真正生效。
        self.system_prompt = f"""你是一位專業的即時口譯員，專門翻譯 YouTube 日文直播的{config.SOURCE_LANG}內容。

請遵守以下規則：
1. 將輸入的{config.SOURCE_LANG}翻譯成自然流暢的{config.TARGET_LANG}
2. 保留直播常見的語氣詞與情緒（如笑聲、驚嘆等）
3. 遊戲術語、人名、角色名稱可保留原文並加括號標示
4. 只輸出翻譯結果，不要加任何解釋或前綴
5. 若輸入不是{config.SOURCE_LANG}或無法翻譯，回傳空字串"""

    def _translate_loop(self):
        logger.info("🌐 翻譯器啟動")
        while not self._stop_event.is_set():
            try:
                japanese_text = self.text_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                stream = self.client.chat.completions.create(
                    model=config.GPT_MODEL,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": japanese_text},
                    ],
                    temperature=0.3,
                    max_tokens=300,
                    stream=True,
                )

                started = False
                pieces = []
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if not delta:
                        continue
                    if not started:
                        # 去掉開頭可能的空白，第一個有內容的 token 才開卡片
                        delta = delta.lstrip()
                        if not delta:
                            continue
                        self.result_queue.put({"type": "start", "original": japanese_text})
                        started = True
                    pieces.append(delta)
                    self.result_queue.put({"type": "delta", "text": delta})

                if started:
                    self.result_queue.put({"type": "end"})
                    logger.info(f"翻譯結果：{''.join(pieces).strip()}")

            except Exception as e:
                logger.error(f"GPT 翻譯錯誤：{e}")

    def start(self):
        self._thread = threading.Thread(target=self._translate_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
