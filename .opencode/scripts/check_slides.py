import json

with open("out9/slides.json", encoding="utf-8") as f:
    data = json.load(f)

for s in data["slides"]:
    img = s.get("image", "")
    path = f"out9/{img}" if img else ""
    exists = "EXISTS" if img and __import__("os").path.exists(path) else "MISSING" if img else "NO IMAGE"
    print(f"  #{s['index']}: {img[:40] if img else 'None'} [{exists}] start={s['start']:.1f}s")
