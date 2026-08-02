# ============================================================
#  wizard.py  ─  首次啟動設定精靈
#
#  流程：歡迎(VB-CABLE 說明) → API Key(需測試通過) → 選裝置 → 完成
#  完成時寫入 settings.json；使用者關窗/取消回傳 False。
# ============================================================

import webbrowser
import logging

import customtkinter as ctk

import config
import theme
import i18n
from i18n import t
from ui_common import device_choices, find_cable_display, test_api_key_async

logger = logging.getLogger(__name__)

VB_CABLE_URL = "https://vb-audio.com/Cable/"


def run_wizard() -> bool:
    theme.apply()
    root = ctk.CTk(fg_color=theme.BG)
    root.title(t("wizard.title"))

    w, h = 640, 480
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.resizable(False, False)

    state = {
        "ok": False,
        "key_verified": config.api_key_from_env(),  # env/.env 已有 key 免驗證
        "step": 0,
        "ui_language": i18n.get_language(),
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
    back_btn = ctk.CTkButton(btn_row, text=t("wizard.back"), width=90,
                             font=(theme.FONT_FAMILY, 13),
                             fg_color=theme.PANEL_2, hover_color=theme.BORDER)
    back_btn.pack(side="left")
    next_btn = ctk.CTkButton(btn_row, text=t("wizard.next"), width=110,
                             font=(theme.FONT_FAMILY, 13),
                             fg_color=theme.ACCENT)
    next_btn.pack(side="right")

    steps = []          # 各步驟的建立函式

    def _clear_body():
        for child in body.winfo_children():
            child.destroy()

    # ── 步驟 1：介面語言 ──
    def build_language():
        _clear_body()
        header.configure(text=t("wizard.lang.header"))
        sub.configure(text=f'{t("wizard.step", n=1, total=4)}　─　{t("wizard.lang.sub")}')
        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 13), text_color=theme.TEXT_MAIN,
            text=t("wizard.lang.body"),
        ).pack(anchor="w", padx=24, pady=(16, 12))

        names = list(i18n.LANGUAGES.values())
        codes = {v: k for k, v in i18n.LANGUAGES.items()}

        def on_pick(display):
            code = codes.get(display, i18n.DEFAULT_LANG)
            state["ui_language"] = code
            i18n.set_language(code)
            build_language()          # 立即以新語言重繪本頁
            _refresh_nav()

        menu = ctk.CTkOptionMenu(
            body, values=names, width=260, command=on_pick,
            font=(theme.FONT_FAMILY, 13),
            fg_color=theme.PANEL_2, button_color=theme.ACCENT)
        menu.set(i18n.LANGUAGES.get(state.get("ui_language", i18n.get_language()),
                                    i18n.LANGUAGES[i18n.DEFAULT_LANG]))
        menu.pack(anchor="w", padx=24)

    # ── 步驟 2：歡迎 ──
    def build_welcome():
        _clear_body()
        header.configure(text=t("wizard.welcome.header"))
        sub.configure(text=f'{t("wizard.step", n=2, total=4)}　─　{t("wizard.welcome.sub")}')
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

        link = ctk.CTkLabel(body, text=t("wizard.welcome.link"),
                            font=(theme.FONT_FAMILY, 13, "underline"),
                            text_color=theme.ACCENT, cursor="hand2")
        link.pack(anchor="w", padx=24, pady=(4, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(VB_CABLE_URL))

    # ── 步驟 2：API Key ──
    def build_api_key():
        _clear_body()
        header.configure(text=t("wizard.key.header"))
        sub.configure(text=f'{t("wizard.step", n=3, total=4)}　─　{t("wizard.key.sub")}')

        if config.api_key_from_env():
            ctk.CTkLabel(
                body, justify="left", wraplength=520,
                font=(theme.FONT_FAMILY, 13), text_color=theme.GOOD,
                text=t("wizard.key.env"),
            ).pack(anchor="w", padx=24, pady=(16, 0))
            state["key_verified"] = True
            return

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 13), text_color=theme.TEXT_MAIN,
            text=t("wizard.key.body"),
        ).pack(anchor="w", padx=24, pady=(8, 6))

        entry = ctk.CTkEntry(body, show="•", font=("Consolas", 12),
                             placeholder_text="sk-...")
        entry.pack(fill="x", padx=24)
        if config.get_saved("API_KEY"):
            entry.insert(0, config.get_saved("API_KEY"))

        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=8)
        status = ctk.CTkLabel(row, text="", font=(theme.FONT_FAMILY, 12),
                              text_color=theme.TEXT_DIM)

        def do_test():
            key = entry.get().strip()
            status.configure(text=t("settings.testing"), text_color=theme.TEXT_DIM)

            def done(ok, msg):
                status.configure(text=msg,
                                 text_color=theme.GOOD if ok else theme.DANGER)
                if ok:
                    state["key_verified"] = True
                    state["api_key"] = key

            test_api_key_async(key, root, done)

        ctk.CTkButton(row, text=t("settings.test_conn"), width=90, height=28,
                      font=(theme.FONT_FAMILY, 12),
                      fg_color=theme.ACCENT, command=do_test).pack(side="left")
        status.pack(side="left", padx=10)

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 11), text_color=theme.TEXT_DIM,
            text=t("wizard.key.note"),
        ).pack(anchor="w", padx=24, pady=(6, 0))

    # ── 步驟 3：音訊裝置 ──
    def build_device():
        _clear_body()
        header.configure(text=t("wizard.device.header"))
        sub.configure(text=f'{t("wizard.step", n=4, total=4)}　─　{t("wizard.device.sub")}')

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 13), text_color=theme.TEXT_MAIN,
            text=t("wizard.device.body"),
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
                text=t("wizard.device.warn"),
            ).pack(anchor="w", padx=24, pady=(8, 0))

        ctk.CTkLabel(
            body, justify="left", wraplength=520,
            font=(theme.FONT_FAMILY, 12), text_color=theme.TEXT_DIM,
            text=t("wizard.device.note"),
        ).pack(anchor="w", padx=24, pady=(10, 0))

    steps.extend([build_language, build_welcome, build_api_key, build_device])

    # ── 導覽 ──
    def _refresh_nav():
        """語言切換後更新視窗標題與導覽按鈕文字。"""
        i = state["step"]
        root.title(t("wizard.title"))
        back_btn.configure(text=t("wizard.back"))
        next_btn.configure(
            text=t("wizard.finish") if i == len(steps) - 1 else t("wizard.next"))

    def show_step(i):
        state["step"] = i
        steps[i]()
        back_btn.configure(state="normal" if i > 0 else "disabled")
        _refresh_nav()

    def on_next():
        i = state["step"]
        if i == 2 and not state["key_verified"]:
            return  # API key 未驗證不能前進（按鈕提示已在畫面）
        if i < len(steps) - 1:
            show_step(i + 1)
        else:
            finish()

    def on_back():
        if state["step"] > 0:
            show_step(state["step"] - 1)

    def finish():
        updates = {"UI_LANGUAGE": state.get("ui_language", i18n.get_language())}
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
