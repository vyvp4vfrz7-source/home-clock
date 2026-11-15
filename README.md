# Home Clock

A full-screen clock, Northwood (London) weather, indoor temperature from Apple Home, family photos, Hong Kong + UK headlines and a Cantonese spoken summary for a wall-mounted iPad.

- Weather: [Open-Meteo](https://open-meteo.com), free, no key. If the device cannot reach it, the page uses `weather.json`, saved every 15 minutes by `.github/workflows/weather.yml`.
- Headlines: `.github/workflows/news.yml` runs `tools/build_news.py` every 30 minutes and writes `news.json` (RTHK 中文 local news + BBC 中文).
- Photos: list them in `photos.json` as `[{"src":"photos/beach.jpg","text":"Brighton day out","when":"Oct 2026"}]` and put the files in `photos/`.
- Settings (city, Home buttons, dim hours) are in the `CONFIG` block at the top of `index.html`.
- Indoor temperature: an Apple Shortcut ("Send home temp") reads the temperature from Apple Home and calls the GitHub API (`repository_dispatch`, event `home-temp`). `.github/workflows/home-temp.yml` saves it to `home.json`, which the page reads every 5 minutes. The reading greys out after 3 hours and hides after 12.
