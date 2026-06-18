#!/usr/bin/env python3
"""
Синхро-лирика каскадом провайдеров (LRCLIB -> Musixmatch -> NetEase -> Genius)
через syncedlyrics. Кладёт .lrc рядом + вшивает в тег (lrcup embed).
Покрывает больше, чем только LRCLIB — особенно русскую/не-западную музыку.
Идемпотентно: пропускает файлы, у которых уже есть .lrc.
"""
import os
import subprocess
import syncedlyrics
from mutagen import File as MutagenFile

MUSIC = os.environ.get("MUSIC_DIR", "/music")
EXTS = (".flac", ".mp3")
done = 0
miss = 0

for root, _, files in os.walk(MUSIC):
    for fn in files:
        if not fn.lower().endswith(EXTS):
            continue
        path = os.path.join(root, fn)
        lrc_path = os.path.splitext(path)[0] + ".lrc"
        if os.path.exists(lrc_path):
            continue
        try:
            audio = MutagenFile(path, easy=True)
            artist = (audio.get("artist") or [""])[0]
            title = (audio.get("title") or [""])[0]
        except Exception:
            continue
        if not artist or not title:
            continue
        try:
            lrc = syncedlyrics.search(f"{artist} {title}", synced_only=True)
        except Exception:
            lrc = None
        if not lrc:
            miss += 1
            continue
        try:
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.write(lrc)
            subprocess.run(["lrcup", "embed", lrc_path, path],
                           capture_output=True, timeout=30)
            done += 1
        except Exception:
            pass

print(f"lyrics: embedded={done} not_found={miss}")
