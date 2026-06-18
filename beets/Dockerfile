# beets — НЕразрушающий чекер библиотеки (целостность + дубликаты). Ночной cron.
# Не реннеймит и не двигает файлы — только каталогизирует в свою БД и проверяет.
FROM python:3.12-slim

# flac (--test), mp3val (битые mp3), libchromaprint-tools (fpcalc для chroma)
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
        flac mp3val libchromaprint-tools curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# hadolint ignore=DL3013
RUN pip install --no-cache-dir "beets[chroma]" pyacoustid requests

ARG SUPERCRONIC_VERSION=v0.2.46
ADD https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

COPY scripts/notify.sh /usr/local/bin/notify.sh
COPY beets/config.yaml /beets-config/config.yaml
COPY beets/check.sh /usr/local/bin/check.sh
COPY beets/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/notify.sh /usr/local/bin/check.sh /usr/local/bin/entrypoint.sh

# Конфиг — в образе (read-only), БД beets — в /config (mounted volume)
ENV BEETSDIR=/beets-config
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
