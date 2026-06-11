# 🎌 YouTube 日文直播即時翻譯器

擷取 YouTube（或任何播放中的）**日文直播音訊**，即時辨識成文字並翻譯成**繁體中文**，
顯示在一個永遠置頂、可拖曳的半透明字幕視窗上。

針對「即時性」做過三階段優化（動態斷句、並行辨識、串流翻譯），
說話到字幕出現的延遲大約落在 **2～3 秒**。

---

## ✨ 功能特色

- **即時語音辨識 + 翻譯**：OpenAI STT 辨識日文 → GPT 翻譯成繁體中文。
- **動態斷句（VAD）**：偵測到說話者停頓就立刻送出辨識，不必死等固定秒數；
  沒有停頓時最多累積到 5 秒上限才強制斷句 → 低延遲又不切碎句子。
- **並行辨識 + 順序重排**：多個 worker 同時呼叫辨識 API，連續快速說話也不會越積越慢；
  結果依序號自動排回，字幕順序不亂。
- **串流翻譯**：翻譯結果逐字浮現，不必等整句翻完。
- **兩種模式一鍵切換**：
  - **翻譯模式**：同時顯示日文原文 + 繁中翻譯。
  - **字幕模式**：只顯示日文原文（不呼叫翻譯，省費用）。
- **幻覺過濾**：自動濾掉 Whisper 常見的幻覺句（如「ご視聴ありがとうございました」）與過短雜音。
- **置頂字幕視窗**：半透明、可拖曳、可調整透明度／字級／行數。

---

## 🧩 運作架構

```
 播放音訊 ──► VB-CABLE ──► AudioCapture ──► audio_queue
                                              │
                                       Transcriber（並行 N worker + 順序重排）
                                              │  text_queue
                                            Router ──┬─ 翻譯模式 ─► translate_queue ─► Translator（串流）
                                                     │                                      │
                                                     └─ 字幕模式 ───────────────► result_queue
                                                                                            │
                                                                                     SubtitleWindow（字幕視窗）
```

| 檔案 | 職責 |
|------|------|
| `audio_capture.py` | 從 CABLE 裝置擷取音訊、動態斷句（VAD）、非阻塞入列 |
| `transcriber.py`   | 並行呼叫 STT 辨識日文、幻覺過濾、依序號重排輸出 |
| `translator.py`    | 透過 GPT 把日文串流翻譯成繁體中文 |
| `main.py`          | 程式入口、Router 分流、Tkinter 字幕視窗 |
| `config.py`        | 所有設定（API key、裝置、模型、斷句、視窗等） |

---

## 📦 安裝需求

- **Python 3.10+**
- **[VB-CABLE](https://vb-audio.com/Cable/) 虛擬音效裝置**（用來把系統聲音導給程式擷取）
- 一把 **OpenAI API Key**

安裝套件：

```powershell
pip install -r requirements.txt
```

> 相依套件：`openai`、`sounddevice`、`numpy`

---

## 🔧 設定步驟

### 1. 設定 OpenAI API Key

**不要**把 key 寫進程式碼。兩種方式擇一：

```powershell
# 方法 A：專案目錄放 .env（最簡單）
copy .env.example .env
notepad .env          # 把 OPENAI_API_KEY=sk-... 換成你的 key

# 方法 B：設成 Windows 使用者環境變數（永久，設定後需重開終端機）
setx OPENAI_API_KEY "sk-你的key"
```

> `.env` 已被 `.gitignore` 排除，不會被 commit。

### 2. 安裝並設定 VB-CABLE 音訊路由

1. 安裝 VB-CABLE 並重開機。
2. 在 Windows 音效設定，把**要被翻譯的聲音來源**輸出到 **CABLE Input**
   （例如：瀏覽器音量混合器 → 把該分頁輸出設成 `CABLE Input`，
   或把系統預設輸出設成 `CABLE Input`）。
3. 程式會從 **CABLE Output** 擷取這份聲音。

> 想同時自己也聽得到，可在「聲音控制台 → 錄製 → CABLE Output → 內容 → 接聽」
> 勾選「接聽此裝置」並選擇你的耳機/喇叭。

### 3. 確認音訊裝置編號

列出所有輸入裝置，找到 CABLE 的編號：

```powershell
python main.py --list-devices
```

在 `config.py` 設定：

```python
CABLE_DEVICE_INDEX = 1     # 換成上面列出的 CABLE Output 編號；None = 自動偵測含 "CABLE" 的裝置
```

---

## ▶️ 使用方式

```powershell
python main.py
```

- 啟動後會跳出置頂的黑色字幕視窗，開始播放日文直播即可看到即時字幕。
- 視窗左上角按鈕可**切換翻譯／字幕模式**。
- 拖曳上方工具列可移動視窗；「清除」按鈕清空字幕。
- 關閉視窗即結束程式。

執行紀錄會寫入 `translator.log`（含每段辨識結果與序號，方便除錯）。

---

## ⚙️ 可調參數（`config.py`）

### 音訊擷取
| 參數 | 預設 | 說明 |
|------|------|------|
| `CABLE_DEVICE_INDEX` | `1` | CABLE 裝置編號；`None` = 自動偵測 |
| `SAMPLE_RATE` | `16000` | 取樣率（STT 建議 16kHz） |
| `CHUNK_SECONDS` | `5` | 斷句的**最長上限**（沒停頓時最多累積到這麼長才強制切） |
| `SILENCE_THRESHOLD` | `200` | 音量低於此值視為靜音（VAD 判斷依據） |
| `AUDIO_QUEUE_MAXSIZE` | `5` | 音訊佇列上限，滿了會丟最舊塊（避免延遲累積） |

### 動態斷句
| 參數 | 預設 | 說明 |
|------|------|------|
| `USE_DYNAMIC_SEGMENTATION` | `True` | `False` = 回到固定每 5 秒切塊 |
| `PAUSE_SECONDS` | `0.6` | 連續靜音達此長度即斷句（調大→句子更完整、延遲略增） |
| `MIN_SPEECH_SECONDS` | `0.8` | 一段語音至少要這麼長才送出（調小→不漏短應答，但易有雜訊/幻覺） |

### 辨識與翻譯
| 參數 | 預設 | 說明 |
|------|------|------|
| `STT_MODEL` | `gpt-4o-mini-transcribe` | 辨識模型；可改回 `whisper-1` |
| `STT_WORKERS` | `3` | 並行辨識的 worker 數（調小可省 API 用量） |
| `GPT_MODEL` | `gpt-4o-mini` | 翻譯模型；要更準可改 `gpt-4o` |
| `SOURCE_LANG` / `TARGET_LANG` | `日文` / `繁體中文` | 來源／目標語言 |

### 字幕視窗
| 參數 | 預設 | 說明 |
|------|------|------|
| `WINDOW_OPACITY` | `0.88` | 視窗透明度（0.0～1.0） |
| `FONT_SIZE` | `18` | 字級 |
| `MAX_LINES` | `6` | 最多顯示幾筆 |
| `WINDOW_WIDTH` / `WINDOW_HEIGHT` | `900` / `300` | 視窗大小 |
| `POLL_INTERVAL_MS` | `60` | 字幕刷新間隔（越小越即時） |

---

## 🩺 疑難排解

| 狀況 | 處理方式 |
|------|----------|
| 啟動報「找不到 CABLE 裝置」 | 跑 `--list-devices` 確認編號並填入 `CABLE_DEVICE_INDEX` |
| 沒有任何字幕 | 確認聲音有導到 `CABLE Input`；檢查 `translator.log` 有無辨識結果 |
| 辨識報錯或無輸出 | 確認帳號有 `gpt-4o-mini-transcribe` 權限，或把 `STT_MODEL` 改回 `whisper-1` |
| 句子被切太碎 | 把 `PAUSE_SECONDS` 調大（如 `0.8`） |
| 短應答（如「うん」）沒翻出來 | 把 `MIN_SPEECH_SECONDS` 調小（如 `0.4`） |
| 想省 API 費用 | 切到「字幕模式」、調小 `STT_WORKERS`、或拉高 `SILENCE_THRESHOLD` |

---

## 🔒 安全性

- API key 一律透過環境變數或 `.env` 載入，**不寫進原始碼**。
- `.gitignore` 已排除 `.env`、`__pycache__/`、`*.log`，避免機密與快取被 commit。
