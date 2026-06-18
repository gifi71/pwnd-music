# Одноразовая автосвязка Prowlarr -> Lidarr через API. Только stdlib.
FROM python:3.12-slim
COPY prowlarr-provision/provision.py /provision.py
ENTRYPOINT ["python", "/provision.py"]
