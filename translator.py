# ============================================================
#  translator.py  ─  GPT 日文 → 繁體中文 翻譯
# ============================================================

import queue
import threading
import logging

from openai import OpenAI
import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""你是一位專業的即時口譯員，專門翻譯 YouTube 日文直播的{config.SOURCE_LANG}內容。

請遵守以下規則：
1. 將輸入的{config.SOURCE_LANG}翻譯成自然流暢的{config.TARGET_LANG}
2. 保留直播常見的語氣詞與情緒（如笑聲、驚嘆等）
3. 遊戲術語、人名、角色名稱可保留原文並加括號標示
4. 只輸出翻譯結果，不要加任何解釋或前綴
5. 若輸入不是{config.SOURCE_LANG}或無法翻譯，回傳空字串"""


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

    def _translate_loop(self):
        logger.info("🌐 翻譯器啟動")
        while not self._stop_event.is_set():
            try:
                japanese_text = self.text_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                response = self.client.chat.completions.create(
                    model=config.GPT_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": japanese_text},
                    ],
                    temperature=0.3,
                    max_tokens=300,
                )
                translation = response.choices[0].message.content.strip()
                if translation:
                    logger.info(f"翻譯結果：{translation}")
                    self.result_queue.put({
                        "original": japanese_text,
                        "translation": translation,
                    })

            except Exception as e:
                logger.error(f"GPT 翻譯錯誤：{e}")

    def start(self):
        self._thread = threading.Thread(target=self._translate_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
