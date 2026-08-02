# 🎌 Japanese Live Translator

**English** | [繁體中文](README.zh-TW.md)

Capture Japanese live-stream audio playing on your PC, transcribe it, and translate it into
real-time subtitles shown in an always-on-top, draggable, semi-transparent overlay.

- Modern dark interface (CustomTkinter) with a **first-run setup wizard** — no code editing required.
- Interface available in **English, 繁體中文, 简体中文, and 日本語**.
- Optimized for low latency in three stages (dynamic segmentation, parallel transcription,
  streaming translation) — roughly **2–3 seconds** from speech to subtitle.
- Ships as a **single .exe**; no Python installation needed.

---

## ✨ Features

- **Real-time transcription + translation**: OpenAI STT for Japanese → GPT for translation.
- **Dynamic segmentation (VAD)**: sends audio for recognition as soon as the speaker pauses,
  instead of waiting a fixed interval. With no pause, it force-cuts at a 5-second cap —
  low latency without fragmenting sentences.
- **Parallel transcription with ordered output**: multiple workers call the STT API concurrently,
  so rapid speech never piles up. Results are re-ordered by sequence number, so subtitles stay in order.
- **Streaming translation**: translated text appears word by word instead of waiting for the full sentence.
- **Two modes, one click**:
  - **Translate**: shows Japanese original + translation.
  - **Transcript**: shows the Japanese original only (no translation calls — saves cost).
- **Click-through overlay**: let the mouse pass through the subtitle window and interact with the
  video underneath. Hold **Ctrl+Alt** to temporarily interact with the window itself.
- **Pause / resume**: no API calls at all while paused.
- **No-audio detection**: a colored indicator plus a warning after 30 seconds of silence,
  reminding you to check your CABLE routing.
- **Glossary**: pin fixed translations for names and terms (e.g. VTuber names, game jargon).
- **Remembers window position and size** between sessions.
- **Graphical settings**: four tabs (General / Speech & Translation / Segmentation / Appearance),
  every numeric field adjustable by slider *or* direct input, with range clamping.
- **Hallucination filtering**: removes common Whisper hallucinations and overly short noise.

---

## 🚀 Quick Start (exe — recommended)

1. Install **[VB-CABLE](https://vb-audio.com/Cable/)** virtual audio device and reboot.
2. Run `JPLiveTranslator.exe`.
3. Follow the **setup wizard**: choose your language → enter your OpenAI API Key
   (click "Test" to verify) → select the CABLE device.
4. Route the audio you want translated to **CABLE Input**
   (via the Windows Volume Mixer for a single app, or by changing the system default output).
5. Start playing a Japanese live stream — subtitles appear in real time.

> Adjust anything later via the **⚙** button. Settings live in
> `%APPDATA%\YoutubeLiveTranslator\settings.json`, with logs in the same folder.

> 💡 To still hear the audio yourself: Sound Control Panel → Recording → CABLE Output →
> Properties → Listen → check "Listen to this device" and pick your headphones/speakers.

---

## 🧑‍💻 Running from source

Requires Python 3.10+, VB-CABLE, and an OpenAI API Key.

```powershell
pip install -r requirements.txt
python main.py                  # first run opens the setup wizard
python main.py --list-devices   # list all audio devices
```

The API Key can also come from the environment (takes priority over the UI setting):

```powershell
# Option A: a .env file in the project directory
copy .env.example .env          # then fill in OPENAI_API_KEY=sk-...

# Option B: a Windows user environment variable (reopen your terminal afterwards)
setx OPENAI_API_KEY "sk-your-key"
```

### Building the exe

```powershell
pip install pyinstaller
.\build.bat                     # outputs dist\JPLiveTranslator.exe
```

---

## 🧩 Architecture

```
 Audio ──► VB-CABLE ──► AudioCapture (dynamic VAD) ──► audio_queue
                                    │
                             Transcriber (N parallel workers + reordering)
                                    │  text_queue
                                  Router ──┬─ Translate mode ─► Translator (streaming) ─┐
                                           │                                            ▼
                                           └─ Transcript mode ───────────────► result_queue
                                                                                        │
                                                                              SubtitleWindow
```

| File | Responsibility |
|------|----------------|
| `main.py`            | Entry point (wires wizard / pipeline / window) |
| `pipeline.py`        | Pipeline management (Router + module lifecycle) |
| `audio_capture.py`   | Audio capture from CABLE, dynamic segmentation (VAD), non-blocking enqueue |
| `transcriber.py`     | Parallel STT, hallucination filtering, sequence-ordered output |
| `translator.py`      | Streaming JA → target-language translation via GPT |
| `subtitle_window.py` | Overlay subtitle window (streaming display, modes, click-through) |
| `settings_window.py` | ⚙ Tabbed settings window |
| `wizard.py`          | First-run setup wizard |
| `config.py`          | Settings management (defaults + settings.json overrides) |
| `i18n.py`            | Interface translations (en / zh-TW / zh-CN / ja) |
| `theme.py`           | Colors and fonts |
| `ui_common.py`       | Shared helpers (device list, API key validation) |
| `build.bat`          | One-click PyInstaller build |

---

## ⚙️ Settings

Everything is configurable in the ⚙ window; changes are applied on save
(the pipeline restarts automatically when needed).

### General
| Setting | Default | Notes |
|---------|---------|-------|
| Interface language | 繁體中文 | en / zh-TW / zh-CN / ja. Independent of the translation target language |
| API Key | — | With a "Test" button; environment variable / `.env` takes priority |
| Audio input device | Auto-detect | Pick CABLE Output; refreshable list |

### Speech & Translation
| Setting | Default | Notes |
|---------|---------|-------|
| Speech recognition model | `gpt-4o-mini-transcribe` | Can switch back to `whisper-1` |
| Parallel STT workers | `3` | Lower to reduce API usage |
| Translation model | `gpt-4o-mini` | Use `gpt-4o` for higher quality |
| Source / target language | 日文 / 繁體中文 | Controls the subtitle translation |
| Glossary | empty | One `source=translation` per line; `#` for comments |

### Segmentation
| Setting | Default | Notes |
|---------|---------|-------|
| Dynamic segmentation (VAD) | On | Off = fixed cuts every "max segment" seconds |
| Pause threshold | `0.6` s | Higher → fuller sentences; lower → more responsive |
| Min speech length | `0.8` s | Lower to keep short responses |
| Max segment length | `5` s | Upper bound when there is no pause |
| Silence threshold | `200` | Raise it in noisy environments |

### Appearance (applies instantly)
| Setting | Default |
|---------|---------|
| Window opacity | `0.88` |
| Font size | `18` |
| Max entries shown | `6` |

---

## 🩺 Troubleshooting

| Problem | Fix |
|---------|-----|
| No CABLE device found | Install VB-CABLE and reboot, then press ↻ to refresh |
| No subtitles at all | Verify audio is routed to `CABLE Input`; check the log in `%APPDATA%\YoutubeLiveTranslator\` |
| Transcription errors / no output | Switch the recognition model back to `whisper-1` |
| Sentences cut too short | Raise the "Pause threshold" (e.g. 0.8) |
| Short responses missing | Lower "Min speech length" (e.g. 0.4) |
| Reduce API cost | Use Transcript mode, lower worker count, raise silence threshold, or pause |
| Slow exe startup (3–8 s) | Normal — a single-file exe unpacks on each launch |
| Can't click the window | Click-through is on — hold **Ctrl+Alt**, or turn it off with the 🖱 button |

---

## 🔒 Security

- The API Key is read from an environment variable / `.env` first; when entered via the UI it is
  stored in your local user settings file
  (`%APPDATA%\YoutubeLiveTranslator\settings.json`, plain text — do not share that file).
- No API key is present in the source code, and the built exe contains no key —
  each user enters their own on first run.
- `.gitignore` excludes `.env`, logs, and build artifacts.
