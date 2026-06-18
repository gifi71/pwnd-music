#!/usr/bin/env python3
"""
Декларативная настройка Lidarr через API (perfectionism-дефолты):
  - Quality Profile: lossless-first, MP3-320 только как fallback, cutoff=FLAC
  - Metadata Profile: тянуть ВСЁ (Album/EP/Single + все secondary)
  - Track Naming: Артист/Альбом (Год)/NN - Трек
  - Metadata Consumer (Kodi): писать обложки артистов/альбомов на диск

Идемпотентно: повторный запуск не плодит дубли, обновляет существующее.
Env:
  LIDARR_URL        (default http://lidarr:8686)
  LIDARR_API_KEY    (если пусто — читается из LIDARR_CONFIG_XML)
  LIDARR_CONFIG_XML (default /lidarr-config/config.xml)
"""
import os
import sys
import json
import time
import re
import urllib.request
import urllib.error

URL = os.environ.get("LIDARR_URL", "http://lidarr:8686").rstrip("/")
CONFIG_XML = os.environ.get("LIDARR_CONFIG_XML", "/lidarr-config/config.xml")
PROFILE_NAME = os.environ.get("LIDARR_QUALITY_PROFILE_NAME", "Lossless (perfectionist)")

LOSSLESS = ["FLAC", "ALAC", "APE", "WavPack", "FLAC 24bit", "ALAC 24bit", "WAV"]
FALLBACK = ["MP3-320"]          # только когда lossless вообще нет
CUTOFF_QUALITY = "FLAC"          # апгрейд до настоящего FLAC и стоп


def api_key():
    k = os.environ.get("LIDARR_API_KEY")
    if k:
        return k
    with open(CONFIG_XML) as f:
        m = re.search(r"<ApiKey>([^<]+)</ApiKey>", f.read())
    if not m:
        sys.exit("ApiKey не найден в " + CONFIG_XML)
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
        return e.code, e.read().decode()[:500]


def wait_ready(timeout=300):
    for _ in range(timeout // 5):
        try:
            st, _ = req("GET", "/api/v1/system/status")
            if st == 200:
                return
        except Exception:
            pass
        time.sleep(5)
    sys.exit("Lidarr API не поднялся за %ss" % timeout)


def set_allowed(items, names):
    """Рекурсивно allowed=true для качеств из names (в группах и одиночных)."""
    for it in items:
        q = it.get("quality")
        if q and q["name"] in names:
            it["allowed"] = True
        sub = it.get("items")
        if sub:
            set_allowed(sub, names)
            # группа allowed, если включён хоть один её элемент
            if any(s.get("allowed") for s in sub):
                it["allowed"] = True


def find_cutoff_id(items, name):
    """cutoff обязан ссылаться на разрешённое качество или ГРУППУ.
    Если качество вложено в группу — возвращаем id группы, иначе id качества."""
    for it in items:
        q = it.get("quality")
        if q and q["name"] == name:          # одиночное качество верхнего уровня
            return q["id"]
        sub = it.get("items")
        if sub:
            for s in sub:
                sq = s.get("quality")
                if sq and sq["name"] == name:  # внутри группы -> id группы
                    return it["id"]
    return None


def provision_quality():
    st, existing = req("GET", "/api/v1/qualityprofile")
    if st == 200 and any(p["name"] == PROFILE_NAME for p in existing):
        print("  quality profile '%s' уже есть — пропуск" % PROFILE_NAME)
        return
    st, schema = req("GET", "/api/v1/qualityprofile/schema")
    if st != 200:
        sys.exit("schema qualityprofile: HTTP %s %s" % (st, schema))
    schema["name"] = PROFILE_NAME
    schema["upgradeAllowed"] = True
    set_allowed(schema["items"], set(LOSSLESS + FALLBACK))
    cid = find_cutoff_id(schema["items"], CUTOFF_QUALITY)
    if cid is None:
        sys.exit("cutoff '%s' не найден" % CUTOFF_QUALITY)
    schema["cutoff"] = cid
    st, resp = req("POST", "/api/v1/qualityprofile", schema)
    if st in (200, 201):
        print("  quality profile создан (cutoff=%s)" % CUTOFF_QUALITY)
    else:
        sys.exit("создание qualityprofile: HTTP %s %s" % (st, resp))


def provision_metadata_profile():
    """Тянуть ВСЁ: все primary + secondary типы, статусы Official+Promotion."""
    st, profiles = req("GET", "/api/v1/metadataprofile")
    if st != 200:
        sys.exit("GET metadataprofile: HTTP %s" % st)
    prof = next((p for p in profiles if p["id"] == 1), profiles[0])
    for t in prof["primaryAlbumTypes"]:
        t["allowed"] = True
    for t in prof["secondaryAlbumTypes"]:
        t["allowed"] = True
    for t in prof["releaseStatuses"]:
        t["allowed"] = t["releaseStatus"]["name"] in ("Official", "Promotion")
    st, resp = req("PUT", "/api/v1/metadataprofile/%d" % prof["id"], prof)
    print("  metadata profile -> все типы (HTTP %s)" % st)


def provision_naming():
    st, naming = req("GET", "/api/v1/config/naming")
    if st != 200:
        sys.exit("GET naming: HTTP %s" % st)
    naming["renameTracks"] = True
    naming["replaceIllegalCharacters"] = True
    naming["artistFolderFormat"] = "{Artist Name}"
    naming["standardTrackFormat"] = \
        "{Album Title} ({Release Year})/{track:00} - {Track Title}"
    naming["multiDiscTrackFormat"] = \
        "{Album Title} ({Release Year})/CD{medium:00}/{track:00} - {Track Title}"
    st, resp = req("PUT", "/api/v1/config/naming", naming)
    print("  naming -> Артист/Альбом (Год)/NN - Трек (HTTP %s)" % st)


def provision_rootfolder():
    """Создать Root Folder /data/music с дефолтными профилями."""
    root = os.environ.get("LIDARR_ROOT_FOLDER", "/data/music")
    st, existing = req("GET", "/api/v1/rootfolder")
    if st == 200 and any(r.get("path", "").rstrip("/") == root for r in existing):
        print("  root folder '%s' уже есть — пропуск" % root)
        return
    st, qps = req("GET", "/api/v1/qualityprofile")
    qid = next((p["id"] for p in qps if p["name"] == PROFILE_NAME),
               qps[0]["id"] if qps else 1)
    body = {
        "path": root,
        "name": "Music",
        "defaultQualityProfileId": qid,
        "defaultMetadataProfileId": 1,
        "defaultMonitorOption": "all",
        "defaultNewItemMonitorOption": "all",
        "defaultTags": [],
    }
    st, resp = req("POST", "/api/v1/rootfolder", body)
    if st in (200, 201):
        print("  root folder '%s' создан" % root)
    else:
        print("  root folder: HTTP %s %s" % (st, resp))


def provision_metadata_consumer():
    """Kodi/Emby консьюмер: писать обложки артистов/альбомов на диск."""
    st, consumers = req("GET", "/api/v1/metadata")
    if st != 200:
        sys.exit("GET metadata: HTTP %s" % st)
    kodi = next((m for m in consumers if "Kodi" in m["name"]), None)
    if not kodi:
        print("  Kodi-консьюмер не найден — пропуск")
        return
    kodi["enable"] = True
    for f in kodi.get("fields", []):
        if f["name"] in ("artistMetadata", "albumMetadata", "trackMetadata",
                         "artistImages", "albumImages"):
            f["value"] = True
    st, resp = req("PUT", "/api/v1/metadata/%d" % kodi["id"], kodi)
    print("  Kodi metadata consumer -> обложки на диск (HTTP %s)" % st)


def provision_ui_prefs():
    """РФ-дефолты UI: русский язык, понедельник, русские форматы даты/времени.
    uiLanguage=11 — id русского для Lidarr 3.1 (env LIDARR_UI_LANGUAGE для override)."""
    st, ui = req("GET", "/api/v1/config/ui")
    if st != 200:
        print("  ui config: HTTP %s — пропуск" % st)
        return
    ui["uiLanguage"] = int(os.environ.get("LIDARR_UI_LANGUAGE", "11"))  # 11 = русский
    ui["firstDayOfWeek"] = 1                        # понедельник
    ui["calendarWeekColumnHeader"] = "ddd D.MM"
    ui["shortDateFormat"] = "DD.MM.YYYY"
    ui["longDateFormat"] = "dddd, D MMMM YYYY"
    ui["timeFormat"] = "HH:mm"
    st, _ = req("PUT", "/api/v1/config/ui", ui)
    print("  ui -> русский + понедельник + РФ дата/время (HTTP %s)" % st)


def provision_write_tags():
    """Тэгать аудиофайлы чистой метадатой (по умолчанию Lidarr этого не делает).
    embedCoverArt оставляем включённым (вшивает обложку в трек)."""
    st, mp = req("GET", "/api/v1/config/metadataprovider")
    if st != 200:
        print("  metadataprovider: HTTP %s — пропуск" % st)
        return
    mp["writeAudioTags"] = "allFiles"
    mp["embedCoverArt"] = True
    st, _ = req("PUT", "/api/v1/config/metadataprovider", mp)
    print("  write audio tags -> allFiles + embed обложки (HTTP %s)" % st)


def prune_quality_profiles():
    """Удалить все профили качества кроме перфекционистского.
    Профиль в использовании удалить нельзя — такие пропускаем (catch)."""
    st, profiles = req("GET", "/api/v1/qualityprofile")
    if st != 200:
        return
    for p in profiles:
        if p["name"] == PROFILE_NAME:
            continue
        dst, resp = req("DELETE", "/api/v1/qualityprofile/%d" % p["id"])
        if dst in (200, 204):
            print("  удалён профиль '%s'" % p["name"])
        else:
            print("  профиль '%s' не удалён (в использовании?) HTTP %s" % (p["name"], dst))


def render_soularr():
    """Сгенерить config/soularr/config.ini из шаблона + ключи (Lidarr из
    config.xml, slskd из env). Убирает ручную правку конфига Soularr."""
    tmpl = os.environ.get("SOULARR_TEMPLATE", "/soularr-template.ini")
    out = os.environ.get("SOULARR_CONFIG_OUT")           # напр. /soularr-out/config.ini
    slskd_key = os.environ.get("SLSKD_API_KEY", "")
    if not out:
        return
    if os.path.exists(out):
        print("  soularr config уже есть — пропуск")
        return
    if not os.path.exists(tmpl):
        print("  soularr шаблон не найден (%s) — пропуск" % tmpl)
        return
    with open(tmpl) as f:
        content = f.read()
    content = content.replace("LIDARR_API_KEY", KEY).replace("SLSKD_API_KEY", slskd_key)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(content)
    print("  soularr config сгенерён -> %s" % out)


def main():
    global KEY
    KEY = api_key()
    print("Lidarr provision -> %s" % URL)
    wait_ready()
    print("[1/5] quality profile")
    provision_quality()
    print("[2/5] metadata profile")
    provision_metadata_profile()
    print("[3/5] naming")
    provision_naming()
    print("[4/5] metadata consumer")
    provision_metadata_consumer()
    print("[5/5] root folder")
    provision_rootfolder()
    print("[+] ui prefs (РФ)")
    provision_ui_prefs()
    print("[+] write audio tags")
    provision_write_tags()
    print("[+] прочистка профилей качества")
    prune_quality_profiles()
    print("[+] soularr config")
    render_soularr()
    print("Готово.")


if __name__ == "__main__":
    main()
