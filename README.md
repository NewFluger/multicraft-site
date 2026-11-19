# MultiCraft — сайт лаунчера

Статическая страница скачивания лаунчера MultiCraft для Windows.

- Сайт: `index.html` — самодостаточный файл, картинки встроены.
- Установщик: `files/MultiCraft-Setup-1.27.0.exe` (54,3 МБ).
- SHA-256 установщика: `A39118F38F2D61158513B9CF401F6C4F2406DC739C0B575B01BC7F1EFBF96260`.
- GitHub Pages: https://newfluger.github.io/multicraft-site/

## Локальный просмотр

Откройте `index.html` в браузере или запустите в этой папке:

```powershell
python -m http.server 8000
```

и откройте http://127.0.0.1:8000.

## Исходник и сборка

Исходник — `source.html` (ссылается на `assets/`). Сборка в самодостаточный `index.html`:

```powershell
multitool-node --skill websites site.cjs bundle source.html index.html
```

Проверка:

```powershell
multitool-node --skill websites site.cjs check index.html
```

## Обновление версии

1. Замените установщик в `files/`.
2. Обновите ссылки, версию, размер и SHA-256 в `index.html`.
3. Закоммитьте и запушьте: `git add -A; git commit -m "Update installer"; git push`.
