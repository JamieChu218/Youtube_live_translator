# ============================================================
#  main.py  ─  程式入口
#
#  組裝流程：首次精靈（如需）→ Pipeline + SubtitleWindow → mainloop
#  各元件職責：
#    pipeline.py         管線（Router 分流 + 模組生命週期）
#    subtitle_window.py  字幕視窗
#    settings_window.py  ⚙ 設定視窗
#    wizard.py           首次啟動精靈
#
#  使用方式：
#    python main.py                 # 正常啟動（首次會進設定精靈）
#    python main.py --list-devices  # 列出所有音訊裝置
# ============================================================

import queue
import logging
import argparse
import threading

import config
from audio_capture import list_devices
from pipeline import Pipeline
from subtitle_window import SubtitleWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


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

    # ── 首次啟動精靈 ──
    if config.is_first_run():
        from wizard import run_wizard
        if not run_wizard():
            logger.info("使用者取消精靈，程式結束")
            return

    subtitle_only = threading.Event()   # 未設定 = 翻譯模式
    result_queue = queue.Queue()

    pipeline = Pipeline(result_queue, subtitle_only)
    window = SubtitleWindow(result_queue, subtitle_only, pipeline)

    ok, err = pipeline.start()
    if not ok:
        window.show_system_message(f"❌ {err}")

    try:
        window.run()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("🛑 正在關閉...")
        pipeline.stop()
        logger.info("👋 程式結束")


if __name__ == "__main__":
    main()
