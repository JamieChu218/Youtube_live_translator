# ============================================================
#  audio_capture.py  ─  從 CABLE Output 擷取音訊
# ============================================================

import sounddevice as sd
import numpy as np
import threading
import queue
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

    def _capture_loop(self):
        logger.info("🎙️ 開始擷取音訊...")

        buffer = []
        buffer_size = 0

        def callback(indata, frames, time_info, status):
            nonlocal buffer, buffer_size
            if status:
                logger.warning(f"音訊狀態警告：{status}")
            buffer.append(indata.copy())
            buffer_size += frames

            if buffer_size >= self.chunk_frames:
                audio_np = np.concatenate(buffer, axis=0)
                buffer = []
                buffer_size = 0

                # 轉為單聲道 int16
                mono = audio_np[:, 0] if audio_np.ndim > 1 else audio_np
                mono_int16 = (mono * 32767).astype(np.int16)

                # 靜音偵測
                rms = np.sqrt(np.mean(mono_int16.astype(np.float32) ** 2))
                if rms < config.SILENCE_THRESHOLD:
                    logger.debug(f"靜音跳過 (RMS={rms:.1f})")
                    return

                self.audio_queue.put(mono_int16.tobytes())

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
