#!/usr/bin/env python3
from __future__ import annotations

import html as html_lib
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
PACK = SITE + "files/MultiCraftVisuals-1.0.0.mrpack"


def fetch(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def send(text: str) -> dict:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": CHANNEL,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def clean(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def changelog_items(html: str, version: str) -> list[str]:
    block = re.search(
        r'class="v">' + re.escape(version) + r"<.*?</article>", html, re.S
    )
    if not block:
        return []
    items = [clean(item) for item in re.findall(r"<li>(.*?)</li>", block.group(0), re.S)]
    return [item for item in items if item][:6]


def size_label(url: str) -> str:
    try:
        request = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            length = int(response.headers.get("Content-Length") or 0)
        if length:
            return f"{length / 1048576:.1f}".replace(".", ",") + " МБ"
    except Exception:  # noqa: BLE001
        pass
    return ""


def build_message(version: str, exe: str, items: list[str], exe_size: str) -> str:
    bullets = "\n".join(f"• {html_lib.escape(item)}" for item in items)
    if not bullets:
        bullets = "• Улучшения и исправления уже на сайте"
    size = f" · {exe_size}" if exe_size else ""
    return (
        f"🚀 <b>MultiCraft {version}</b> — новое обновление\n\n"
        f"🆕 <b>Что нового</b>\n{bullets}\n\n"
        f"📦 <b>Визуальная сборка</b>\n"
        f"MultiCraft Visuals 1.0.0 · 1.21.4 · Fabric · HUD 1.7.2\n\n"
        f"⬇️ <b>Скачать</b>\n"
        f'• <a href="{exe}">Установщик MultiCraft</a>{size}\n'
        f'• <a href="{PACK}">MultiCraft Visuals</a>\n\n'
        f'🌐 <a href="{SITE}">Сайт</a> · '
        f'💬 <a href="https://t.me/tgkcoqoza">Поддержка</a>\n\n'
        f"#MultiCraft #Minecraft"
    )


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
            state = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
        except ValueError:
            state = {}
    last = str(state.get("version") or "")
    print(f"site={version} last={last or '-'} exe={exe}")
    if version == last:
        print("Изменений нет")
        return 0
    items = changelog_items(html, version)
    text = build_message(version, exe, items, size_label(exe))
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
