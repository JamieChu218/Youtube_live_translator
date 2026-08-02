# ============================================================
#  i18n.py  ─  介面語言（與「翻譯目標語言」完全獨立）
#
#  用法：
#      from i18n import t
#      ctk.CTkLabel(parent, text=t("settings.title"))
#
#  切換語言：set_language("en") → 之後 t() 回傳英文。
#  找不到鍵時回退到繁中，再找不到就回傳鍵本身（方便發現漏翻）。
# ============================================================

import logging

logger = logging.getLogger(__name__)

DEFAULT_LANG = "zh-TW"

# 顯示名稱一律用該語言自己的寫法，方便使用者在任何介面語言下辨認
LANGUAGES = {
    "zh-TW": "繁體中文",
    "zh-CN": "简体中文",
    "en":    "English",
    "ja":    "日本語",
}

_current = DEFAULT_LANG


STRINGS = {
    # ── 繁體中文 ──────────────────────────────────────────
    "zh-TW": {
        # 字幕視窗
        "app.title":            "🎌 日文直播翻譯",
        "app.header":           "🎌 日文直播即時翻譯",
        "mode.translate":       "翻譯模式",
        "mode.subtitle":        "字幕模式",
        "btn.clear":            "清除",
        "btn.passthrough":      "🖱穿透",
        "status.waiting":       "⏳ 等待音訊...",
        "status.updated":       "更新 {time}",
        "status.resumed":       "▶ 已繼續",
        "status.pausing":       "⏸ 暫停中...",
        "status.paused":        "⏸ 已暫停(不計費)",
        "msg.passthrough_on":   "🖱 點擊穿透已開啟：滑鼠會穿過字幕視窗。按住 Ctrl+Alt 可暫時操作視窗（拖曳/按按鈕）。",
        "msg.no_audio":         "⚠ 已 {seconds} 秒未收到音訊。請確認聲音有輸出到「CABLE Input」（Windows 音量混合器 → 播放程式的輸出裝置）。",
        "msg.settings_saved_paused": "✅ 設定已儲存，將在繼續辨識時生效",
        "msg.settings_applied": "✅ 設定已套用，管線已重新啟動",
        "err.no_api_key":       "尚未設定 OpenAI API Key，請開啟「⚙ 設定」填入。",

        # 設定視窗
        "settings.title":       "⚙ 設定",
        "settings.tab.general": "一般",
        "settings.tab.engine":  "辨識與翻譯",
        "settings.tab.segment": "斷句",
        "settings.tab.appearance": "外觀",
        "settings.save":        "儲存並套用",
        "settings.cancel":      "取消",

        "settings.ui_language": "介面語言",
        "settings.ui_language.hint": "只變更介面文字，不影響字幕翻譯的目標語言。",
        "settings.api_key":     "OpenAI API Key",
        "settings.api_key.env_hint": "已從環境變數 / .env 讀取 API Key（優先於此處設定）。如需更換請修改環境變數，或先移除後再於此填入。",
        "settings.toggle_show": "顯示/隱藏",
        "settings.test_conn":   "測試連線",
        "settings.testing":     "測試中...",
        "settings.device":      "音訊輸入裝置",
        "settings.device.hint": "選擇 VB-CABLE 的 CABLE Output；「自動偵測」會尋找名稱含 CABLE 的裝置。",
        "settings.loading":     "載入中...",

        "settings.stt_model":   "語音辨識模型",
        "settings.stt_model.hint": "gpt-4o-mini-transcribe 延遲較低；帳號無權限時可改回 whisper-1。",
        "settings.workers":     "並行辨識 worker 數",
        "settings.workers.hint": "連續快速說話時清空積壓更快；調小可省 API 用量。",
        "settings.gpt_model":   "翻譯模型",
        "settings.source_lang": "來源語言",
        "settings.target_lang": "目標語言",
        "settings.glossary":    "術語對照表（人名/術語固定譯法）",
        "settings.glossary.hint": "一行一組「原文=譯文」，# 開頭為註解。例：ぺこら=佩可拉。清單空白時對翻譯零影響。",

        "settings.dynamic_seg": "動態斷句（VAD）",
        "settings.dynamic_seg.hint": "偵測到停頓就立刻送出辨識；關閉則固定每「斷句上限」秒切一塊。",
        "settings.pause_sec":   "停頓斷句門檻（秒）",
        "settings.pause_sec.hint": "調大→句子更完整但延遲略增；調小→更即時但可能切碎。",
        "settings.min_speech":  "最短語音長度（秒）",
        "settings.min_speech.hint": "過短的聲音片段不送辨識；調小可保留短應答（如「うん」）。",
        "settings.chunk_sec":   "斷句上限（秒）",
        "settings.silence":     "靜音門檻（音量）",
        "settings.silence.hint": "低於此音量視為靜音；環境雜訊大時調高。",

        "settings.opacity":     "視窗透明度",
        "settings.font_size":   "字級",
        "settings.max_lines":   "最多顯示筆數",
        "settings.appearance.hint": "外觀變更立即生效，不需重啟管線。",

        # API key 驗證
        "api.ok":               "✅ 連線成功",
        "api.invalid":          "❌ API Key 無效",
        "api.failed":           "❌ 連線失敗：{msg}",
        "api.empty":            "請先輸入 API Key",

        # 精靈
        "wizard.title":         "🎌 初次設定精靈",
        "wizard.back":          "上一步",
        "wizard.next":          "下一步",
        "wizard.finish":        "完成 ✓",
        "wizard.step":          "步驟 {n} / {total}",

        "wizard.lang.header":   "選擇介面語言",
        "wizard.lang.sub":      "Language / 语言 / 言語",
        "wizard.lang.body":     "\n請選擇這個程式的介面語言。\n（之後可在「⚙ 設定 → 一般」隨時更改）",

        "wizard.welcome.header": "歡迎使用 日文直播即時翻譯",
        "wizard.welcome.sub":   "開始之前",
        "wizard.welcome.body":  "\n這個工具會擷取電腦正在播放的日文直播聲音，即時辨識並翻譯成字幕。\n\n使用前需要：\n\n  ①  安裝 VB-CABLE 虛擬音效裝置（免費）\n       並把要翻譯的聲音輸出設為「CABLE Input」\n\n  ②  一把 OpenAI API Key（下一步填入）\n",
        "wizard.welcome.link":  "🔗 下載 VB-CABLE（vb-audio.com/Cable）",

        "wizard.key.header":    "設定 OpenAI API Key",
        "wizard.key.sub":       "連線驗證",
        "wizard.key.env":       "\n✅ 已偵測到環境變數 / .env 中的 API Key，此步驟可直接跳過。",
        "wizard.key.body":      "\n請貼上你的 OpenAI API Key（sk- 開頭），並按「測試連線」驗證：",
        "wizard.key.note":      "Key 會儲存在你電腦的使用者設定檔中，不會上傳到其他地方。",

        "wizard.device.header": "選擇音訊輸入裝置",
        "wizard.device.sub":    "最後一步",
        "wizard.device.body":   "\n選擇 VB-CABLE 的「CABLE Output」裝置（已自動偵測預選）：",
        "wizard.device.warn":   "⚠️ 未偵測到 CABLE 裝置。若尚未安裝 VB-CABLE，可先選「自動偵測」，安裝後重新啟動程式即可。",
        "wizard.device.note":   "提醒：這裡只是選擇程式要「聽」哪個裝置，不會更改系統音訊設定。\n要讓聲音進得來，請把播放來源的輸出設為「CABLE Input」——\n可在 Windows 音量混合器對單一程式（如瀏覽器）設定，或將系統預設輸出改為 CABLE Input。",

        "device.auto":          "自動偵測（含 CABLE 的裝置）",
    },

    # ── 简体中文 ──────────────────────────────────────────
    "zh-CN": {
        "app.title":            "🎌 日文直播翻译",
        "app.header":           "🎌 日文直播实时翻译",
        "mode.translate":       "翻译模式",
        "mode.subtitle":        "字幕模式",
        "btn.clear":            "清除",
        "btn.passthrough":      "🖱穿透",
        "status.waiting":       "⏳ 等待音频...",
        "status.updated":       "更新 {time}",
        "status.resumed":       "▶ 已继续",
        "status.pausing":       "⏸ 暂停中...",
        "status.paused":        "⏸ 已暂停(不计费)",
        "msg.passthrough_on":   "🖱 点击穿透已开启：鼠标会穿过字幕窗口。按住 Ctrl+Alt 可临时操作窗口（拖动/按按钮）。",
        "msg.no_audio":         "⚠ 已 {seconds} 秒未收到音频。请确认声音已输出到「CABLE Input」（Windows 音量合成器 → 播放程序的输出设备）。",
        "msg.settings_saved_paused": "✅ 设置已保存，将在继续识别时生效",
        "msg.settings_applied": "✅ 设置已应用，管线已重新启动",
        "err.no_api_key":       "尚未设置 OpenAI API Key，请打开「⚙ 设置」填入。",

        "settings.title":       "⚙ 设置",
        "settings.tab.general": "常规",
        "settings.tab.engine":  "识别与翻译",
        "settings.tab.segment": "断句",
        "settings.tab.appearance": "外观",
        "settings.save":        "保存并应用",
        "settings.cancel":      "取消",

        "settings.ui_language": "界面语言",
        "settings.ui_language.hint": "只更改界面文字，不影响字幕翻译的目标语言。",
        "settings.api_key":     "OpenAI API Key",
        "settings.api_key.env_hint": "已从环境变量 / .env 读取 API Key（优先于此处设置）。如需更换请修改环境变量，或先移除后再在此填入。",
        "settings.toggle_show": "显示/隐藏",
        "settings.test_conn":   "测试连接",
        "settings.testing":     "测试中...",
        "settings.device":      "音频输入设备",
        "settings.device.hint": "选择 VB-CABLE 的 CABLE Output；「自动检测」会寻找名称含 CABLE 的设备。",
        "settings.loading":     "加载中...",

        "settings.stt_model":   "语音识别模型",
        "settings.stt_model.hint": "gpt-4o-mini-transcribe 延迟较低；账号无权限时可改回 whisper-1。",
        "settings.workers":     "并行识别 worker 数",
        "settings.workers.hint": "连续快速说话时清空积压更快；调小可省 API 用量。",
        "settings.gpt_model":   "翻译模型",
        "settings.source_lang": "源语言",
        "settings.target_lang": "目标语言",
        "settings.glossary":    "术语对照表（人名/术语固定译法）",
        "settings.glossary.hint": "一行一组「原文=译文」，# 开头为注释。例：ぺこら=佩克拉。列表空白时对翻译零影响。",

        "settings.dynamic_seg": "动态断句（VAD）",
        "settings.dynamic_seg.hint": "检测到停顿就立刻送出识别；关闭则固定每「断句上限」秒切一块。",
        "settings.pause_sec":   "停顿断句阈值（秒）",
        "settings.pause_sec.hint": "调大→句子更完整但延迟略增；调小→更实时但可能切碎。",
        "settings.min_speech":  "最短语音长度（秒）",
        "settings.min_speech.hint": "过短的声音片段不送识别；调小可保留短应答（如「うん」）。",
        "settings.chunk_sec":   "断句上限（秒）",
        "settings.silence":     "静音阈值（音量）",
        "settings.silence.hint": "低于此音量视为静音；环境噪声大时调高。",

        "settings.opacity":     "窗口透明度",
        "settings.font_size":   "字号",
        "settings.max_lines":   "最多显示条数",
        "settings.appearance.hint": "外观更改立即生效，无需重启管线。",

        "api.ok":               "✅ 连接成功",
        "api.invalid":          "❌ API Key 无效",
        "api.failed":           "❌ 连接失败：{msg}",
        "api.empty":            "请先输入 API Key",

        "wizard.title":         "🎌 初次设置向导",
        "wizard.back":          "上一步",
        "wizard.next":          "下一步",
        "wizard.finish":        "完成 ✓",
        "wizard.step":          "步骤 {n} / {total}",

        "wizard.lang.header":   "选择界面语言",
        "wizard.lang.sub":      "Language / 語言 / 言語",
        "wizard.lang.body":     "\n请选择这个程序的界面语言。\n（之后可在「⚙ 设置 → 常规」随时更改）",

        "wizard.welcome.header": "欢迎使用 日文直播实时翻译",
        "wizard.welcome.sub":   "开始之前",
        "wizard.welcome.body":  "\n这个工具会捕获电脑正在播放的日文直播声音，实时识别并翻译成字幕。\n\n使用前需要：\n\n  ①  安装 VB-CABLE 虚拟声卡（免费）\n       并把要翻译的声音输出设为「CABLE Input」\n\n  ②  一个 OpenAI API Key（下一步填入）\n",
        "wizard.welcome.link":  "🔗 下载 VB-CABLE（vb-audio.com/Cable）",

        "wizard.key.header":    "设置 OpenAI API Key",
        "wizard.key.sub":       "连接验证",
        "wizard.key.env":       "\n✅ 已检测到环境变量 / .env 中的 API Key，此步骤可直接跳过。",
        "wizard.key.body":      "\n请粘贴你的 OpenAI API Key（sk- 开头），并按「测试连接」验证：",
        "wizard.key.note":      "Key 会保存在你电脑的用户配置文件中，不会上传到其他地方。",

        "wizard.device.header": "选择音频输入设备",
        "wizard.device.sub":    "最后一步",
        "wizard.device.body":   "\n选择 VB-CABLE 的「CABLE Output」设备（已自动检测预选）：",
        "wizard.device.warn":   "⚠️ 未检测到 CABLE 设备。若尚未安装 VB-CABLE，可先选「自动检测」，安装后重新启动程序即可。",
        "wizard.device.note":   "提醒：这里只是选择程序要「听」哪个设备，不会更改系统音频设置。\n要让声音进得来，请把播放来源的输出设为「CABLE Input」——\n可在 Windows 音量合成器对单一程序（如浏览器）设置，或将系统默认输出改为 CABLE Input。",

        "device.auto":          "自动检测（含 CABLE 的设备）",
    },

    # ── English ───────────────────────────────────────────
    "en": {
        "app.title":            "🎌 Live Translator",
        "app.header":           "🎌 Japanese Live Translator",
        "mode.translate":       "Translate",
        "mode.subtitle":        "Transcript",
        "btn.clear":            "Clear",
        "btn.passthrough":      "🖱 Pass",
        "status.waiting":       "⏳ Waiting for audio...",
        "status.updated":       "Updated {time}",
        "status.resumed":       "▶ Resumed",
        "status.pausing":       "⏸ Pausing...",
        "status.paused":        "⏸ Paused (no API cost)",
        "msg.passthrough_on":   "🖱 Click-through enabled: the mouse now passes through the subtitle window. Hold Ctrl+Alt to interact with the window temporarily (drag / click buttons).",
        "msg.no_audio":         "⚠ No audio received for {seconds} seconds. Make sure your sound is routed to \"CABLE Input\" (Windows Volume Mixer → output device of the playing app).",
        "msg.settings_saved_paused": "✅ Settings saved. They will take effect when you resume.",
        "msg.settings_applied": "✅ Settings applied, pipeline restarted",
        "err.no_api_key":       "No OpenAI API Key configured. Open \"⚙ Settings\" to enter one.",

        "settings.title":       "⚙ Settings",
        "settings.tab.general": "General",
        "settings.tab.engine":  "Speech & Translation",
        "settings.tab.segment": "Segmentation",
        "settings.tab.appearance": "Appearance",
        "settings.save":        "Save & Apply",
        "settings.cancel":      "Cancel",

        "settings.ui_language": "Interface language",
        "settings.ui_language.hint": "Changes interface text only. Does not affect the subtitle translation target language.",
        "settings.api_key":     "OpenAI API Key",
        "settings.api_key.env_hint": "An API Key was loaded from an environment variable / .env (it takes priority over this field). To change it, edit the environment variable, or remove it and enter a key here.",
        "settings.toggle_show": "Show/Hide",
        "settings.test_conn":   "Test",
        "settings.testing":     "Testing...",
        "settings.device":      "Audio input device",
        "settings.device.hint": "Select VB-CABLE's CABLE Output. \"Auto-detect\" looks for a device whose name contains CABLE.",
        "settings.loading":     "Loading...",

        "settings.stt_model":   "Speech recognition model",
        "settings.stt_model.hint": "gpt-4o-mini-transcribe has lower latency. Switch back to whisper-1 if your account lacks access.",
        "settings.workers":     "Parallel STT workers",
        "settings.workers.hint": "Clears the backlog faster during rapid speech. Lower it to reduce API usage.",
        "settings.gpt_model":   "Translation model",
        "settings.source_lang": "Source language",
        "settings.target_lang": "Target language",
        "settings.glossary":    "Glossary (fixed translations for names/terms)",
        "settings.glossary.hint": "One \"source=translation\" pair per line; lines starting with # are comments. Example: ぺこら=Pekora. No effect when left empty.",

        "settings.dynamic_seg": "Dynamic segmentation (VAD)",
        "settings.dynamic_seg.hint": "Sends audio for recognition as soon as a pause is detected. When off, audio is cut every \"max segment\" seconds.",
        "settings.pause_sec":   "Pause threshold (sec)",
        "settings.pause_sec.hint": "Higher → more complete sentences, slightly more latency. Lower → more responsive, may fragment sentences.",
        "settings.min_speech":  "Min speech length (sec)",
        "settings.min_speech.hint": "Skips very short audio fragments. Lower it to keep brief responses (e.g. \"うん\").",
        "settings.chunk_sec":   "Max segment length (sec)",
        "settings.silence":     "Silence threshold (volume)",
        "settings.silence.hint": "Audio below this volume counts as silence. Raise it in noisy environments.",

        "settings.opacity":     "Window opacity",
        "settings.font_size":   "Font size",
        "settings.max_lines":   "Max entries shown",
        "settings.appearance.hint": "Appearance changes apply immediately; no pipeline restart needed.",

        "api.ok":               "✅ Connected",
        "api.invalid":          "❌ Invalid API Key",
        "api.failed":           "❌ Connection failed: {msg}",
        "api.empty":            "Please enter an API Key first",

        "wizard.title":         "🎌 Setup Wizard",
        "wizard.back":          "Back",
        "wizard.next":          "Next",
        "wizard.finish":        "Finish ✓",
        "wizard.step":          "Step {n} / {total}",

        "wizard.lang.header":   "Choose your language",
        "wizard.lang.sub":      "Language / 語言 / 言語",
        "wizard.lang.body":     "\nSelect the interface language for this app.\n(You can change it any time in \"⚙ Settings → General\")",

        "wizard.welcome.header": "Welcome to Japanese Live Translator",
        "wizard.welcome.sub":   "Before you start",
        "wizard.welcome.body":  "\nThis tool captures Japanese live-stream audio playing on your PC, transcribes it, and translates it into subtitles in real time.\n\nYou will need:\n\n  ①  VB-CABLE virtual audio device (free)\n       and set the audio you want translated to output to \"CABLE Input\"\n\n  ②  An OpenAI API Key (entered on the next step)\n",
        "wizard.welcome.link":  "🔗 Download VB-CABLE (vb-audio.com/Cable)",

        "wizard.key.header":    "Set your OpenAI API Key",
        "wizard.key.sub":       "Connection check",
        "wizard.key.env":       "\n✅ An API Key was detected in your environment variable / .env. You can skip this step.",
        "wizard.key.body":      "\nPaste your OpenAI API Key (starts with sk-) and click \"Test\" to verify:",
        "wizard.key.note":      "The key is stored in your local user settings file and is never uploaded anywhere else.",

        "wizard.device.header": "Select audio input device",
        "wizard.device.sub":    "Last step",
        "wizard.device.body":   "\nSelect VB-CABLE's \"CABLE Output\" device (auto-detected below):",
        "wizard.device.warn":   "⚠️ No CABLE device detected. If VB-CABLE isn't installed yet, choose \"Auto-detect\" for now and restart the app after installing.",
        "wizard.device.note":   "Note: this only chooses which device the app listens to — it does not change your system audio settings.\nFor audio to come through, set the playback source's output to \"CABLE Input\" —\nuse the Windows Volume Mixer for a single app (e.g. your browser), or change the system default output to CABLE Input.",

        "device.auto":          "Auto-detect (device containing CABLE)",
    },

    # ── 日本語 ────────────────────────────────────────────
    "ja": {
        "app.title":            "🎌 ライブ翻訳",
        "app.header":           "🎌 日本語ライブ同時翻訳",
        "mode.translate":       "翻訳モード",
        "mode.subtitle":        "字幕モード",
        "btn.clear":            "クリア",
        "btn.passthrough":      "🖱 透過",
        "status.waiting":       "⏳ 音声を待機中...",
        "status.updated":       "更新 {time}",
        "status.resumed":       "▶ 再開しました",
        "status.pausing":       "⏸ 一時停止中...",
        "status.paused":        "⏸ 一時停止中（課金なし）",
        "msg.passthrough_on":   "🖱 クリック透過を有効にしました：マウスが字幕ウィンドウを通り抜けます。Ctrl+Alt を押している間は一時的にウィンドウを操作できます（ドラッグ／ボタン）。",
        "msg.no_audio":         "⚠ {seconds} 秒間、音声を受信していません。音声が「CABLE Input」に出力されているか確認してください（Windows の音量ミキサー → 再生アプリの出力デバイス）。",
        "msg.settings_saved_paused": "✅ 設定を保存しました。再開時に反映されます",
        "msg.settings_applied": "✅ 設定を適用し、パイプラインを再起動しました",
        "err.no_api_key":       "OpenAI API Key が未設定です。「⚙ 設定」から入力してください。",

        "settings.title":       "⚙ 設定",
        "settings.tab.general": "一般",
        "settings.tab.engine":  "認識と翻訳",
        "settings.tab.segment": "区切り",
        "settings.tab.appearance": "外観",
        "settings.save":        "保存して適用",
        "settings.cancel":      "キャンセル",

        "settings.ui_language": "表示言語",
        "settings.ui_language.hint": "画面の文字だけを変更します。字幕の翻訳先言語には影響しません。",
        "settings.api_key":     "OpenAI API Key",
        "settings.api_key.env_hint": "環境変数 / .env から API Key を読み込みました（この欄より優先されます）。変更するには環境変数を編集するか、削除してからここに入力してください。",
        "settings.toggle_show": "表示/非表示",
        "settings.test_conn":   "接続テスト",
        "settings.testing":     "テスト中...",
        "settings.device":      "音声入力デバイス",
        "settings.device.hint": "VB-CABLE の CABLE Output を選択してください。「自動検出」は名前に CABLE を含むデバイスを探します。",
        "settings.loading":     "読み込み中...",

        "settings.stt_model":   "音声認識モデル",
        "settings.stt_model.hint": "gpt-4o-mini-transcribe は低遅延です。アカウントに権限がない場合は whisper-1 に戻してください。",
        "settings.workers":     "並列認識ワーカー数",
        "settings.workers.hint": "早口が続くときの滞留を早く解消します。減らすと API 使用量を節約できます。",
        "settings.gpt_model":   "翻訳モデル",
        "settings.source_lang": "翻訳元の言語",
        "settings.target_lang": "翻訳先の言語",
        "settings.glossary":    "用語集（人名・用語の訳を固定）",
        "settings.glossary.hint": "1 行に 1 組「原文=訳語」、# で始まる行はコメントです。例：ぺこら=佩可拉。空欄の場合、翻訳への影響はありません。",

        "settings.dynamic_seg": "動的区切り（VAD）",
        "settings.dynamic_seg.hint": "無音を検出した時点で認識に送ります。オフにすると「最大区切り」秒ごとに固定で分割します。",
        "settings.pause_sec":   "無音の区切りしきい値（秒）",
        "settings.pause_sec.hint": "大きく→文がまとまるが遅延がやや増加。小さく→即時性は上がるが文が切れやすい。",
        "settings.min_speech":  "最短音声長（秒）",
        "settings.min_speech.hint": "短すぎる音声は認識に送りません。小さくすると短い相づち（「うん」など）も拾えます。",
        "settings.chunk_sec":   "最大区切り長（秒）",
        "settings.silence":     "無音しきい値（音量）",
        "settings.silence.hint": "この音量未満を無音とみなします。環境音が大きい場合は上げてください。",

        "settings.opacity":     "ウィンドウの不透明度",
        "settings.font_size":   "文字サイズ",
        "settings.max_lines":   "最大表示件数",
        "settings.appearance.hint": "外観の変更は即時反映され、パイプラインの再起動は不要です。",

        "api.ok":               "✅ 接続成功",
        "api.invalid":          "❌ API Key が無効です",
        "api.failed":           "❌ 接続失敗：{msg}",
        "api.empty":            "先に API Key を入力してください",

        "wizard.title":         "🎌 初期設定ウィザード",
        "wizard.back":          "戻る",
        "wizard.next":          "次へ",
        "wizard.finish":        "完了 ✓",
        "wizard.step":          "ステップ {n} / {total}",

        "wizard.lang.header":   "表示言語を選択",
        "wizard.lang.sub":      "Language / 語言 / 言語",
        "wizard.lang.body":     "\nこのアプリの表示言語を選択してください。\n（後から「⚙ 設定 → 一般」でいつでも変更できます）",

        "wizard.welcome.header": "日本語ライブ同時翻訳へようこそ",
        "wizard.welcome.sub":   "はじめる前に",
        "wizard.welcome.body":  "\nこのツールは PC で再生中の日本語ライブ音声を取り込み、リアルタイムで認識・翻訳して字幕を表示します。\n\n事前に必要なもの：\n\n  ①  VB-CABLE 仮想オーディオデバイス（無料）\n       翻訳したい音声の出力を「CABLE Input」に設定\n\n  ②  OpenAI API Key（次のステップで入力）\n",
        "wizard.welcome.link":  "🔗 VB-CABLE をダウンロード（vb-audio.com/Cable）",

        "wizard.key.header":    "OpenAI API Key を設定",
        "wizard.key.sub":       "接続の確認",
        "wizard.key.env":       "\n✅ 環境変数 / .env に API Key を検出しました。このステップはスキップできます。",
        "wizard.key.body":      "\nOpenAI API Key（sk- で始まる）を貼り付け、「接続テスト」で確認してください：",
        "wizard.key.note":      "Key はお使いの PC のユーザー設定ファイルに保存され、外部に送信されることはありません。",

        "wizard.device.header": "音声入力デバイスを選択",
        "wizard.device.sub":    "最後のステップ",
        "wizard.device.body":   "\nVB-CABLE の「CABLE Output」デバイスを選択してください（自動検出済み）：",
        "wizard.device.warn":   "⚠️ CABLE デバイスが見つかりません。VB-CABLE が未インストールの場合は「自動検出」を選び、インストール後にアプリを再起動してください。",
        "wizard.device.note":   "注意：ここで選ぶのはアプリが「聞く」デバイスだけで、システムの音声設定は変更されません。\n音声を取り込むには、再生元の出力を「CABLE Input」に設定してください——\nWindows の音量ミキサーでアプリ単位（ブラウザなど）に設定するか、システム既定の出力を CABLE Input に変更します。",

        "device.auto":          "自動検出（CABLE を含むデバイス）",
    },
}


def set_language(lang: str):
    global _current
    _current = lang if lang in STRINGS else DEFAULT_LANG


def get_language() -> str:
    return _current


def t(key: str, **kwargs) -> str:
    """取得目前語言的字串；缺鍵時回退繁中，再缺則回傳鍵本身。"""
    text = STRINGS.get(_current, {}).get(key)
    if text is None:
        text = STRINGS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
