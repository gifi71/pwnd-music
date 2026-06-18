# Enrichment: вшивание обложек + синхро-лирики, .lrc рядом. Cron через supercronic.
FROM python:3.14-slim

# rsgain — запись ReplayGain/EBU R128 тегов (нормализация громкости).
# apt-пины в Debian брит — версии исчезают из репо
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
        flac ffmpeg curl ca-certificates rsgain \
    && rm -rf /var/lib/apt/lists/*

# pip-пакеты тянут свежие фиксы; воспроизводимость даёт git-тег образа
# hadolint ignore=DL3013
RUN pip install --no-cache-dir lrcup syncedlyrics eyeD3 mutagen

# supercronic — cron, корректно работающий в контейнере (логи в stdout)
ARG SUPERCRONIC_VERSION=v0.2.46
ADD https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

COPY scripts/notify.sh /usr/local/bin/notify.sh
COPY enrichment/enrich.sh /usr/local/bin/enrich.sh
COPY enrichment/lyrics.py /usr/local/bin/lyrics.py
COPY enrichment/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/notify.sh /usr/local/bin/enrich.sh /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
