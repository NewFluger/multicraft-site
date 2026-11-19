#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SITE = os.environ.get("MULTICRAFT_SITE", "https://newfluger.github.io/multicraft-site/").rstrip("/") + "/"
CHANNEL = os.environ.get("MULTICRAFT_CHANNEL", "@tgkcoqoza")
TOKEN = os.environ.get("MULTICRAFT_BOT_TOKEN", "")
STATE_PATH = Path(os.environ.get("MULTICRAFT_STATE", "bot/state.json"))
USER_AGENT = "MultiCraftBot/1.0"


def fetch(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def send(text: str) -> dict:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": CHANNEL, "text": text, "parse_mode": "HTML"}
    ).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    dry = "--dry-run" in sys.argv[1:]
    if not TOKEN and not dry:
        print("MULTICRAFT_BOT_TOKEN не задан")
        return 1
    html = fetch(SITE)
    version_match = re.search(r'class="v">([0-9][0-9.]*)<', html)
    exe_match = re.search(r"files/(MultiCraft-Setup-[0-9.]+\.exe)", html)
    if not version_match:
        print("Версия на сайте не найдена")
        return 1
    version = version_match.group(1)
    exe = (
        f"{SITE}files/{exe_match.group(1)}"
        if exe_match
        else f"{SITE}files/MultiCraft-Setup-{version}.exe"
    )
    state: dict = {}
    if STATE_PATH.is_file():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except ValueError:
            state = {}
    last = str(state.get("version") or "")
    print(f"site={version} last={last or '-'} exe={exe}")
    if version == last:
        print("Изменений нет")
        return 0
    text = (
        f"<b>Вышло обновление MultiCraft {version}</b>\n\n"
        f"Сайт: {SITE}\n"
        f"Скачать: {exe}\n"
        f"Сборка: {SITE}files/MultiCraftVisuals-1.0.0.mrpack"
    )
    if dry:
        print("dry-run, было бы отправлено:\n" + text)
    else:
        send(text)
        print("Опубликовано")
    state["version"] = version
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Состояние обновлено")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
