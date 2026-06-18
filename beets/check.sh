#!/usr/bin/env bash
# Ночной НЕразрушающий чек библиотеки: каталогизация (без правок файлов),
# проверка целостности (badfiles) + дубликатов (duplicates). Отчёт + Telegram.
set -uo pipefail

MUSIC="${MUSIC_DIR:-/music}"
REPORTS="${REPORTS_DIR:-/reports}"
TS="$(date +%F_%H%M)"
REPORT="${REPORTS}/beets-${TS}.txt"
mkdir -p "$REPORTS"

# 1. Каталогизация в БД beets (move/copy/write/autotag = no -> файлы не трогаются)
beet import -A -q "$MUSIC" >/dev/null 2>&1 || true

# 2. Проверки (read-only)
{
  echo "# beets чек $TS"
  echo ""
  echo "## Битые/повреждённые файлы (badfiles):"
  beet badfiles 2>/dev/null || echo "(badfiles ничего не вернул)"
  echo ""
  echo "## Дубликаты (duplicates):"
  beet duplicates 2>/dev/null || echo "(дубликатов нет)"
} >> "$REPORT"

bad=$(beet badfiles 2>/dev/null | grep -ciE 'corrupt|error|FAILED|checksum' || true)
dup=$(beet duplicates 2>/dev/null | grep -c . || true)
[ -z "$bad" ] && bad=0
[ -z "$dup" ] && dup=0

if [ "$bad" -gt 0 ] || [ "$dup" -gt 0 ]; then
  /usr/local/bin/notify.sh "🧪 <b>beets чек</b> ($(hostname)): битых <b>${bad}</b>, дублей <b>${dup}</b>.
Отчёт: $(basename "$REPORT")"
else
  /usr/local/bin/notify.sh "✅ <b>beets чек</b> ($(hostname)): битых/дублей не найдено."
fi
echo "[$(date)] beets done: bad=$bad dup=$dup -> $REPORT"
