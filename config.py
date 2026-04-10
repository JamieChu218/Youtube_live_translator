# ============================================================
#  config.py  ─  設定檔
#  請在這裡填入你的 OpenAI API Key 以及選擇音訊裝置
# ============================================================

OPENAI_API_KEY = "REDACTED-OLD-KEY-REVOKED"   # ← 填入你的 API Key

# --- 音訊擷取設定 ---
# 執行 main.py 時加上 --list-devices 參數可以列出所有裝置編號
CABLE_DEVICE_INDEX = 1   # None = 自動偵測含 "CABLE" 的裝置；或直接填數字如 3

SAMPLE_RATE      = 16000    # Whisper 建議 16 kHz
CHANNELS         = 1        # 單聲道
CHUNK_SECONDS    = 5        # 每幾秒送一次辨識（建議 4~8）
SILENCE_THRESHOLD = 200     # 音量低於此值視為靜音，不送辨識（節省費用）

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
