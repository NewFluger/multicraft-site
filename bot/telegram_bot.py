#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_PATH = ROOT / "state.json"
API = "https://api.telegram.org/bot{token}/{method}"
USER_AGENT = "MultiCraftBot/1.0"

HELP = (
    "<b>MultiCraft Bot</b>\n\n"
    "Админ-команды:\n"
    "/news текст — новость в канал\n"
    "/release 1.28.4 | список изменений — релиз\n"
    "/pack — ссылка на визуальную сборку\n"
    "/link — все ссылки\n"
    "/id — ваш Telegram ID\n\n"
    "Автопост: python bot.py --watch"
)


def log(message: str) -> None:
    print(time.strftime("%H:%M:%S"), message, flush=True)


def load_config() -> dict:
    config: dict = {}
    if CONFIG_PATH.is_file():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    token = os.environ.get("MULTICRAFT_BOT_TOKEN") or config.get("token") or ""
    if not token or token.startswith("PASTE"):
        log("Вставьте токен бота в config.json или MULTICRAFT_BOT_TOKEN.")
        sys.exit(1)
    config["token"] = token
    config["channel"] = (
        os.environ.get("MULTICRAFT_CHANNEL") or config.get("channel") or "@tgkcoqoza"
    )
    admins = list(config.get("admins") or [])
    for item in str(os.environ.get("MULTICRAFT_ADMINS") or "").split(","):
        item = item.strip()
        if item:
            try:
                admins.append(int(item))
            except ValueError:
                pass
    config["admins"] = sorted({int(item) for item in admins})
    config.setdefault("site", "https://newfluger.github.io/multicraft-site/")
    config.setdefault("download", config["site"] + "files/MultiCraft-Setup-1.28.8.exe")
    config.setdefault("pack", config["site"] + "files/MultiCraftVisuals-1.0.0.mrpack")
    config.setdefault("watch_minutes", 10)
    return config


def api(config: dict, method: str, data: dict | None = None, timeout: int = 45) -> dict:
    url = API.format(token=config["token"], method=method)
    body = urllib.parse.urlencode(data or {}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def send(config: dict, chat_id, text: str) -> None:
    api(
        config,
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        },
    )


def links(config: dict) -> str:
    return (
        f'Сайт: {config["site"]}\n'
        f'Скачать: {config["download"]}\n'
        f'Сборка: {config["pack"]}'
    )


def is_admin(config: dict, user_id: int) -> bool:
    return user_id in config["admins"]


def handle(config: dict, message: dict) -> None:
    text = (message.get("text") or "").strip()
    if not text.startswith("/"):
        return
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    parts = text.split(maxsplit=1)
    command = parts[0].split("@")[0].lower()
    argument = parts[1].strip() if len(parts) > 1 else ""

    if command in ("/start", "/help"):
        send(config, chat_id, HELP)
        return
    if command == "/id":
        send(config, chat_id, f"Ваш ID: <code>{user_id}</code>\nЧат: <code>{chat_id}</code>")
        return
    if command == "/link":
        send(config, chat_id, "Ссылки MultiCraft:\n" + links(config))
        return
    if not is_admin(config, user_id):
        send(config, chat_id, "Эта команда доступна только администратору.")
        return

    if command == "/news":
        if not argument:
            send(config, chat_id, "Формат: /news текст новости")
            return
        send(
            config,
            config["channel"],
            f"<b>Новости MultiCraft</b>\n\n{argument}\n\n{links(config)}",
        )
        send(config, chat_id, "Новость опубликована.")
    elif command == "/release":
        if not argument:
            send(config, chat_id, "Формат: /release 1.28.4 | что изменилось")
            return
        version, _, changes = argument.partition("|")
        version = version.strip()
        changes = changes.strip()
        text = "\n".join(
            [
                f"<b>MultiCraft {version}</b>",
                "",
                changes or "Новая версия уже на сайте.",
                "",
                links(config),
            ]
        )
        send(config, config["channel"], text)
        send(config, chat_id, f"Релиз {version} опубликован.")
    elif command == "/pack":
        send(
            config,
            config["channel"],
            "<b>MultiCraft Visuals 1.0.0</b>\n"
            "Визуальная сборка для 1.21.4 (Fabric).\n\n"
            f'{config["pack"]}',
        )
        send(config, chat_id, "Сборка опубликована.")
    else:
        send(config, chat_id, "Неизвестная команда. /help")


def latest_version(url: str) -> str | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=25) as response:
        html = response.read().decode("utf-8", "replace")
    match = re.search(r'class="v">([0-9][0-9.]*)<', html)
    return match.group(1) if match else None


def watch(config: dict) -> None:
    state: dict = {}
    if STATE_PATH.is_file():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except ValueError:
            state = {}
    last = str(state.get("version") or "")
    while True:
        try:
            current = latest_version(config["site"])
            if current and current != last:
                if last:
                    send(
                        config,
                        config["channel"],
                        f"<b>Вышло обновление MultiCraft {current}</b>\n\n{links(config)}",
                    )
                    log(f"Автопост: {current}")
                last = current
                STATE_PATH.write_text(json.dumps({"version": last}), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            log(f"watch: {exc}")
        time.sleep(max(1, int(config["watch_minutes"])) * 60)


def poll(config: dict, max_seconds: int | None = None) -> None:
    offset = 0
    try:
        data = api(
            config,
            "getUpdates",
            {"offset": -1, "limit": 1, "timeout": 0},
            timeout=15,
        )
        updates = data.get("result") or []
        if updates:
            offset = int(updates[-1]["update_id"]) + 1
    except Exception as exc:  # noqa: BLE001
        log(f"skip backlog: {exc}")
    deadline = time.time() + max_seconds if max_seconds else None
    log("Бот запущен. Ожидаю команды.")
    while deadline is None or time.time() < deadline:
        try:
            timeout = 30 if deadline is None else max(1, min(30, int(deadline - time.time())))
            data = api(
                config,
                "getUpdates",
                {"offset": offset, "timeout": timeout, "allowed_updates": '["message"]'},
                timeout=timeout + 15,
            )
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if message:
                    handle(config, message)
        except urllib.error.HTTPError as exc:
            log(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}")
            time.sleep(5)
        except Exception as exc:  # noqa: BLE001
            log(f"poll: {exc}")
            time.sleep(5)
    log("Сессия завершена")


def main() -> None:
    config = load_config()
    args = sys.argv[1:]
    max_seconds = None
    if "--max-seconds" in args:
        index = args.index("--max-seconds")
        try:
            max_seconds = int(args[index + 1])
        except (IndexError, ValueError):
            max_seconds = None
    log(f"Канал: {config['channel']}; админов: {len(config['admins'])}")
    if "--watch" in args:
        threading.Thread(target=watch, args=(config,), daemon=True).start()
    poll(config, max_seconds=max_seconds)


if __name__ == "__main__":
    main()
