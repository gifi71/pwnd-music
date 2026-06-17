#!/usr/bin/env bash
# Генерит crontab из расписания и запускает supercronic.
# RUN_ON_START=true -> один прогон сразу при старте.
set -euo pipefail

SCHEDULE="${ENRICH_SCHEDULE:-0 4 * * *}"

if [ "${RUN_ON_START:-false}" = "true" ]; then
  echo "[entrypoint] прогон при старте"
  /usr/local/bin/enrich.sh || true
fi

echo "${SCHEDULE} /usr/local/bin/enrich.sh" > /tmp/crontab
echo "[entrypoint] расписание: ${SCHEDULE}"
exec /usr/local/bin/supercronic /tmp/crontab
