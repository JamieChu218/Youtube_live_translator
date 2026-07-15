# ============================================================
#  config.py  ─  設定管理
#
#  兩層設計：
#    1. DEFAULTS       ── 內建預設值（程式碼裡的唯一真相）
#    2. settings.json  ── 使用者設定檔（%APPDATA%\YoutubeLiveTranslator\），
#                         由設定視窗 / 首次精靈寫入，覆蓋預設值
#
#  其他模組照舊以屬性讀取：config.STT_MODEL、config.PAUSE_SECONDS ...
#
#  API key 優先序：環境變數 OPENAI_API_KEY → 專案 .env（開發用）
#                 → settings.json 的 API_KEY（一般使用者由 UI 填入）
# ============================================================

import os
import json

APP_NAME = "YoutubeLiveTranslator"
APP_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME
)
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
LOG_PATH = os.path.join(APP_DIR, "translator.log")

os.makedirs(APP_DIR, exist_ok=True)


# ── 內建預設值 ────────────────────────────────────────────
DEFAULTS = {
    # 音訊擷取
    "CABLE_DEVICE_INDEX": None,   # None = 自動偵測含 "CABLE" 的裝置
    "SAMPLE_RATE": 16000,         # Whisper 建議 16 kHz
    "CHANNELS": 1,                # 單聲道
    "CHUNK_SECONDS": 5,           # 斷句的最長上限（秒）
    "SILENCE_THRESHOLD": 200,     # 音量低於此值視為靜音
    "AUDIO_QUEUE_MAXSIZE": 5,     # 音訊佇列上限；滿了丟最舊塊

    # 動態斷句
    "USE_DYNAMIC_SEGMENTATION": True,
    "PAUSE_SECONDS": 0.6,         # 連續靜音達此長度即斷句
    "MIN_SPEECH_SECONDS": 0.8,    # 語音至少要這麼長才送出

    # 辨識
    "STT_MODEL": "gpt-4o-mini-transcribe",   # 可改回 "whisper-1"
    "STT_WORKERS": 3,             # 並行辨識 worker 數

    # 翻譯
    "SOURCE_LANG": "日文",
    "TARGET_LANG": "繁體中文",
    "GPT_MODEL": "gpt-4o-mini",

    # 字幕視窗
    "WINDOW_OPACITY": 0.88,
    "FONT_SIZE": 18,
    "MAX_LINES": 6,
    "WINDOW_WIDTH": 900,
    "WINDOW_HEIGHT": 300,
    "WINDOW_X": None,          # None = 使用預設位置;關閉視窗時自動記錄
    "WINDOW_Y": None,
    "CLICK_THROUGH": False,    # 點擊穿透模式(滑鼠穿過字幕視窗)
    "POLL_INTERVAL_MS": 60,

    # 術語對照表:一行一組「原文=譯文」,# 開頭為註解;空白時對翻譯零影響
    "GLOSSARY": "",

    # UI 填入的 API key（僅當環境變數與 .env 都沒有時使用）
    "API_KEY": "",
}

_settings = {}   # settings.json 的實際內容（只存使用者改過的鍵）


def _read_env_api_key():
    """環境變數 → 專案 .env（開發用途），找不到回傳 None。"""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key

    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    name, value = line.split("=", 1)
                    if name.strip() == "OPENAI_API_KEY":
                        return value.strip().strip('"').strip("'")
        except OSError:
            pass
    return None


def _resolve_api_key():
    return _read_env_api_key() or (_settings.get("API_KEY") or None)


def load():
    """讀取 settings.json，套用到模組屬性（預設值 ← 使用者覆蓋）。"""
    global _settings
    data = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError):
            data = {}
    _settings = data

    g = globals()
    for key, default in DEFAULTS.items():
        g[key] = data.get(key, default)
    g["OPENAI_API_KEY"] = _resolve_api_key()


def save(updates: dict):
    """把使用者變更寫入 settings.json 並立即重新載入。"""
    for key, value in updates.items():
        if key in DEFAULTS:
            _settings[key] = value
    os.makedirs(APP_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(_settings, f, ensure_ascii=False, indent=2)
    load()


def get_saved(key: str, default=""):
    """讀取 settings.json 中已儲存的值（不含內建預設），UI 模組請用這個而非 _settings。"""
    return _settings.get(key, default)


def is_first_run() -> bool:
    """settings.json 不存在，或完全沒有可用的 API key → 需要首次精靈。"""
    return (not os.path.exists(SETTINGS_PATH)) or (OPENAI_API_KEY is None)


def api_key_from_env() -> bool:
    """API key 是否來自環境變數/.env（此時設定視窗顯示唯讀提示）。"""
    return _read_env_api_key() is not None


# 模組載入時即讀取一次
load()
