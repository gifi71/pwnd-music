#!/usr/bin/env python3
"""
Декларативная автосвязка Prowlarr -> Lidarr (App) через API.
После этого КАЖДЫЙ индексер, добавленный в Prowlarr, синкается в Lidarr сам.
Идемпотентно: повторный запуск не плодит дубли.

Env:
  PROWLARR_URL         (default http://prowlarr:9696)
  PROWLARR_INTERNAL    URL Prowlarr глазами Lidarr (default http://prowlarr:9696)
  LIDARR_INTERNAL      URL Lidarr глазами Prowlarr (default http://lidarr:8686)
  PROWLARR_CONFIG_XML  (default /prowlarr-config/config.xml) — ключ Prowlarr
  LIDARR_CONFIG_XML    (default /lidarr-config/config.xml)   — ключ Lidarr
  APP_NAME             (default Lidarr)
"""
import os
import sys
import json
import time
import re
import urllib.request
import urllib.error

URL = os.environ.get("PROWLARR_URL", "http://prowlarr:9696").rstrip("/")
PROWLARR_INTERNAL = os.environ.get("PROWLARR_INTERNAL", "http://prowlarr:9696")
LIDARR_INTERNAL = os.environ.get("LIDARR_INTERNAL", "http://lidarr:8686")
PROWLARR_XML = os.environ.get("PROWLARR_CONFIG_XML", "/prowlarr-config/config.xml")
LIDARR_XML = os.environ.get("LIDARR_CONFIG_XML", "/lidarr-config/config.xml")
APP_NAME = os.environ.get("APP_NAME", "Lidarr")


def key_from(path):
    with open(path) as f:
        m = re.search(r"<ApiKey>([^<]+)</ApiKey>", f.read())
    if not m:
        sys.exit("ApiKey не найден в " + path)
    return m.group(1)


KEY = None
def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, method=method,
                               headers={"X-Api-Key": KEY,
                                        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


def wait_ready(timeout=300):
    for _ in range(timeout // 5):
        try:
            st, _ = req("GET", "/api/v1/system/status")
            if st == 200:
                return
        except Exception:
            pass
        time.sleep(5)
    sys.exit("Prowlarr API не поднялся за %ss" % timeout)


def set_field(fields, name, value):
    for f in fields:
        if f["name"] == name:
            f["value"] = value
            return
    fields.append({"name": name, "value": value})


def main():
    global KEY
    KEY = key_from(PROWLARR_XML)
    lidarr_key = key_from(LIDARR_XML)
    print("Prowlarr provision -> %s" % URL)
    wait_ready()

    st, existing = req("GET", "/api/v1/applications")
    if st == 200 and any(a.get("name") == APP_NAME for a in existing):
        print("  app '%s' уже есть — пропуск" % APP_NAME)
        return

    st, schema = req("GET", "/api/v1/applications/schema")
    if st != 200:
        sys.exit("schema applications: HTTP %s %s" % (st, schema))
    tmpl = next((s for s in schema if s.get("implementation") == "Lidarr"), None)
    if not tmpl:
        sys.exit("Lidarr-шаблон не найден в schema")

    tmpl["name"] = APP_NAME
    tmpl["syncLevel"] = "fullSync"
    fields = tmpl.setdefault("fields", [])
    set_field(fields, "prowlarrUrl", PROWLARR_INTERNAL)
    set_field(fields, "baseUrl", LIDARR_INTERNAL)
    set_field(fields, "apiKey", lidarr_key)

    st, resp = req("POST", "/api/v1/applications", tmpl)
    if st in (200, 201):
        print("  app Lidarr создан (syncLevel=fullSync) — индексеры синкаются сами")
    else:
        sys.exit("создание application: HTTP %s %s" % (st, resp))
    print("Готово.")


if __name__ == "__main__":
    main()
