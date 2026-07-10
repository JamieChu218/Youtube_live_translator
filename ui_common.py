# ============================================================
#  ui_common.py  ─  設定視窗與首次精靈共用的小工具
# ============================================================

import logging

logger = logging.getLogger(__name__)


def device_choices():
    """
    回傳輸入裝置清單 [(顯示文字, 裝置索引或 None), ...]，
    第一項固定為「自動偵測」。顯示文字含索引前綴，保證唯一。
    """
    import sounddevice as sd
    choices = [("自動偵測（含 CABLE 的裝置）", None)]
    try:
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                choices.append((f"[{i}] {dev['name']}", i))
    except Exception as e:
        logger.error(f"列出音訊裝置失敗：{e}")
    return choices


def find_cable_display(choices):
    """從 device_choices() 結果中找出第一個含 CABLE 的顯示文字，找不到回傳 None。"""
    for display, idx in choices:
        if idx is not None and "CABLE" in display.upper():
            return display
    return None


def test_api_key(key: str, timeout: float = 10):
    """
    以最輕量的 API 呼叫驗證 key。回傳 (成功與否, 訊息)。
    會阻塞，呼叫端請放在背景執行緒。
    """
    key = (key or "").strip()
    if not key:
        return False, "請先輸入 API Key"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key, timeout=timeout)
        client.models.list()
        return True, "✅ 連線成功"
    except Exception as e:
        msg = str(e)
        if "401" in msg or "invalid_api_key" in msg.lower() or "incorrect api key" in msg.lower():
            return False, "❌ API Key 無效"
        return False, f"❌ 連線失敗：{msg[:80]}"
