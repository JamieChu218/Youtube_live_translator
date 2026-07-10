# 🎌 YouTube 日文直播即時翻譯器

擷取 YouTube(或任何播放中的)**日文直播音訊**,即時辨識成文字並翻譯成**繁體中文**,
顯示在一個永遠置頂、可拖曳的半透明字幕視窗上。

- 現代化深色介面(CustomTkinter),**首次啟動精靈**引導完成所有設定,不需改任何程式碼。
- 針對「即時性」做過三階段優化(動態斷句、並行辨識、串流翻譯),
  說話到字幕出現的延遲大約落在 **2~3 秒**。
- 可打包成**單一 .exe**,雙擊即用,不需安裝 Python。

---

## ✨ 功能特色

- **即時語音辨識 + 翻譯**:OpenAI STT 辨識日文 → GPT 翻譯成繁體中文。
- **動態斷句(VAD)**:偵測到說話者停頓就立刻送出辨識,不必死等固定秒數;
  沒有停頓時最多累積到 5 秒上限才強制斷句 → 低延遲又不切碎句子。
- **並行辨識 + 順序重排**:多個 worker 同時呼叫辨識 API,連續快速說話也不會越積越慢;
  結果依序號自動排回,字幕順序不亂。
- **串流翻譯**:翻譯結果逐字浮現,不必等整句翻完。
- **兩種模式一鍵切換**:
  - **翻譯模式**:同時顯示日文原文 + 繁中翻譯。
  - **字幕模式**:只顯示日文原文(不呼叫翻譯,省費用)。
- **圖形化設定**:⚙ 設定視窗四分頁(一般/辨識與翻譯/斷句/外觀),
  含 API Key 測試連線、音訊裝置即時列表、滑桿調參;儲存即套用。
- **首次啟動精靈**:第一次執行自動引導 → 填 API Key(驗證連線)→ 選音訊裝置 → 完成。
- **幻覺過濾**:自動濾掉 Whisper 常見的幻覺句與過短雜音。

---

## 🚀 快速開始(exe 版,推薦一般使用者)

1. 安裝 **[VB-CABLE](https://vb-audio.com/Cable/)** 虛擬音效裝置並重開機。
2. 雙擊 `JPLiveTranslator.exe`。
3. 跟著**首次設定精靈**走:填 OpenAI API Key(按「測試連線」驗證)→ 選 CABLE 裝置 → 完成。
4. 把要翻譯的聲音輸出設為 **CABLE Input**(瀏覽器分頁的音量混合器或系統預設輸出)。
5. 開始播放日文直播,字幕視窗就會即時顯示。

> 之後想調整任何參數,點字幕視窗右上角的 **⚙** 即可,設定存在
> `%APPDATA%\YoutubeLiveTranslator\settings.json`,執行紀錄也在同目錄的 `translator.log`。

> 💡 想同時自己也聽得到聲音:「聲音控制台 → 錄製 → CABLE Output → 內容 → 接聽」
> 勾選「接聽此裝置」並選擇你的耳機/喇叭。

---

## 🧑‍💻 從原始碼執行(開發者)

需求:Python 3.10+、VB-CABLE、OpenAI API Key。

```powershell
pip install -r requirements.txt
python main.py                  # 首次會進設定精靈
python main.py --list-devices   # 列出所有音訊裝置
```

API Key 也可以用環境變數提供(優先於 UI 設定,適合開發):

```powershell
# 方法 A:專案目錄放 .env
copy .env.example .env          # 再填入 OPENAI_API_KEY=sk-...

# 方法 B:Windows 使用者環境變數(設定後重開終端機)
setx OPENAI_API_KEY "sk-你的key"
```

### 打包成 exe

```powershell
pip install pyinstaller
.\build.bat                     # 輸出 dist\JPLiveTranslator.exe
```

---

## 🧩 運作架構

```
 播放音訊 ──► VB-CABLE ──► AudioCapture(動態斷句 VAD) ──► audio_queue
                                              │
                                       Transcriber(並行 N worker + 順序重排)
                                              │  text_queue
                                            Router ──┬─ 翻譯模式 ─► Translator(串流) ─┐
                                                     │                                ▼
                                                     └─ 字幕模式 ──────────────► result_queue
                                                                                       │
                                                                              SubtitleWindow(字幕視窗)
```

| 檔案 | 職責 |
|------|------|
| `main.py`            | 程式入口(組裝精靈/管線/視窗) |
| `pipeline.py`        | 管線管理(Router 分流 + 模組生命週期 start/stop/restart) |
| `audio_capture.py`   | 從 CABLE 裝置擷取音訊、動態斷句(VAD)、非阻塞入列 |
| `transcriber.py`     | 並行 STT 辨識、幻覺過濾、依序號重排輸出 |
| `translator.py`      | GPT 日文 → 繁中串流翻譯 |
| `subtitle_window.py` | 置頂字幕視窗(串流逐字顯示、模式切換) |
| `settings_window.py` | ⚙ 分頁設定視窗 |
| `wizard.py`          | 首次啟動設定精靈 |
| `config.py`          | 設定管理(內建預設 + settings.json 使用者覆蓋) |
| `theme.py`           | UI 配色與字型常數 |
| `ui_common.py`       | 裝置列表 / API Key 驗證等共用工具 |
| `build.bat`          | PyInstaller 一鍵打包 |

---

## ⚙️ 可調參數(⚙ 設定視窗)

所有參數都可以在設定視窗調整,儲存後自動套用(必要時自動重啟管線)。
設定檔位置:`%APPDATA%\YoutubeLiveTranslator\settings.json`(只記錄你改過的項目)。

### 一般
| 參數 | 預設 | 說明 |
|------|------|------|
| API Key | — | 含「測試連線」驗證;環境變數/.env 優先於此處 |
| 音訊輸入裝置 | 自動偵測 | 選 CABLE Output;可即時重新整理列表 |

### 辨識與翻譯
| 參數 | 預設 | 說明 |
|------|------|------|
| 語音辨識模型 | `gpt-4o-mini-transcribe` | 可改回 `whisper-1` |
| 並行 worker 數 | `3` | 調小可省 API 用量 |
| 翻譯模型 | `gpt-4o-mini` | 要更準可改 `gpt-4o` |
| 來源/目標語言 | 日文 / 繁體中文 | |

### 斷句
| 參數 | 預設 | 說明 |
|------|------|------|
| 動態斷句(VAD) | 開 | 關閉 = 固定每「斷句上限」秒切一塊 |
| 停頓斷句門檻 | `0.6` 秒 | 調大→句子更完整;調小→更即時 |
| 最短語音長度 | `0.8` 秒 | 調小→不漏短應答,但易有雜訊 |
| 斷句上限 | `5` 秒 | 沒停頓時最多累積這麼長 |
| 靜音門檻 | `200` | 環境雜訊大時調高 |

### 外觀(變更立即生效)
| 參數 | 預設 |
|------|------|
| 視窗透明度 | `0.88` |
| 字級 | `18` |
| 最多顯示筆數 | `6` |

---

## 🩺 疑難排解

| 狀況 | 處理方式 |
|------|----------|
| 精靈/設定找不到 CABLE 裝置 | 確認 VB-CABLE 已安裝並重開機,按 ↻ 重新整理 |
| 沒有任何字幕 | 確認聲音有導到 `CABLE Input`;看 `%APPDATA%\YoutubeLiveTranslator\translator.log` |
| 辨識報錯或無輸出 | 設定→辨識模型改回 `whisper-1` 試試 |
| 句子被切太碎 | 設定→斷句→「停頓斷句門檻」調大(如 0.8) |
| 短應答(如「うん」)沒翻出來 | 設定→斷句→「最短語音長度」調小(如 0.4) |
| 想省 API 費用 | 切「字幕模式」、調小 worker 數、拉高靜音門檻 |
| exe 啟動較慢(3~8 秒) | 單檔 exe 每次啟動需解壓,屬正常現象 |

---

## 🔒 安全性

- API Key 優先從環境變數 / `.env` 讀取;由 UI 填入時儲存於使用者設定檔
  (`%APPDATA%\YoutubeLiveTranslator\settings.json`,明文,請勿分享該檔案)。
- 原始碼中**不含**任何 API Key;`.gitignore` 已排除 `.env`、log、建置產物。
