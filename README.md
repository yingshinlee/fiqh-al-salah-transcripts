# fiqh-al-salah-transcripts

中文 YouTube 講座轉逐字稿工具 —— 專為夾雜大量伊斯蘭教專有名詞的中文影片設計。
A Chinese-language transcription tool for lectures rich in Islamic terminology, packaged as a [Claude Code](https://claude.com/claude-code) skill.

## 這是什麼

把 YouTube 影片（或本機音檔）轉成兩份檔案：

- `*.txt` —— 純文字逐字稿
- `*.srt` —— 帶時間軸、可搭配影片的字幕

整套流程在本機執行、免費、不外流：用 Apple Silicon 的 GPU 跑 `mlx_whisper`（large-v3-turbo）。48 分鐘的影片約 6–7 分鐘完成。它會自動偵測並修正 Whisper 常見的「某字不斷重複」的辨識錯誤，並附一份伊斯蘭教專有名詞校對表，把音近錯字改回正確寫法。

> 原始用途：轉錄《拜功教法學》（Fiqh al-Salah，فقه الصلاة）系列講座。

## 安裝

需要 macOS（Apple Silicon）。第一次使用先裝相依工具：

```bash
brew install yt-dlp ffmpeg
python3 -m pip install mlx-whisper opencc
```

把本 repo 放到 Claude Code 的 skills 目錄即可被自動載入：

```bash
git clone https://github.com/yingshinlee/fiqh-al-salah-transcripts.git \
  ~/.claude/skills/fiqh-al-salah-transcripts
```

也可以不透過 Claude，直接用腳本：

```bash
python3 scripts/transcribe.py "https://www.youtube.com/watch?v=XXXX" --outdir ./out
```

## 內容

| 路徑 | 說明 |
|---|---|
| `SKILL.md` | Claude Code skill 定義與使用說明 |
| `scripts/transcribe.py` | 下載 → 辨識 → 修正重複辨識錯誤 → 輸出 txt/srt 的主程式 |
| `references/islamic-terms.md` | 伊斯蘭教專有名詞校對表（持續補充） |

## 授權

程式碼與校對表以 MIT 授權釋出，詳見 [LICENSE](LICENSE)。
（講座逐字稿本身的著作權屬於原始影片／教材作者，不在本授權範圍內。）

## 貢獻

歡迎補充 `references/islamic-terms.md` 的術語對照，或回報辨識／校正問題。
