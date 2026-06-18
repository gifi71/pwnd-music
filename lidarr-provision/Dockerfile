# Одноразовая декларативная настройка Lidarr через API.
# provision.py использует только stdlib — зависимостей нет.
FROM python:3.12-slim
COPY lidarr-provision/provision.py /provision.py
ENTRYPOINT ["python", "/provision.py"]
