# ============================================================
#  wizard.py  ─  首次啟動設定精靈
#
#  流程：歡迎(VB-CABLE 說明) → API Key(需測試通過) → 選裝置 → 完成
#  完成時寫入 settings.json；使用者關窗/取消回傳 False。
# ============================================================

import threading
import webbrowser
import logging

import customtkinter as ctk

import config
import theme
from ui_common import device_choices, find_cable_display, test_api_key

logger = logging.getLogger(__name__)

VB_CABLE_URL = "https://vb-audio.com/Cable/"


def run_wizard() -> bool:
    theme.apply()
    root = ctk.CTk(fg_color=theme.BG)
    root.title("🎌 初次設定精靈")

    w, h = 640, 480
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.resizable(False, False)

    state = {
        "ok": False,
        "key_verified": config.api_key_from_env(),  # env/.env 已有 key 免驗證
        "step": 0,
    }
    device_map = {}

    # ── 版面骨架 ──
    header = ctk.CTkLabel(root, text="", font=(theme.FONT_FAMILY, 20, "bold"),
                          text_color=theme.TEXT_MAIN)
    header.pack(pady=(24, 4))
    sub = ctk.CTkLabel(root, text="", font=(theme.FONT_FAMILY, 12),
                       text_color=theme.TEXT_DIM)
    sub.pack()

    body = ctk.CTkFrame(root, fg_color=theme.PANEL, corner_radius=12)
    body.pack(fill="both", expand=True, padx=28, pady=16)

    btn_row = ctk.CTkFrame(root, fg_color="transparent")
    btn_row.pack(fill="x", padx=28, pady=(0, 20))
    back_btn = ctk.CTkButton(btn_row, text="上一步", width=90,
                             font=(theme.FONT_FAMILY, 13),
                             fg_color=theme.PANEL_2, hover_color=theme.BORDER)
    back_btn.pack(side="left")
    next_btn = ctk.CTkButton(btn_row, text="下一步", width=110,
                             font=(theme.FONT_FAMILY, 13),
                             fg_color=theme.ACCENT)
    next_btn.pack(side="right")

    steps = []          # [(建立函式, frame), ...]
    frames = []

    def _clear_body():
        for child in body.winfo_children():
            child.destroy()

    # ── 步驟 1：歡迎 ──
    def build_welcome():
        _clear_body()
        header.configure(text="歡迎使用 日文直播即時翻譯")
        sub.configure(text="步驟 1 / 3　─　開始之前")
        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 13), text_color=theme.TEXT_MAIN,
            text=(
                "\n這個工具會擷取電腦正在播放的日文直播聲音，"
                "即時辨識並翻譯成繁體中文字幕。\n\n"
                "使用前需要：\n\n"
                "  ①  安裝 VB-CABLE 虛擬音效裝置（免費）\n"
                "       並把要翻譯的聲音輸出設為「CABLE Input」\n\n"
                "  ②  一把 OpenAI API Key（下一步填入）\n"
            ),
        ).pack(anchor="w", padx=24, pady=(8, 0))

        link = ctk.CTkLabel(body, text="🔗 下載 VB-CABLE（vb-audio.com/Cable）",
                            font=(theme.FONT_FAMILY, 13, "underline"),
                            text_color=theme.ACCENT, cursor="hand2")
        link.pack(anchor="w", padx=24, pady=(4, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(VB_CABLE_URL))

    # ── 步驟 2：API Key ──
    def build_api_key():
        _clear_body()
        header.configure(text="設定 OpenAI API Key")
        sub.configure(text="步驟 2 / 3　─　連線驗證")

        if config.api_key_from_env():
            ctk.CTkLabel(
                body, justify="left", wraplength=520,
                font=(theme.FONT_FAMILY, 13), text_color=theme.GOOD,
                text="\n✅ 已偵測到環境變數 / .env 中的 API Key，此步驟可直接跳過。",
            ).pack(anchor="w", padx=24, pady=(16, 0))
            state["key_verified"] = True
            return

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 13), text_color=theme.TEXT_MAIN,
            text="\n請貼上你的 OpenAI API Key（sk- 開頭），並按「測試連線」驗證：",
        ).pack(anchor="w", padx=24, pady=(8, 6))

        entry = ctk.CTkEntry(body, show="•", font=("Consolas", 12),
                             placeholder_text="sk-...")
        entry.pack(fill="x", padx=24)
        if config._settings.get("API_KEY"):
            entry.insert(0, config._settings["API_KEY"])

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        status = ctk.CTkLabel(row, text="", font=(theme.FONT_FAMILY, 12),
                              text_color=theme.TEXT_DIM)

        def do_test():
            key = entry.get().strip()
            status.configure(text="測試中...", text_color=theme.TEXT_DIM)

            def worker():
                ok, msg = test_api_key(key)

                def done():
                    status.configure(text=msg,
                                     text_color=theme.GOOD if ok else theme.DANGER)
                    if ok:
                        state["key_verified"] = True
                        state["api_key"] = key
                root.after(0, done)

            threading.Thread(target=worker, daemon=True).start()

        ctk.CTkButton(row, text="測試連線", width=90, height=28,
                      font=(theme.FONT_FAMILY, 12),
                      fg_color=theme.ACCENT, command=do_test).pack(side="left")
        status.pack(side="left", padx=10)

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_DIM,
            text="Key 會儲存在你電腦的使用者設定檔中，不會上傳到其他地方。",
        ).pack(anchor="w", padx=24, pady=(6, 0))

    # ── 步驟 3：音訊裝置 ──
    def build_device():
        _clear_body()
        header.configure(text="選擇音訊輸入裝置")
        sub.configure(text="步驟 3 / 3　─　最後一步")

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 13), text_color=theme.TEXT_MAIN,
            text="\n選擇 VB-CABLE 的「CABLE Output」裝置（已自動偵測預選）：",
        ).pack(anchor="w", padx=24, pady=(8, 6))

        choices = device_choices()
        device_map.clear()
        device_map.update(dict(choices))
        displays = [d for d, _ in choices]

        menu = ctk.CTkOptionMenu(body, values=displays, width=480,
                                 font=(theme.FONT_FAMILY, 12),
                                 fg_color=theme.PANEL_2,
                                 button_color=theme.ACCENT)
        menu.pack(anchor="w", padx=24)
        cable = find_cable_display(choices)
        menu.set(cable if cable else displays[0])
        state["device_menu"] = menu

        if not cable:
            ctk.CTkLabel(
                body, justify="left", wraplength=520,
                font=(theme.FONT_FAMILY, 12), text_color=theme.WARN,
                text="⚠️ 未偵測到 CABLE 裝置。若尚未安裝 VB-CABLE，"
                     "可先選「自動偵測」，安裝後重新啟動程式即可。",
            ).pack(anchor="w", padx=24, pady=(8, 0))

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_DIM,
            text="提醒：這裡只是選擇程式要「聽」哪個裝置，不會更改系統音訊設定。\n"
                 "要讓聲音進得來，請把播放來源的輸出設為「CABLE Input」——\n"
                 "可在 Windows 音量混合器對單一程式（如瀏覽器）設定，"
                 "或將系統預設輸出改為 CABLE Input。",
        ).pack(anchor="w", padx=24, pady=(10, 0))

    steps.extend([build_welcome, build_api_key, build_device])

    # ── 導覽 ──
    def show_step(i):
        state["step"] = i
        steps[i]()
        back_btn.configure(state="normal" if i > 0 else "disabled")
        next_btn.configure(text="完成 ✓" if i == len(steps) - 1 else "下一步")

    def on_next():
        i = state["step"]
        if i == 1 and not state["key_verified"]:
            return  # API key 未驗證不能前進（按鈕提示已在畫面）
        if i < len(steps) - 1:
            show_step(i + 1)
        else:
            finish()

    def on_back():
        if state["step"] > 0:
            show_step(state["step"] - 1)

    def finish():
        updates = {}
        if state.get("api_key"):
            updates["API_KEY"] = state["api_key"]
        menu = state.get("device_menu")
        if menu is not None:
            updates["CABLE_DEVICE_INDEX"] = device_map.get(menu.get())
        config.save(updates)   # 即使空 dict 也會建立 settings.json（結束首次精靈狀態）
        state["ok"] = True
        logger.info("🧙 首次設定完成")
        root.destroy()

    next_btn.configure(command=on_next)
    back_btn.configure(command=on_back)

    show_step(0)
    root.mainloop()
    return state["ok"]
