#!/bin/sh
# Отправка уведомления в Telegram. Используется enrichment / fakeflac кронами.
# Тихо ничего не делает, если TELEGRAM_BOT_TOKEN/CHAT_ID не заданы.
# Использование: notify.sh "текст сообщения"

[ -z "$TELEGRAM_BOT_TOKEN" ] && exit 0
[ -z "$TELEGRAM_CHAT_ID" ] && exit 0

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=$1" \
  -d "parse_mode=HTML" \
  -d "disable_web_page_preview=true" >/dev/null 2>&1 || true
