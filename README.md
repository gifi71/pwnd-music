# 🎵 pwnd-music

> Полностью автоматический self-hosted музыкальный стек: стриминг как в Spotify,
> авто-пополнение библиотеки из торрентов и Soulseek в lossless, персональная
> статистика прослушиваний, обложки/тексты/метадата — всё по умолчанию.

<p>
<img alt="License" src="https://img.shields.io/github/license/gifi71/pwnd-music">
<img alt="Build" src="https://github.com/gifi71/pwnd-music/actions/workflows/build-images.yml/badge.svg">
<img alt="Docker Compose" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
<img alt="Self-hosted" src="https://img.shields.io/badge/self--hosted-yes-success">
</p>

Navidrome (стриминг) ← Lidarr (менеджер коллекции) ← qBittorrent + Soulseek
(источники), Koito + Maloja (статистика), всё в Docker Compose. Из коробки:
только настоящий FLAC, обложки и синхро-тексты в каждом треке, раскладка
`Артист/Альбом (Год)/`, раздача обратно в сообщество.

<!-- TODO(владелец): добавить скриншоты UI Navidrome/Koito в docs/screenshots/ -->

## ⚡ Quickstart

Кратко (полная пошаговая установка с созданием каталогов — в разделе
[«Запуск стека»](#запуск-стека), выполняй именно его, иначе будут ошибки прав):

```bash
git clone https://github.com/gifi71/pwnd-music.git /opt/pwnd-music
cd /opt/pwnd-music
cp .env.example .env && nano .env          # пути, таймзона, пароли, ключи
# ... создать каталоги config/ и data/ (см. «Запуск стека») ...
docker compose up -d                       # первый раз СОБИРАЕТ кастомные
                                           # образы локально (~неск. минут)
```

Первый `up` собирает 4 кастомных образа (enrichment, fakeflac, *-provision) —
это нормально. Если у тебя [GHCR-пакеты сделаны публичными](#кастомные-образы-cicd),
вместо сборки можно `docker compose pull`.

Затем ~10 минут пост-настройки (ниже): ключи Koito/Maloja, Last.fm/Spotify,
трекеры.

## Состав

| Сервис | Порт | Назначение |
|---|---|---|
| [Navidrome](https://www.navidrome.org/) | 4533 | Стриминг, веб-плеер, Subsonic API (мобильные клиенты: Symfonium, Tempo, play:Sub) |
| [Koito](https://koito.io/) ×N | 4110, 4111… | Персональная статистика прослушиваний — свой инстанс на юзера (Koito однопользовательский) |
| [multi-scrobbler](https://github.com/FoxxMD/multi-scrobbler) | 9078 | Роутер скробблов: по токену раскидывает прослушивания юзеров в их Koito |
| [Maloja](https://github.com/krateng/maloja) | 42010 | Углублённая статистика/анализ прослушиваний (пишется параллельно с Koito) |
| [Lidarr](https://lidarr.audio/) | 8686 | Менеджер коллекции: следит за артистами, ищет релизы |
| [Prowlarr](https://prowlarr.com/) | 9696 | Менеджер торрент-индексеров (RuTracker, NNM-Club), сам прописывает их в Lidarr |
| [qBittorrent](https://www.qbittorrent.org/) | 8090 | Торрент-клиент для Lidarr |
| [slskd](https://github.com/slskd/slskd) | 5030 | Soulseek-демон + веб-UI для ручного поиска |
| [Soularr](https://github.com/mrusse/soularr) | 8265 | Мост: wanted-список Lidarr → автопоиск в Soulseek через slskd |
| lidarr-provision | — | Одноразовая настройка Lidarr через API (качество/метадата/нейминг/обложки) |
| enrichment | — | Ночной cron: вшивает обложки и синхро-лирику в треки, кладёт `.lrc` рядом |
| fakeflac | — | Ночной cron: детектит фейковый (перекодированный) FLAC, шлёт отчёт |

## Поток данных

```mermaid
flowchart TD
    U([ты: добавил артиста/альбом]) --> L[Lidarr]
    L -- "wanted-список" --> S[Soularr]
    L -- "релиз найден на трекере" --> Q[qBittorrent]
    S -- "API" --> SL[slskd]
    SL -- "поиск" --> SS([сеть Soulseek])
    SL --> D1["/data/downloads/slskd/complete"]
    Q --> D2["/data/downloads/torrents"]
    D1 --> IMP[Lidarr: импорт hardlink]
    D2 --> IMP
    IMP --> M["/data/music"]
    M --> N[Navidrome: сканирует и стримит]
    N -- "трек доигран → ListenBrainz API" --> MS[multi-scrobbler]
    MS -- "токен gifi" --> K1[koito-gifi]
    MS -- "токен al" --> K2[koito-al]
    MS -- "токен gifi" --> MJ[maloja]
```

## Структура на диске

```
${DATA_DIR}/                  # большой диск (по умолчанию /srv/media)
├── music/                    # библиотека
└── downloads/
    ├── torrents/             # загрузки qBittorrent
    └── slskd/
        ├── complete/         # завершённые загрузки slskd
        └── incomplete/

репозиторий/
├── docker-compose.yml
├── .env                      # секреты (НЕ в гите)
├── ms-config/config.json     # роутинг multi-scrobbler (секреты — через env)
├── templates/soularr-config.ini
└── config/                   # runtime-данные контейнеров (НЕ в гите)
```

Единый корень `${DATA_DIR}` смонтирован в Lidarr как `/data` целиком: загрузки и
библиотека на одной файловой системе, поэтому импорт — мгновенный hardlink без
удвоения занятого места.

## Требования к хосту

Подойдёт любой хост с Docker: VM, LXC-контейнер, отдельная машина или NAS.
Ориентир:

- **Docker** + **Docker Compose** (`curl -fsSL https://get.docker.com | sh`).
- **CPU/RAM:** 2 vCPU / 4 ГБ (хватает; enrichment/fakeflac-кроны прожорливее в
  момент ночного прогона — librosa/onnx).
- **Диск:** небольшой системный (≈20 ГБ) + отдельный большой том под музыку,
  смонтированный в `${DATA_DIR}` (по умолчанию `/srv/media`). Загрузки и
  библиотека должны быть на **одной ФС** — иначе импорт копирует, а не
  хардлинкает (удвоение места, см. ниже).

> На Proxmox это обычно LXC (Debian 12, unprivileged, в Options включить
> `keyctl=1,nesting=1` для Docker) или VM; том с музыкой пробрасывается
> mountpoint'ом/диском в `${DATA_DIR}`. Конкретный способ проброса — на твоё
> усмотрение, стек к нему безразличен.

### Запуск стека

```bash
git clone https://github.com/gifi71/pwnd-music.git /opt/pwnd-music && cd /opt/pwnd-music

# 1. Окружение
cp .env.example .env
nano .env        # пути, таймзона, логин Soulseek, пароли, API-ключ slskd

# 2. Подхватить переменные из .env для следующих шагов
set -a; . ./.env; set +a

# 3. Конфиг Soularr
mkdir -p config/soularr
cp templates/soularr-config.ini config/soularr/config.ini
# LIDARR_API_KEY вставим после первого запуска (шаг ниже)

# 4. Каталоги конфигов. ВАЖНО: создать заранее — иначе docker создаст их
# под root, а сервисы бегут под PUID и не смогут писать.
mkdir -p config/{navidrome,koito-gifi,koito-al,maloja,multi-scrobbler,lidarr,prowlarr,qbittorrent,slskd,soularr,fakeflac-reports}
sudo chown -R "$PUID:$PGID" config

# 5. Каталоги данных
sudo mkdir -p "$DATA_DIR"/music "$DATA_DIR"/downloads/torrents \
              "$DATA_DIR"/downloads/slskd/{complete,incomplete}
sudo chown -R "$PUID:$PGID" "$DATA_DIR"

# 6. Поехали
docker compose up -d
```

## Пост-настройка (один раз, ~10 минут)

### 1. Персональный скробблинг (Navidrome → multi-scrobbler → Koito)

У каждого юзера свой Koito; multi-scrobbler различает юзеров по токену
(`LB_TOKEN_*` из `.env`). Кто статистику не хочет — просто не включает
скробблинг у себя, остальное его не касается.

Подключение юзера (пример — gifi, для al аналогично со своими значениями):

1. Открыть Navidrome `http://<host>:4533` — при первом входе создаётся админ.
2. Открыть Koito юзера `http://<host>:4110` (al — `:4111`). Визарда нет —
   аккаунт создан автоматически при первом старте (логин/пароль —
   `KOITO_USERNAME` / `KOITO_PASSWORD` из `.env`). Нажать **Sign In**.
3. Settings → **API Keys** → скопировать ключ → вписать в `.env` в
   `KOITO_API_KEY_GIFI` → `docker compose up -d multi-scrobbler`.
4. В Navidrome под юзером gifi: Settings → Personal → включить
   **Scrobble to ListenBrainz** → вставить токен `LB_TOKEN_GIFI` из `.env` → Save.
5. Проверка: послушать трек до конца → появится в его Koito.
   Статус роутера: `http://<host>:9078`.

### 2. Lidarr: базовая настройка

1. Открыть `http://<host>:8686`, задать аутентификацию.
2. Settings → Media Management → Root Folder: **`/data/music`**.
3. Settings → General → скопировать **API Key** (нужен для Soularr).
4. Русский интерфейс: Settings → UI → Language → **Russian**.

### 3. Lidarr → qBittorrent

1. Логин qBittorrent — `admin`, пароль при первом старте временный, смотреть:
   `docker logs qbittorrent` → строка "temporary password".
2. Открыть `http://<host>:8090`, сменить пароль:
   Tools → Options → Web UI.
3. Там же Downloads → Default Save Path: **`/data/downloads/torrents`**,
   и Behavior → Language → **Русский**.
4. В Lidarr: Settings → Download Clients → `+` → qBittorrent:
   Host `qbittorrent`, Port `8090` (= `QBIT_WEBUI_PORT`), логин/пароль
   из шага 2, Category `music`.

### 4. Lidarr → Soularr → slskd

1. Вписать API-ключ Lidarr (шаг 2.3) в `config/soularr/config.ini`
   вместо `LIDARR_API_KEY`.
2. Вместо `SLSKD_API_KEY` — то же значение, что в `.env`.
3. `docker compose restart soularr`.
4. Проверка: `docker logs soularr` — не должно быть ошибок подключения.
   Веб-морда Soularr: `http://<host>:8265`.

slskd доступен на `http://<host>:5030` (логин из `.env`) — там же ручной поиск
по Soulseek, если хочется качнуть что-то мимо Lidarr.

### 5. Prowlarr: торрент-индексеры (NNM-Club, RuTracker)

1. Открыть `http://<host>:9696`, задать аутентификацию.
2. Если трекеры/метадата блокируются: Settings → Indexers → `+` Proxy →
   Socks5 (хост/порт/креды своего прокси), Tag: `proxy`.
3. Indexers → `+` → найти **NoNameClub** (или RuTracker) → логин/пароль
   аккаунта трекера → при необходимости Tag `proxy` → Test → Save.

Связка Prowlarr → Lidarr создаётся **автоматически** контейнером
`prowlarr-provision` при `docker compose up` (App «Lidarr», fullSync). Каждый
добавленный индексер сам появляется в Lidarr — Settings → Apps руками настраивать
не нужно. (Если хочешь проверить: Prowlarr → Settings → Apps → там уже есть Lidarr.)

### Добавить юзера с личной статистикой

1. `docker-compose.yml`: скопировать блок `koito-gifi` → `koito-<имя>`,
   заменить имя контейнера, том (`config/koito-<имя>`) и порт.
2. `.env`: добавить `LB_TOKEN_<ИМЯ>` (openssl rand -hex 16),
   `KOITO_API_KEY_<ИМЯ>=changeme`, `KOITO_<ИМЯ>_PORT`.
3. В compose у `multi-scrobbler` пробросить обе новые переменные в `environment`.
4. `ms-config/config.json`: добавить source и client по образцу существующих.
5. `docker compose up -d`, затем шаги 2–4 из «Персонального скробблинга»
   (забрать API-ключ нового Koito, юзер вставляет свой токен в Navidrome).

## Перфекционизм по умолчанию

Стек настроен на максимум качества «из коробки». Что работает автоматически:

- **lidarr-provision** — одноразовый контейнер, при каждом `up` декларативно
  применяет в Lidarr через API: профиль качества (только lossless, MP3-320
  лишь как fallback когда FLAC вообще нет), Metadata Profile «тянуть всё»
  (альбомы + синглы + EP + все вторичные типы), раскладку
  `Артист/Альбом (Год)/NN - Трек`, запись обложек артистов/альбомов на диск
  (Kodi-консьюмер). Читает API-ключ Lidarr из его `config.xml` сам.
- **enrichment** (ночной cron) — вшивает обложку из `cover.jpg` в каждый трек
  без встроенной картинки и синхро-лирику (LRCLIB) в теги, плюс кладёт `.lrc`
  рядом. Так обложки и текст видны и в нативном UI, и в любом клиенте.
- **fakeflac** (ночной cron) — детектит фейковый (перекодированный из mp3)
  FLAC, шлёт отчёт в Telegram. Ничего не удаляет — решение за тобой.

Метадата артистов (фото/био) в Navidrome требует ключей в `.env`:
`ND_LASTFM_APIKEY/SECRET` ([last.fm/api](https://www.last.fm/api/account/create))
и `ND_SPOTIFY_ID/SECRET` ([developer.spotify.com](https://developer.spotify.com/dashboard)).
Без них страницы артистов будут без фото.

**enrichment и fakeflac — локально собираемые образы** (`docker compose build`).
fakeflac тянет ML-модель [FLAD](https://github.com/Sg4Dylan/FLAD). Если не нужны —
закомментируй сервисы в compose.

### Maloja (углублённый анализ)

Maloja (`:42010`) пишется параллельно с Koito (multi-scrobbler fan-out) и даёт
более глубокую статистику/экспорт. Ключ: Maloja UI → Admin → API Keys →
создать → в `.env` `MLJ_API_KEY` → `docker compose up -d multi-scrobbler`.

## Качество и удаление «плохих» файлов

Профиль качества Lidarr настроен на lossless с cutoff на FLAC: берётся лучший
доступный релиз; если есть только MP3 — возьмётся MP3-320, а когда позже
появится FLAC — Lidarr сам апгрейдит. Защиты от **фейкового** FLAC в Lidarr нет
— этим занимается контейнер `fakeflac`.

**Как правильно удалить плохой релиз, чтобы Lidarr не скачал то же самое:**

1. Lidarr → артист → альбом → у файла **Delete** (удалит с диска).
2. ВАЖНО: Lidarr → **Activity → History** → найти этот релиз → **Blocklist**
   (или при удалении из очереди поставить галку *Blocklist Release*). Без
   блок-листа автопоиск возьмёт ровно тот же битый релиз снова.
3. Lidarr пере-ищет альбом и возьмёт следующий по качеству. Soularr дополнительно
   ведёт свой denylist (`failed_import_denylist = True`) для slskd-загрузок.

## Торренты: какие подключать

Подключаются через Prowlarr (раздел пост-настройки выше). С открытой
регистрацией и хорошим lossless:

- **RuTracker** — лучший источник lossless, нативный индексер в Prowlarr,
  открытая регистрация. Нюанс: сам блокирует РФ-IP → прокси должен быть
  **не-РФ и со стабильным (sticky) IP**, иначе логин-куки рвутся.
- **NoNaMe Club (NNM-Club)** — хороший вторичный, открытая регистрация.
- **Rutor** — без регистрации.
- RED / Orpheus — лучшие в мире, но только по инвайтам.

Задача владельца: зарегистрироваться на трекере, добавить его в Prowlarr
(Indexers → `+`), при необходимости повесить tag прокси, затем Settings → Apps
синхронизирует индексер в Lidarr.

## Если артиста нет в Lidarr

Lidarr берёт метадату из [MusicBrainz](https://musicbrainz.org). Если артист
не находится:

1. Проверь поиском на самом [musicbrainz.org](https://musicbrainz.org) или в
   [MusicBrainz Picard](https://picard.musicbrainz.org/) (десктоп-теггер с
   lookup), [Harmony](https://harmony.pulsewidth.org.uk/) (поиск релизов).
   Самохостимого полного MB-UI нет — база слишком большая.
2. Если артиста реально нет в MusicBrainz — добавь его там (регистрация
   бесплатна); правка появится в Lidarr после рефреша кэша (обычно часы-сутки).
3. Либо скачай вручную (slskd UI) и сделай **Manual Import** в Lidarr
   (Wanted → Manual Import → путь к файлам). Рут-фолдер загрузок добавлять
   НЕ надо — это плодит дубли.

## qBittorrent: вечный сид + лимиты отдачи

Чтобы раздавать обратно сообществу (важно!) и не насиловать домашний аплинк —
настройки в `config/qbittorrent/qBittorrent/qBittorrent.conf`. qBittorrent
переписывает conf при выходе, поэтому правь **при остановленном контейнере**:

```bash
docker compose stop qbittorrent
# отредактировать conf, секция [BitTorrent]:
#   Session\GlobalMaxRatio=-1                 ; сид без лимита по ratio
#   Session\GlobalMaxSeedingMinutes=-1        ; сид без лимита по времени
#   Session\MaxRatioAction=0                  ; 0=Pause (НИКОГДА не 3=delete!)
#   Session\GlobalDLSpeedLimit=0              ; скачивание безлимит
#   Session\GlobalUPSpeedLimit=1500           ; отдача KiB/s (~75% аплинка)
docker compose start qbittorrent
```

Импорт в Lidarr — hardlink, поэтому раздача **не рвётся** после импорта (файл
тот же inode). slskd раздаёт библиотеку автоматически (см. `SLSKD_SHARED_DIR`).

## Настройка для РФ

Часть внешних сервисов закрыта от РФ-IP (Cloudflare отдаёт 403):
`api.lidarr.audio` (метадата/поиск Lidarr) и `indexers.prowlarr.com`
(определения индексеров Prowlarr), плюс трекеры. Лечение — SOCKS5/HTTP-прокси
с **не-РФ** выходом:

- `.env` → `PROWLARR_PROXY` и `LIDARR_PROXY` (можно один и тот же,
  `socks5://user:pass@host:port`). Весь внешний трафик этих сервисов пойдёт
  через прокси, внутренние сервисы исключены (`NO_PROXY` в compose).
- Переменные **опциональны**: пусто = стек работает без прокси (актуально вне РФ).
- Для трекеров в Prowlarr — отдельный Indexer Proxy в его UI.

## Проверка, что всё связано

1. В Lidarr добавить артиста с парой альбомов → Search.
2. Смотреть: qBittorrent тянет с трекеров, Soularr (`docker logs -f soularr`)
   ищет недостающее в Soulseek.
3. После импорта файлы появляются в `/srv/media/music`, Navidrome подхватывает
   при сканировании (каждый час, либо вручную: Activity → Quick Scan).
4. Послушать трек до конца → он появляется в персональном Koito юзера
   (если тот включил скробблинг).

## Обслуживание

Версии образов зафиксированы в `docker-compose.yml`. Обновление — через
[Dependabot](https://docs.github.com/en/code-security/dependabot)
(конфиг `.github/dependabot.yml`): раз в неделю открывает PR с bump'ом
версий (minor/patch — сгруппированы, major — отдельно), ты ревьюишь и
мержишь. Включается само при пуше на GitHub. После мержа на сервере:

```bash
git pull && docker compose pull && docker compose up -d
docker compose logs -f <service>              # логи
```

Нюанс linuxserver-образов (lidarr, qbittorrent): они пересобираются на свежей
базе и под тем же тегом (CVE-фиксы базового слоя без смены версии приложения).
Dependabot такие ребилды не видит, поэтому раз в месяц стоит делать
`docker compose pull && docker compose up -d` даже без открытых PR.

### Кастомные образы (CI/CD)

Четыре образа собираются из этого репо: `enrichment`, `fakeflac`,
`lidarr-provision`, `prowlarr-provision`. GitHub Actions
([build-images.yml](.github/workflows/build-images.yml)) собирает их и пушит в
**GHCR** (`ghcr.io/gifi71/pwnd-music-*`) при пуше в `main`, по тегам `v*` и
вручную. На сервере они тянутся обычным `docker compose pull` — локальная
сборка не нужна. Если правишь Dockerfile/скрипты — `git push`, CI пересоберёт,
на сервере `docker compose pull && up -d`. Хочешь собрать локально —
`docker compose build`.

**Бэкапить:** `.env`, `config/` (базы и настройки сервисов), сам `${DATA_DIR}/music`.
Репозиторий хранит всю декларативную конфигурацию; восстановление сервера =
clone + `.env` из бэкапа + `config/` из бэкапа + `docker compose up -d`.

## Безопасность

Стек рассчитан на доступ из локальной сети. Наружу (интернет) ничего не
пробрасывать как есть — для удалённого доступа использовать VPN до дома
(WireGuard/Tailscale) или reverse-proxy с аутентификацией. Торренты при
необходимости можно завернуть в VPN, добавив контейнер
[Gluetun](https://github.com/qdm12/gluetun) и `network_mode: service:gluetun`
у qBittorrent.

**Telegram-уведомления** (отчёты fakeflac/enrichment) — опциональны. Бот:
[@BotFather](https://t.me/BotFather) → `/newbot` → токен в `TELEGRAM_BOT_TOKEN`.
`chat_id`: написать боту, открыть
`https://api.telegram.org/bot<TOKEN>/getUpdates` → взять `chat.id` в
`TELEGRAM_CHAT_ID`. Пусто = уведомления выключены.

## Правовая оговорка

Этот проект — набор свободного программного обеспечения с открытым исходным
кодом (Navidrome, Lidarr и др.) для развёртывания личного домашнего
медиа-сервера. Программное обеспечение является нейтральным инструментом: оно
не содержит и не распространяет какой-либо защищённый авторским правом контент.

Проект предназначен исключительно для личного и домашнего использования с
контентом, на использование которого у вас есть законное право (собственные
записи, легально приобретённые фонограммы, произведения под свободными
лицензиями или в общественном достоянии).

Согласно ст. 1273 ГК РФ, гражданин вправе без согласия правообладателя и без
выплаты вознаграждения воспроизводить правомерно обнародованное произведение
исключительно в личных целях. Эта норма не распространяется на распространение
(раздачу, доведение до всеобщего сведения) произведений — такие действия могут
влечь гражданскую, административную или, при крупном размере (свыше 100 000 ₽),
уголовную ответственность по ст. 146 УК РФ.

Ответственность за законность любого контента, который вы загружаете, храните,
воспроизводите или раздаёте с помощью этого ПО, а также за соблюдение
законодательства вашей юрисдикции, несёте исключительно вы. Авторы и участники
проекта не несут ответственности за то, как вы используете эти инструменты.

Данный текст не является юридической консультацией. Программное обеспечение
предоставляется «как есть», без каких-либо гарантий.
