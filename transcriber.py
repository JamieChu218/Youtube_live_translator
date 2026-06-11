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
    """
    並行辨識：多個 worker 同時呼叫 STT API，清空積壓更快；
    結果依序號 (seq) 重排後才送進 text_queue，確保字幕順序正確。

    執行緒組成：
      dispatcher(1) → 讀 audio_queue、配序號、丟進 _work_q
      worker(N)     → 從 _work_q 取出辨識、把 (seq, text) 丟進 _done_q
      committer(1)  → 依 seq 順序把 text 送進 text_queue
    """

    def __init__(self, audio_queue: queue.Queue, text_queue: queue.Queue,
                 num_workers: int = None):
        self.audio_queue = audio_queue
        self.text_queue = text_queue
        self.num_workers = num_workers or getattr(config, "STT_WORKERS", 3)
        self._stop_event = threading.Event()
        self._threads = []
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

        self._work_q = queue.Queue()   # (seq, audio_bytes)
        self._done_q = queue.Queue()   # (seq, text or None)
        self._seq = 0

    # ── 實際呼叫 STT（抽出來方便測試 mock）──────────────
    def _transcribe_one(self, audio_bytes: bytes) -> str:
        wav_file = _bytes_to_wav(audio_bytes)
        response = self.client.audio.transcriptions.create(
            model=config.STT_MODEL,
            file=wav_file,
            language="ja",
            response_format="text",
        )
        return response.strip()

    def _dispatch_loop(self):
        while not self._stop_event.is_set():
            try:
                audio_bytes = self.audio_queue.get(timeout=1)
            except queue.Empty:
                continue
            seq = self._seq
            self._seq += 1
            self._work_q.put((seq, audio_bytes))

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                seq, audio_bytes = self._work_q.get(timeout=1)
            except queue.Empty:
                continue

            text = None
            try:
                raw = self._transcribe_one(audio_bytes)
                if raw and _is_hallucination(raw):
                    logger.debug(f"🚫 幻覺過濾[{seq}]：{raw}")
                elif raw:
                    text = raw
                    logger.info(f"辨識結果[{seq}]：{raw}")
            except Exception as e:
                logger.error(f"Whisper API 錯誤[{seq}]：{e}")

            # 無論成功、空白或出錯都要回報 seq，committer 才能往前推進
            self._done_q.put((seq, text))

    def _commit_loop(self):
        next_seq = 0
        buffer = {}
        while not self._stop_event.is_set():
            try:
                seq, text = self._done_q.get(timeout=1)
            except queue.Empty:
                continue
            buffer[seq] = text
            while next_seq in buffer:
                t = buffer.pop(next_seq)
                next_seq += 1
                if t is not None:
                    self.text_queue.put(t)

    def start(self):
        self._threads = [
            threading.Thread(target=self._dispatch_loop, daemon=True),
            threading.Thread(target=self._commit_loop, daemon=True),
        ]
        for _ in range(self.num_workers):
            self._threads.append(threading.Thread(target=self._worker_loop, daemon=True))
        for t in self._threads:
            t.start()
        logger.info(f"📝 辨識器啟動（{self.num_workers} 並行 worker + 順序重排）")

    def stop(self):
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=5)
