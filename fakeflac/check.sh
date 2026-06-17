#!/usr/bin/env bash
# Ночной скан библиотеки на фейковый FLAC (перекод из lossy).
# НЕ удаляет ничего — пишет отчёт + Telegram. Решение за человеком.
set -uo pipefail

MUSIC="${MUSIC_DIR:-/music}"
REPORTS="${REPORTS_DIR:-/reports}"
TS="$(date +%F_%H%M)"
REPORT="${REPORTS}/fakeflac-${TS}.txt"
mkdir -p "$REPORTS"
cd /opt/FLAD || exit 1

echo "# Fake-FLAC скан $TS" > "$REPORT"
echo "# 'Final result' не Lossless = подозрение на перекод из lossy" >> "$REPORT"
echo "# Проверь в Spek, затем в Lidarr: удали файл + BLOCKLIST релиз" >> "$REPORT"
echo "" >> "$REPORT"

find "$MUSIC" -type f -iname '*.flac' 2>/dev/null | while read -r f; do
  rm -rf /opt/FLAD/temp; mkdir -p /opt/FLAD/temp
  res=$(python eval.py "$f" 2>/dev/null | grep '^Final result:' | tail -1)
  case "$res" in
    *Lossless*) : ;;                                   # подлинный
    "")         echo "ERROR (нет результата): $f" >> "$REPORT" ;;
    *)          echo "SUSPECT [${res#Final result: }]: $f" >> "$REPORT" ;;
  esac
done

n=$(grep -c '^SUSPECT' "$REPORT" 2>/dev/null || echo 0)
e=$(grep -c '^ERROR' "$REPORT" 2>/dev/null || echo 0)

if [ "$n" -gt 0 ]; then
  /usr/local/bin/notify.sh "⚠️ <b>Fake-FLAC</b> ($(hostname)): подозрительных <b>${n}</b>, ошибок ${e}.
Отчёт: $(basename "$REPORT")
Проверь в Spek → удали + blocklist релиз в Lidarr."
else
  /usr/local/bin/notify.sh "✅ <b>Fake-FLAC</b> ($(hostname)): фейков не найдено (ошибок ${e})."
fi
echo "[$(date)] done: suspect=$n error=$e -> $REPORT"
