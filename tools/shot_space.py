# test runs only: screenshot the space page so it can be checked before merging
import sys, time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1366, "height": 1024}, device_scale_factor=2, timezone_id="Europe/London")
    pg.on("console", lambda m: print("console:", m.text))
    pg.goto("http://localhost:8000/index.html?page=6&night=0")
    time.sleep(12)
    pg.screenshot(path="preview/space-1.png")
    pg.click("#spMars"); time.sleep(6)
    pg.screenshot(path="preview/space-2.png")
    pg.click("#spApod"); time.sleep(4)
    pg.screenshot(path="preview/space-apod.png")
    b.close()
