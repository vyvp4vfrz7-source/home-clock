# Home Clock

A full-screen clock, London weather, family photos, Hong Kong + UK headlines and a Cantonese spoken summary for a wall-mounted iPad.

- Weather: [Open-Meteo](https://open-meteo.com), free, no key.
- Headlines: `.github/workflows/news.yml` runs `tools/build_news.py` every 30 minutes and writes `news.json` (RTHK 中文 local news + BBC 中文).
- Photos: list them in `photos.json` as `[{"src":"photos/beach.jpg","text":"Brighton day out","when":"Oct 2026"}]` and put the files in `photos/`.
- Settings (city, Home buttons, dim hours) are in the `CONFIG` block at the top of `index.html`.
