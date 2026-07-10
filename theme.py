# ============================================================
#  theme.py  ─  UI 配色與字型常數（唯一的外觀真相來源）
# ============================================================

import customtkinter as ctk

FONT_FAMILY = "微軟正黑體"

# ── 介面主色（深色系）─────────────────────────────────────
BG        = "#0b0e14"   # 視窗底色
PANEL     = "#141926"   # 工具列 / 面板
PANEL_2   = "#1b2233"   # hover / 次面板
ACCENT    = "#3b82f6"   # 主要按鈕（翻譯模式・藍）
ACCENT_2  = "#a855f7"   # 字幕模式・紫
GOOD      = "#2ecc71"
WARN      = "#f39c12"
DANGER    = "#e74c3c"
TEXT_MAIN = "#f5f7fa"
TEXT_DIM  = "#8b93a7"
BORDER    = "#232b3d"

# ── 字幕文字框 tag 顏色 ───────────────────────────────────
TAG_TIME        = "#5c6478"
TAG_JAPANESE    = "#9fc9ff"
TAG_TRANSLATION = "#ffffff"
TAG_SYSTEM      = "#f39c12"   # 系統訊息（錯誤/提示）
TAG_SEPARATOR   = "#333a4d"


def apply():
    """套用全域 CustomTkinter 主題，建立任何視窗前呼叫一次。"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
