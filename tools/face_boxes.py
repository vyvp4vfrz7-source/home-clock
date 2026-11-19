"""Find faces in the family photos so the full-photo clock never cuts people off.

Uses OpenCV's small YuNet face detector (tools/models, MIT licence). Results are cached in
faces.json by file name, so each photo is checked once. Each entry is a list of face boxes
[x0, y0, x1, y1] as fractions of the (EXIF-rotated) picture. Safe to skip: if OpenCV is not
installed, the page just shows whole photos."""
import json, os

CACHE = "faces.json"
MODEL = os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet_2023mar.onnx")

def load():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def detect(path):
    import cv2
    img = cv2.imread(path)   # applies the EXIF rotation, like Safari does
    if img is None:
        return None
    h, w = img.shape[:2]
    k = min(1.0, 1280 / max(w, h))
    small = cv2.resize(img, (int(w * k), int(h * k))) if k < 1 else img
    sh, sw = small.shape[:2]
    det = cv2.FaceDetectorYN.create(MODEL, "", (sw, sh), 0.75, 0.3, 50)
    _, faces = det.detect(small)
    out = []
    for f in (faces if faces is not None else []):
        x, y, fw, fh = [float(v) for v in f[:4]]
        if fw * fh < 0.00015 * sw * sh:   # far-away specks in the background
            continue
        out.append([round(max(0, x / sw), 3), round(max(0, y / sh), 3),
                    round(min(1, (x + fw) / sw), 3), round(min(1, (y + fh) / sh), 3)])
    return out

def update(files):
    """files: photo paths now in the album. Returns {name: [boxes]} and saves the cache."""
    cache, out = load(), {}
    for p in files:
        name = os.path.basename(p)
        if name not in cache and os.path.exists(p):
            try:
                found = detect(p)
            except Exception as e:   # no OpenCV, bad file...
                print("faces skipped:", name, e)
                continue
            if found is None:
                continue
            cache[name] = found
            print("faces:", name, len(found))
        if name in cache:
            out[name] = cache[name]
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=0, sort_keys=True)
    return out

if __name__ == "__main__":   # re-check every photo in photos.json
    with open("photos.json", encoding="utf-8") as f:
        items = json.load(f)
    res = update([i["src"] for i in items if i.get("src")])
    print(len(res), "photos,", sum(1 for v in res.values() if v), "with faces")
