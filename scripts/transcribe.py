#!/usr/bin/env python3
"""
YouTube → 中文逐字稿 + 帶時間軸字幕（針對含大量伊斯蘭專有名詞的影片）

流程：
  1. yt-dlp 下載音訊（若傳入的是 YouTube 網址）
  2. mlx_whisper（large-v3-turbo，Apple GPU 加速）做中文辨識
  3. 自動偵測 Whisper 的「重複幻覺」段落（某字狂重複），切片重轉修正
  4. 輸出 <名稱>.txt（純文字）與 <名稱>.srt（帶時間軸字幕）

用法：
  python3 transcribe.py <YouTube網址或本機音檔> [--outdir 輸出資料夾] [--name 檔名]
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
# 偏置提示：讓辨識更傾向繁體中文與這些術語（不保證拼對，後續仍建議人工校對）
DEFAULT_PROMPT = (
    "以下是一段繁體中文的伊斯蘭教拜功教法學講座，內容包含禮拜、清真、穆斯林、"
    "安拉、古蘭經、祈禱、淨禮、朝向等詞彙。"
)


def sanitize(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name).strip()
    return name[:80] or "transcript"


def get_audio(source: str, workdir: str):
    """回傳 (音檔路徑, 建議檔名)。source 可為網址或本機檔案。"""
    if os.path.exists(source):
        base = sanitize(os.path.splitext(os.path.basename(source))[0])
        return source, base

    # 取標題當預設檔名
    try:
        title = subprocess.check_output(
            ["yt-dlp", "--print", "%(title)s", "--skip-download", source],
            text=True,
        ).strip().splitlines()[-1]
    except Exception:
        title = "transcript"
    base = sanitize(title)

    out_tmpl = os.path.join(workdir, "audio.%(ext)s")
    print(f"⬇️  下載音訊：{title}", flush=True)
    subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
         "-o", out_tmpl, source],
        check=True,
    )
    audio = os.path.join(workdir, "audio.mp3")
    if not os.path.exists(audio):
        sys.exit("❌ 下載失敗，找不到音檔")
    return audio, base


# ---- 幻覺偵測 / 清理 ----
PUNCT = "。，、；：！？「」『』（）()…—-. \n\t"


def longest_run(s: str) -> int:
    best = run = 1
    for i in range(1, len(s)):
        run = run + 1 if s[i] == s[i - 1] else 1
        best = max(best, run)
    return best if s else 0


def is_hallucination(text: str) -> bool:
    core = "".join(c for c in text if c not in PUNCT)
    if len(core) < 12:
        return False
    # 同一個字連續重複 8 次以上 → 幾乎一定是 Whisper 鬼打牆
    if longest_run(core) >= 8:
        return True
    # 整段去重後字種極少（重複短語）→ 也是幻覺
    if len(set(core)) / len(core) < 0.12:
        return True
    return False


def collapse_repeats(text: str) -> str:
    # 把連續重複 4 次以上的同字壓成 1 個
    text = re.sub(r"(.)\1{3,}", r"\1", text)
    # 把連續重複 3 次以上的短語（2-6 字）壓成 1 次
    text = re.sub(r"(.{2,6}?)\1{2,}", r"\1", text)
    return text.strip()


def cut_audio(audio: str, start: float, dur: float, out: str):
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(start), "-t", str(dur), "-i", audio, out],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def ts(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60)
    s = int(sec % 60); ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="YouTube 網址或本機音檔路徑")
    ap.add_argument("--outdir", default=".", help="輸出資料夾")
    ap.add_argument("--name", default=None, help="輸出檔名（不含副檔名）")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--language", default="zh")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = ap.parse_args()

    import mlx_whisper  # 延後 import，讓 --help 不必載入

    os.makedirs(args.outdir, exist_ok=True)
    with tempfile.TemporaryDirectory() as workdir:
        audio, base = get_audio(args.source, workdir)
        name = args.name or base

        print("🎙️  辨識中（首次會下載模型）…", flush=True)
        result = mlx_whisper.transcribe(
            audio, path_or_hf_repo=args.model, language=args.language,
            initial_prompt=args.prompt, verbose=False,
        )
        segs = result["segments"]

        # 偵測 + 修正幻覺段
        bad = [i for i, s in enumerate(segs) if is_hallucination(s["text"])]
        if bad:
            print(f"🩹 偵測到 {len(bad)} 段重複幻覺，切片重轉修正…", flush=True)
        for i in bad:
            s = segs[i]
            start = max(0, s["start"] - 2)
            dur = (s["end"] - s["start"]) + 4
            clip = os.path.join(workdir, f"clip_{i}.mp3")
            try:
                cut_audio(audio, start, dur, clip)
                r = mlx_whisper.transcribe(
                    clip, path_or_hf_repo=args.model, language=args.language,
                    condition_on_previous_text=False,  # 關掉前文制約，避免再次鬼打牆
                    initial_prompt=args.prompt, verbose=False,
                )
                fixed = collapse_repeats(r["text"])
                # 若重轉後仍是幻覺，至少把原本的重複壓掉
                segs[i]["text"] = fixed if not is_hallucination(fixed) else collapse_repeats(s["text"])
            except Exception as e:
                segs[i]["text"] = collapse_repeats(s["text"])
                print(f"   ⚠️ 第 {i} 段重轉失敗（{e}），改為壓縮重複", flush=True)

        # 輸出
        txt_path = os.path.join(args.outdir, f"{name}.txt")
        srt_path = os.path.join(args.outdir, f"{name}.srt")
        srt_lines, txt_lines = [], []
        for i, s in enumerate(segs, 1):
            t = s["text"].strip()
            if not t:
                continue
            srt_lines.append(f"{i}\n{ts(s['start'])} --> {ts(s['end'])}\n{t}\n")
            txt_lines.append(t)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines) + "\n")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        print(f"\n✅ 完成（{len(segs)} 段，修正 {len(bad)} 處幻覺）")
        print(f"   逐字稿：{txt_path}")
        print(f"   字幕檔：{srt_path}")


if __name__ == "__main__":
    main()
