#!/usr/bin/env bash
# Генерит crontab из расписания и запускает supercronic.
set -euo pipefail

SCHEDULE="${FAKEFLAC_SCHEDULE:-0 5 * * *}"

if [ "${RUN_ON_START:-false}" = "true" ]; then
  echo "[entrypoint] прогон при старте"
  /usr/local/bin/check.sh || true
fi

echo "${SCHEDULE} /usr/local/bin/check.sh" > /tmp/crontab
echo "[entrypoint] расписание: ${SCHEDULE}"
exec /usr/local/bin/supercronic /tmp/crontab
