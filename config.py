# ============================================================
#  config.py  ─  設定檔
#  ⚠️ 不要把 API Key 寫死在這裡！請改用環境變數或 .env 檔。
# ============================================================

import os


def _read_api_key():
    """
    依序嘗試取得 OpenAI API Key：
      1. 環境變數 OPENAI_API_KEY
      2. 專案目錄下的 .env 檔（格式：OPENAI_API_KEY=sk-...，已被 .gitignore 排除）
    找不到時回傳 None，讓實際呼叫 API 時才報錯（這樣 --list-devices 仍可使用）。
    """
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                if name.strip() == "OPENAI_API_KEY":
                    return value.strip().strip('"').strip("'")
    return None


OPENAI_API_KEY = _read_api_key()

# --- 音訊擷取設定 ---
# 執行 main.py 時加上 --list-devices 參數可以列出所有裝置編號
CABLE_DEVICE_INDEX = 1   # None = 自動偵測含 "CABLE" 的裝置；或直接填數字如 3

SAMPLE_RATE      = 16000    # Whisper 建議 16 kHz
CHANNELS         = 1        # 單聲道
CHUNK_SECONDS    = 5        # 每幾秒送一次辨識（建議 4~8）
SILENCE_THRESHOLD = 200     # 音量低於此值視為靜音，不送辨識（節省費用）
AUDIO_QUEUE_MAXSIZE = 5     # 音訊佇列上限；滿了會丟棄最舊的塊（避免延遲累積與 callback 阻塞）

# --- 動態斷句（Phase 2）---
# 偵測到停頓就立刻斷句送辨識；沒停頓時最多累積到 CHUNK_SECONDS(5s) 才強制斷句。
USE_DYNAMIC_SEGMENTATION = True   # False = 回到固定 5 秒切塊
PAUSE_SECONDS       = 0.6   # 連續靜音達此長度即斷句（越小越即時，太小會把句子切碎）
MIN_SPEECH_SECONDS  = 0.8   # 一段語音至少要這麼長才送出（過濾雜音/單音）

# --- 辨識設定 ---
# gpt-4o-mini-transcribe：較新、延遲較低、準確度相當；要回到舊版可改回 "whisper-1"
STT_MODEL   = "gpt-4o-mini-transcribe"

# --- 翻譯設定 ---
SOURCE_LANG = "日文"
TARGET_LANG = "繁體中文"
GPT_MODEL   = "gpt-4o-mini"   # 便宜且夠快；如需更準確可改 gpt-4o

# --- 字幕視窗設定 ---
WINDOW_OPACITY  = 0.88          # 0.0 全透明 ~ 1.0 不透明
FONT_SIZE       = 18
MAX_LINES       = 6             # 視窗最多顯示幾行
WINDOW_WIDTH    = 900
WINDOW_HEIGHT   = 300
POLL_INTERVAL_MS = 60           # 字幕視窗輪詢間隔（ms）；越小越即時，60 約等於 16fps
