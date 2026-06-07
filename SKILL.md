---
name: youtube-transcribe-zh
description: >-
  把 YouTube 影片（或本機音檔）轉成中文逐字稿，同時產出帶時間軸、可搭配影片的 .srt 字幕。
  專為「主要語言是中文、但夾雜大量伊斯蘭教專有名詞」的講座 / 教學影片設計，會自動修正
  Whisper 常見的「結尾或中段某個字狂重複」的幻覺。當使用者想把 YouTube 影片、講座、
  podcast、錄音轉成逐字稿或字幕（subtitle / SRT / 逐字稿 / transcript / 字幕檔 / 聽打），
  尤其是伊斯蘭、宗教、清真、拜功、教法相關的中文影片時，請使用這個 skill。即使使用者只丟一條
  YouTube 連結說「幫我轉逐字稿」也適用。
---

# YouTube → 中文逐字稿與字幕

把一條 YouTube 連結（或本機音／影片檔）變成兩份檔案：

- `<名稱>.txt` —— 純文字逐字稿
- `<名稱>.srt` —— 帶時間軸的字幕，可直接掛進影片播放器（VLC、剪輯軟體、YouTube 上字幕）

整套流程是**本機跑、免費、不外流**：用 Apple Silicon 的 GPU 跑 `mlx_whisper`。48 分鐘的影片約 6–7 分鐘完成。

## 什麼時候用

使用者想把影片／音訊轉成逐字稿或字幕時。特別適合中文為主、含大量伊斯蘭教術語（禮拜、拜功、清真、穆斯林、安拉、古蘭經、淨禮…）的內容——這類詞 Whisper 常聽成音近的錯字，這個 skill 會在最後做一次術語校對。

## 前置需求（第一次用才需要裝）

這些工具裝一次就好。先檢查，缺哪個再裝：

```bash
which yt-dlp ffmpeg                       # 下載與音訊處理
/usr/bin/python3 -c "import mlx_whisper"  # 語音辨識（裝在系統 Python）
```

- 缺 yt-dlp / ffmpeg：`brew install yt-dlp ffmpeg`
- 缺 mlx_whisper：`/usr/bin/python3 -m pip install mlx-whisper`

> 為什麼用系統 Python（`/usr/bin/python3`）？因為 `mlx_whisper` 已裝在那裡，模型也快取在那邊；用它最省事。**不要為這個 skill 另外建 venv 去裝 faster-whisper 在 CPU 上跑** —— 在 8GB RAM 的機器上 large 模型會因記憶體不足被系統中止（這是踩過的坑）。

## 怎麼跑

一行搞定。把網址換成實際連結，`--outdir` 指到要存的資料夾：

```bash
/usr/bin/python3 ~/.claude/skills/youtube-transcribe-zh/scripts/transcribe.py \
  "https://www.youtube.com/watch?v=XXXXXXXXXXX" \
  --outdir ~/Documents/伊斯蘭拜功教法學系列逐字稿
```

常用選項：
- `--name ep2` —— 自訂輸出檔名（預設用影片標題）。同一系列建議用 `ep2`、`ep3`… 方便排序。
- `--source` 也可以是本機檔案，例如已經下載好的 `something.mp3` 或 `.mp4`。

腳本會自動：下載音訊 → 辨識 → **偵測並切片重轉修正重複幻覺** → 輸出 txt 與 srt。

## 跑完一定要做的最後一步：術語校對

Whisper 對中文整體很準，但**阿拉伯文音譯詞常常是「音近字錯」**（例如把開場的「Alhamdulillah」聽成「阿姨姥特勒拉」）。腳本修不了這個——這需要靠理解上下文來判斷。

所以辨識完成後，**讀一遍 `references/islamic-terms.md`，再掃過逐字稿**，把明顯聽錯的伊斯蘭術語改成正確寫法（.txt 和 .srt 都要改）。判斷依據是「這是一場什麼主題的講座 + 前後文意思」。

重要原則：**這是有根據的推測，不是百分之百證實。** 改動較大或沒把握的地方，標記出來提醒使用者請懂阿拉伯文／熟悉教法的人最終確認，不要默默改掉就當定案。

## 想更快？（雲端選項）

本機方案每支約 6 分鐘、免費、隱私不外流，週更一支綽綽有餘，建議當預設。
若哪天要趕時間、且不介意把音訊上傳到第三方、願意花一點點錢，可改用雲端 Whisper API（例如 Groq，48 分鐘約 10–20 秒完成、花費約台幣 1 元內）。需要時再叫我幫忙接，預設不用。
