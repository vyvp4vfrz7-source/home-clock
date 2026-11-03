# Home Clock

A full-screen clock, London weather, family photos, Hong Kong + UK headlines and a Cantonese spoken summary for a wall-mounted iPad.

- Weather: [Open-Meteo](https://open-meteo.com), free, no key.
- Headlines: `.github/workflows/news.yml` runs `tools/build_news.py` every 30 minutes and writes `news.json` (RTHK 中文 local news + BBC 中文).
- Photos: list them in `photos.json` as `[{"src":"photos/beach.jpg","text":"Brighton day out","when":"Oct 2026"}]` and put the files in `photos/`.
- Settings (city, Home buttons, dim hours) are in the `CONFIG` block at the top of `index.html`.

## Parents' screen (`/parents/`)

A photo frame for Mum and Dad: full-screen photos with a big Cantonese clock, their city's weather, and a large FaceTime button.

- Open `/parents/?frame&ft=<Billy's phone number or Apple ID>` on their iPad, then Add to Home Screen.
- City defaults to Hong Kong; change with `&lat=..&lon=..&name=..&tz=..`.
- Photos: uses the family album synced into `/photos.json` by default. To show different photos, list them in `parents/photos.json` and put the files in `parents/photos/`.
