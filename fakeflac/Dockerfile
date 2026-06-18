# Fake-FLAC детектор (FLAD, ML/ONNX). Ночной cron через supercronic.
FROM python:3.14-slim

# apt-пины в Debian брит — версии исчезают из репо
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl unzip flac ffmpeg libsndfile1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# pip-пакеты тянут свежие фиксы; воспроизводимость даёт git-тег образа
# hadolint ignore=DL3013
RUN pip install --no-cache-dir \
        numpy librosa resampy matplotlib Pillow onnxruntime soundfile

# FLAD + модель (онл. в репо только placeholder; модель — в релизе v0.1)
RUN git clone --depth 1 https://github.com/Sg4Dylan/FLAD /opt/FLAD \
    && curl -fsSL -o /tmp/model.zip \
        https://github.com/Sg4Dylan/FLAD/releases/download/v0.1/model.zip \
    && unzip -o /tmp/model.zip -d /tmp/model \
    && mkdir -p /opt/FLAD/onnx \
    && find /tmp/model -iname '*.onnx' -exec cp {} /opt/FLAD/onnx/flad.onnx \; \
    && rm -rf /tmp/model.zip /tmp/model \
    && test -f /opt/FLAD/onnx/flad.onnx \
    && chmod -R a+w /opt/FLAD       # eval.py пишет temp/ относительно cwd

ARG SUPERCRONIC_VERSION=v0.2.33
ADD https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64 /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

COPY scripts/notify.sh /usr/local/bin/notify.sh
COPY fakeflac/check.sh /usr/local/bin/check.sh
COPY fakeflac/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/notify.sh /usr/local/bin/check.sh /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
