# ============================================================
#  audio_capture.py  ─  從 CABLE Output 擷取音訊
# ============================================================

import sounddevice as sd
import numpy as np
import threading
import queue
import time
import logging

import config

logger = logging.getLogger(__name__)


def list_devices():
    """列出所有音訊裝置，方便使用者找到 CABLE 的編號"""
    devices = sd.query_devices()
    print("\n📋 可用音訊裝置列表：")
    print("-" * 60)
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            print(f"  [{i:2d}] 🎤 輸入  {dev['name']}")
    print("-" * 60)


def find_cable_device():
    """自動搜尋含有 'CABLE' 關鍵字的輸入裝置"""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0 and "CABLE" in dev["name"].upper():
            logger.info(f"自動偵測到 CABLE 裝置：[{i}] {dev['name']}")
            return i
    return None


class AudioCapture:
    """
    以背景執行緒持續從 CABLE 裝置讀取音訊，
    將每個 CHUNK_SECONDS 的片段放入 audio_queue。
    """

    def __init__(self, audio_queue: queue.Queue):
        self.audio_queue = audio_queue
        self._stop_event = threading.Event()
        self._thread = None

        # 決定裝置編號
        if config.CABLE_DEVICE_INDEX is not None:
            self.device_index = config.CABLE_DEVICE_INDEX
        else:
            self.device_index = find_cable_device()
            if self.device_index is None:
                raise RuntimeError(
                    "❌ 找不到 CABLE 裝置！請執行 main.py --list-devices 查看裝置列表，"
                    "並在 config.py 中手動設定 CABLE_DEVICE_INDEX。"
                )

        self.chunk_frames = int(config.SAMPLE_RATE * config.CHUNK_SECONDS)

        # 供 UI 顯示音訊狀態（callback 單純覆寫 float/時戳，不需鎖）
        self.current_rms = 0.0
        self.last_audio_time = time.monotonic()

    def _enqueue(self, chunk_bytes: bytes):
        """
        非阻塞放入 audio_queue：絕對不能在音訊 callback 裡 block（會造成爆音/掉字）。
        佇列滿代表辨識跟不上 → 丟掉最舊的塊、保留最新，避免延遲越積越多。
        """
        try:
            self.audio_queue.put_nowait(chunk_bytes)
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.audio_queue.put_nowait(chunk_bytes)
            except queue.Full:
                pass
            logger.warning("⚠️ 辨識跟不上，丟棄最舊音訊塊以維持即時性")

    @staticmethod
    def _to_int16_bytes(blocks: list) -> bytes:
        audio_np = np.concatenate(blocks, axis=0)
        mono = audio_np[:, 0] if audio_np.ndim > 1 else audio_np
        return (mono * 32767).astype(np.int16).tobytes()

    def _make_fixed_callback(self):
        """固定每 CHUNK_SECONDS 切一塊（Phase 1 行為，保留為後備）。"""
        state = {"buffer": [], "size": 0}

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"音訊狀態警告：{status}")
            state["buffer"].append(indata.copy())
            state["size"] += frames

            if state["size"] >= self.chunk_frames:
                blocks = state["buffer"]
                state["buffer"], state["size"] = [], 0

                chunk_bytes = self._to_int16_bytes(blocks)
                rms = np.sqrt(np.mean(np.frombuffer(chunk_bytes, np.int16).astype(np.float32) ** 2))
                self.current_rms = float(rms)
                if rms < config.SILENCE_THRESHOLD:
                    logger.debug(f"靜音跳過 (RMS={rms:.1f})")
                    return
                self.last_audio_time = time.monotonic()
                self._enqueue(chunk_bytes)

        return callback

    def _make_dynamic_callback(self):
        """
        動態斷句：以每個 callback 區塊（~64ms）為單位做能量 VAD。
        - 偵測到語音 → 累積
        - 句中/句尾靜音累計達 PAUSE_SECONDS → 斷句送出
        - 沒停頓時最多累積到 CHUNK_SECONDS(5s) → 強制斷句
        - 前導靜音直接丟棄，不累積
        """
        max_frames   = int(config.SAMPLE_RATE * config.CHUNK_SECONDS)
        pause_frames = int(config.SAMPLE_RATE * config.PAUSE_SECONDS)
        min_frames   = int(config.SAMPLE_RATE * config.MIN_SPEECH_SECONDS)

        # total = 全部已累積（含尾端靜音，用於 5s 上限與音訊長度）
        # speech = 只計語音（用於最短長度門檻，避免被尾端靜音灌水）
        state = {"blocks": [], "total": 0, "speech": 0, "silence": 0}

        def emit():
            if state["speech"] >= min_frames:
                self._enqueue(self._to_int16_bytes(state["blocks"]))
            else:
                logger.debug(f"片段語音過短跳過 (speech={state['speech']} frames)")
            state["blocks"], state["total"], state["speech"], state["silence"] = [], 0, 0, 0

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"音訊狀態警告：{status}")

            block = indata.copy()
            mono = block[:, 0] if block.ndim > 1 else block
            rms = np.sqrt(np.mean((mono * 32767).astype(np.float32) ** 2))
            is_speech = rms >= config.SILENCE_THRESHOLD

            self.current_rms = float(rms)
            if is_speech:
                self.last_audio_time = time.monotonic()

            if is_speech:
                state["blocks"].append(block)
                state["total"] += frames
                state["speech"] += frames
                state["silence"] = 0
            elif state["total"] > 0:
                # 句中或句尾的靜音：保留一點點當自然停頓，並累計靜音長度
                state["blocks"].append(block)
                state["total"] += frames
                state["silence"] += frames
                if state["silence"] >= pause_frames:
                    emit()
                    return
            # else：還沒開始講話的前導靜音 → 丟棄

            # 沒停頓但已達 5s 上限 → 強制斷句
            if state["total"] >= max_frames:
                emit()

        return callback

    def _capture_loop(self):
        if config.USE_DYNAMIC_SEGMENTATION:
            logger.info("🎙️ 開始擷取音訊（動態斷句）...")
            callback = self._make_dynamic_callback()
        else:
            logger.info("🎙️ 開始擷取音訊（固定切塊）...")
            callback = self._make_fixed_callback()

        with sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=self.device_index,
            callback=callback,
            blocksize=1024,
        ):
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.1)

        logger.info("🎙️ 音訊擷取已停止")

    def start(self):
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
