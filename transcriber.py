# ============================================================
#  transcriber.py  ─  OpenAI Whisper 語音辨識
# ============================================================

import io
import re
import wave
import queue
import threading
import logging

from openai import OpenAI
import config

logger = logging.getLogger(__name__)

# ── Whisper 常見幻覺句子黑名單 ────────────────────────────
HALLUCINATION_BLACKLIST = [
    "ご視聴ありがとうございました",
    "ありがとうございました",
    "チャンネル登録",
    "高評価",
    "よろしくお願いします",
    "よろしくお願いいたします",
    "お願いします",
    "お願いいたします",
    "字幕は自動生成",
    "自動字幕",
    "概要欄",
    "Thank you for watching",
    "Please subscribe",
    "ご覧いただきありがとう",
    "またね",
    "バイバイ",
]

MIN_TEXT_LENGTH = 4


def _is_hallucination(text: str) -> bool:
    text_clean = text.strip()
    if len(text_clean) < MIN_TEXT_LENGTH:
        return True
    for phrase in HALLUCINATION_BLACKLIST:
        if phrase in text_clean:
            return True
    if re.fullmatch(r"[。、！？!?…・\s\-\.]+", text_clean):
        return True
    return False


def _bytes_to_wav(audio_bytes: bytes) -> io.BytesIO:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(config.CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(config.SAMPLE_RATE)
        wf.writeframes(audio_bytes)
    buf.seek(0)
    buf.name = "audio.wav"
    return buf


class Transcriber:
    def __init__(self, audio_queue: queue.Queue, text_queue: queue.Queue):
        self.audio_queue = audio_queue
        self.text_queue = text_queue
        self._stop_event = threading.Event()
        self._thread = None
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def _transcribe_loop(self):
        logger.info("📝 Whisper 辨識器啟動")
        while not self._stop_event.is_set():
            try:
                audio_bytes = self.audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                wav_file = _bytes_to_wav(audio_bytes)
                response = self.client.audio.transcriptions.create(
                    model=config.STT_MODEL,
                    file=wav_file,
                    language="ja",
                    response_format="text",
                )
                text = response.strip()

                if not text:
                    continue
                if _is_hallucination(text):
                    logger.debug(f"🚫 幻覺過濾：{text}")
                    continue

                logger.info(f"辨識結果：{text}")
                self.text_queue.put(text)

            except Exception as e:
                logger.error(f"Whisper API 錯誤：{e}")

    def start(self):
        self._thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
