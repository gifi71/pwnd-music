#!/usr/bin/env bash
# Обогащение библиотеки: вшить обложку в каждый трек без неё + синхро-лирику
# (LRCLIB) в теги и .lrc рядом. Идемпотентно — пропускает уже обработанное.
set -uo pipefail

MUSIC="${MUSIC_DIR:-/music}"
TS="$(date +%F_%H%M)"
LOG="/tmp/enrich-${TS}.log"

echo "[$(date)] enrich start: $MUSIC" | tee "$LOG"

# ── 1. Вшить обложку из cover.* в файлы без встроенной картинки ──
find "$MUSIC" -type d 2>/dev/null | while read -r dir; do
  cover=""
  for c in cover.jpg cover.png folder.jpg front.jpg; do
    [ -f "$dir/$c" ] && cover="$dir/$c" && break
  done
  [ -z "$cover" ] && continue

  find "$dir" -maxdepth 1 -type f -iname '*.flac' 2>/dev/null | while read -r f; do
    # exit!=0 от export-picture = нет PICTURE-блока -> вшиваем
    if ! metaflac --export-picture-to=- "$f" >/dev/null 2>&1; then
      metaflac --import-picture-from="3||||$cover" "$f" 2>>"$LOG" \
        && echo "FLAC art: $f" >>"$LOG"
    fi
  done

  find "$dir" -maxdepth 1 -type f -iname '*.mp3' 2>/dev/null | while read -r f; do
    if ! eyeD3 "$f" 2>/dev/null | grep -q 'FRONT_COVER'; then
      eyeD3 --add-image="$cover:FRONT_COVER" "$f" >/dev/null 2>>"$LOG" \
        && echo "MP3 art: $f" >>"$LOG"
    fi
  done
done

# ── 2. Синхро-лирика из LRCLIB: вшить в теги + .lrc рядом ──
# lrcup читает теги, ищет на lrclib.net, embed + download (.lrc sidecar).
echo "[$(date)] lyrics pass (lrcup autosearch)" >>"$LOG"
lrcup autosearch --embed --download "$MUSIC" >>"$LOG" 2>&1 || \
  echo "lrcup завершился с ошибкой (см. выше)" >>"$LOG"

art_lines=$(grep -c ' art: ' "$LOG" 2>/dev/null || echo 0)
echo "[$(date)] enrich done. art=$art_lines" | tee -a "$LOG"

/usr/local/bin/notify.sh "🎵 <b>Enrichment</b> завершён ($(hostname))
Обложек вшито: ${art_lines}
Лог: $(basename "$LOG")"
