# Одноразовая декларативная настройка Lidarr через API.
# provision.py использует только stdlib — зависимостей нет.
FROM python:3.12-slim
COPY lidarr-provision/provision.py /provision.py
COPY templates/soularr-config.ini /soularr-template.ini
ENTRYPOINT ["python", "/provision.py"]
