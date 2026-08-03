# Установка

## 1. Подставить свои данные

Всё содержимое баннеров лежит в `profile.json`. Минимум, что нужно поменять:

```jsonc
"identity": {
  "wordmark": "EGOISTONLY",     // крупная надпись в баннере
  "handle": "egoistonly",       // GitHub username, он же источник статистики
  "roles": [...],               // строки, которые печатаются по очереди
  "statement": "..."            // одна строка под ролями
},
"links": [...],                 // подписи, иконки и адреса кнопок
"stats": {
  "metrics": ["repos", "years", "industries"],  // до трёх: repos, stars, followers,
                                                // following, years, forks, industries
  "industries": ["retail", "finance", ...]      // отрасли под цифрами
}
```

Кнопки — единственный блок с внешними адресами: поменяйте `url` в `links`, пересоберите,
и `href` в `README.md` между `<!-- links:start -->` и `<!-- links:end -->` обновятся сами.
Сейчас там `CHANGEME` — их нужно заменить на реальные.

Нижняя половина панели — один слот. Если `stats.industries` не пуст, там сетка отраслей;
уберите список — вернётся полоса «top languages» по публичным репозиториям (её можно
выключить совсем через `"languages": false`). Отрасли заданы вручную намеренно: закрытая
работа в GitHub API не видна, а `"industries"` в `metrics` считает их автоматически.
Ряды выравниваются по ширине сами, порядок в списке сохраняется.

## 2. Пересобрать ассеты

```bash
python3 -m venv .venv
.venv/bin/pip install fonttools brotli
.venv/bin/python tools/build.py
```

Можно собрать что-то одно: `tools/build.py hero`, `stack`, `capabilities`, `stats`, `buttons`.

Скрипту нужен интернет: он тянет шрифты с Google Fonts (сразу сабсетом под нужные символы)
и брендовые иконки из Simple Icons, затем вшивает их внутрь SVG. Скачанное кэшируется
в `tools/.cache/`.

## 3. Посмотреть локально

```bash
python3 -m http.server 8777
# открыть http://127.0.0.1:8777/preview/index.html
```

Страница показывает все ассеты на тёмном фоне GitHub и баннер на светлом.

## 4. Выложить

Профильный README живёт в репозитории, чьё имя совпадает с вашим username.

```bash
git init && git add . && git commit -m "profile"
git remote add origin git@github.com:<username>/<username>.git
git push -u origin main
```

Пути к картинкам относительные, GitHub сам подставит `raw.githubusercontent.com`.
Обновлённый SVG появляется на странице примерно через 5 минут (`cache-control: max-age=300`).

## 5. Автообновление статистики

`.github/workflows/refresh-stats.yml` раз в сутки перерисовывает `assets/stats.svg`
по данным GitHub API и коммитит его. Ничего настраивать не нужно, встроенного
`GITHUB_TOKEN` хватает. Запустить вручную: вкладка Actions, workflow «refresh stats».

# Что можно поменять в дизайне

| Что | Где |
|---|---|
| Палитра, толщина линий, размер фаски | `tools/kit.py`, словарь `T` и `CHAMFER` |
| Шрифты | `profile.json`, блок `fonts` (любая семья с Google Fonts) |
| Кириллица в баннере | см. ниже |
| Тайминги печати, глитча, сетки | `tools/build.py`, функция `build_hero` |
| Состав иконок | `profile.json`, блок `stack`, слаги из Simple Icons |

# Если надпись в баннере на кириллице

Дефолтный дисплейный шрифт Archivo кириллицу не содержит, сборка это проверяет и падает
с понятной ошибкой. Замените `fonts.display` в `profile.json` на любой из проверенных:

```json
{ "query": "Unbounded:wght@800",  "family": "Unbounded",  "weight": 800 }
{ "query": "Tektur:wght@700",     "family": "Tektur",     "weight": 700 }
{ "query": "Golos+Text:wght@800", "family": "Golos Text", "weight": 800 }
```

Моноширинный JetBrains Mono кириллицу поддерживает, его менять не нужно.

# Технические ограничения, на которые это рассчитано

GitHub отдаёт README-картинки с `default-src 'none'`, а SVG внутри `<img>` работает
в secure animated mode. Из этого следует:

- CSS `@keyframes` и SMIL работают, JavaScript внутри SVG не работает;
- внешние шрифты и внешние `<image href>` блокируются, поэтому шрифты вшиты как
  base64 `data:` URI, а иконки вставлены как пути;
- инлайновый `<svg>` прямо в markdown вырезается санитайзером, картинки только через `<img src>`;
- фильтры, маски, `clipPath` и `mix-blend-mode` работают.

Вся анимация выключается через `prefers-reduced-motion`, при этом контент остаётся
видимым: у элементов задано нормальное состояние покоя, а не `opacity: 0`.
