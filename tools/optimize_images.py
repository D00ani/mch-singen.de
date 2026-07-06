# -*- coding: utf-8 -*-
"""
Bild-Optimierung fuer mch-singen.de (PageSpeed).
Erzeugt WebP-Varianten neben den Originalen (Originale bleiben als Fallback
erhalten) und verkleinerte Logo-Versionen. Nach dem Hinzufuegen neuer Bilder
einfach erneut ausfuehren:  python tools/optimize_images.py
Benoetigt: pip install Pillow
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = 82  # WebP-Qualitaet: visuell verlustfrei bei Fotos

def webp(src, widths=None, quality=Q):
    """Erzeugt <name>-<w>.webp Varianten (oder <name>.webp bei widths=None)."""
    path = os.path.join(ROOT, src)
    im = Image.open(path)
    base, _ = os.path.splitext(path)
    made = []
    for w in (widths or [None]):
        out = f"{base}-{w}.webp" if w else f"{base}.webp"
        img = im
        if w and w < im.width:
            img = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        elif w and w >= im.width:
            out = f"{base}-{im.width}.webp" if f"{base}-{w}.webp" != out else out
            img = im
        img.save(out, "WEBP", quality=quality, method=6)
        made.append((os.path.relpath(out, ROOT), os.path.getsize(out) // 1024, img.size))
    return made

def small_png(src, out_name, size):
    """Verkleinerte, quantisierte PNG-Kopie (fuer Logos)."""
    path = os.path.join(ROOT, src)
    im = Image.open(path).convert("RGBA")
    im = im.resize((size, size), Image.LANCZOS)
    im = im.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
    out = os.path.join(ROOT, os.path.dirname(src), out_name)
    im.save(out, "PNG", optimize=True)
    return out_name, os.path.getsize(out) // 1024

def compress_png_inplace(src, colors=256):
    """PNG in-place quantisieren (Ersparnis ohne sichtbaren Unterschied)."""
    path = os.path.join(ROOT, src)
    before = os.path.getsize(path)
    im = Image.open(path).convert("RGBA")
    q = im.quantize(colors=colors, method=Image.Quantize.FASTOCTREE)
    q.save(path, "PNG", optimize=True)
    return before // 1024, os.path.getsize(path) // 1024

results = []

# --- Hero-Slider (Startseite): responsive Varianten ---
results += webp("media/bilder/mch_pic.jpg", [480, 640])
results += webp("media/bilder/kartsport/kart_abteilung.jpg", [480, 800, 1600])

# trial_abteilung: Hochformat-Foto, im 16:9-Hero-Slider per object-fit:cover
# ohnehin auf 16:9 beschnitten -> WebP direkt als 16:9-Center-Crop erzeugen
# (rendert pixelidentisch, spart aber >50% Dateigroesse beim koernigen Foto)
_ta = Image.open(os.path.join(ROOT, "media/bilder/trial/trial_abteilung.jpg"))
_ch = round(_ta.width * 9 / 16)
_top = (_ta.height - _ch) // 2
_crop = _ta.crop((0, _top, _ta.width, _top + _ch))
for _w in [480, 800, 1179]:
    _img = _crop if _w >= _crop.width else _crop.resize((_w, round(_ch * _w / _ta.width)), Image.LANCZOS)
    _out = os.path.join(ROOT, f"media/bilder/trial/trial_abteilung-{_w}.webp")
    _img.save(_out, "WEBP", quality=80, method=6)
    results.append((os.path.relpath(_out, ROOT), os.path.getsize(_out) // 1024, _img.size))

# --- Content-Bilder ---
# trial1/trial2: 800px reichen fuer die 250px-Karten (Lightbox nutzt das JPEG-Original)
for _n in ["trial1", "trial2"]:
    _im = Image.open(os.path.join(ROOT, f"media/bilder/trial/{_n}.jpg"))
    _img = _im.resize((800, round(_im.height * 800 / _im.width)), Image.LANCZOS)
    _out = os.path.join(ROOT, f"media/bilder/trial/{_n}.webp")
    _img.save(_out, "WEBP", quality=78, method=6)
    results.append((os.path.relpath(_out, ROOT), os.path.getsize(_out) // 1024, _img.size))
results += webp("media/bilder/geschichte/dtm_singen.jpg", [650, 1300])
results += webp("media/bilder/geschichte/formel3.jpg")
results += webp("media/bilder/ueber-uns/platzhalter.jpg")
results += webp("media/bilder/kartsport/mach1-kart.png")

# --- Sponsoren (Anzeige max. 200px, @2x = 400px) ---
for s in ["alicke.jpg", "herby.jpg", "mofashion.jpg", "randegger.jpg",
          "schlegel.jpg", "sparkasse.jpg", "daeschle.png"]:
    p = os.path.join("media/sponsoren", s)
    im = Image.open(os.path.join(ROOT, p))
    results += webp(p, [400] if im.width > 400 else None)

# --- Team-Fotos (ueber-uns): Handy-Originale (<name>.webp, ~1.5 MB) ->
#     700px-Karten-Variante + JPEG-Fallback fuer <picture> ---
# Personen-Zuschnitt (x0, y0, x1, y1 als Anteil der Bildmasse), damit alle
# Gesichter gleich gross und gleich hoch sitzen wie bei Max (Referenzbild).
# max: Referenz unveraendert; daniel: naeher fotografiert, kein Spielraum.
TEAM_CROPS = {
    "jochen":   (0.0914, 0.0911, 0.8371, 0.8360),
    "alex":     (0.0743, 0.0986, 0.9771, 1.0),
    "andi":     (0.1000, 0.1008, 0.8871, 0.8885),
    "thorsten": (0.1786, 0.1726, 0.8600, 0.8542),
}
from PIL import ImageOps
for n in ["jochen", "alex", "andi", "thorsten", "max", "daniel"]:
    src = os.path.join(ROOT, f"media/bilder/ueber-uns/{n}.webp")
    if not os.path.exists(src):
        continue
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    if n in TEAM_CROPS:
        x0, y0, x1, y1 = TEAM_CROPS[n]
        im = im.crop((round(x0 * im.width), round(y0 * im.height),
                      round(x1 * im.width), round(y1 * im.height)))
    small = im.resize((700, 933), Image.LANCZOS)
    for ext, fmt, q in [("webp", "WEBP", 80), ("jpg", "JPEG", 85)]:
        out = os.path.join(ROOT, f"media/bilder/ueber-uns/{n}-700.{ext}")
        small.save(out, fmt, quality=q, **({"method": 6} if fmt == "WEBP" else {"optimize": True}))
        results.append((os.path.relpath(out, ROOT), os.path.getsize(out) // 1024, small.size))

# --- Logos ---
print("Logo 128px:", small_png("media/logos/favicon.png", "mch-logo-128.png", 128))
# In-place-Quantisierung nur, wenn die Datei noch unkomprimiert ist (>100 KB),
# damit wiederholte Laeufe das Logo nicht mehrfach quantisieren
if os.path.getsize(os.path.join(ROOT, "media/logos/favicon.png")) > 100_000:
    print("favicon.png in-place:", compress_png_inplace("media/logos/favicon.png"), "KB (vorher/nachher)")

for name, kb, size in results:
    print(f"{name}: {kb} KB {size[0]}x{size[1]}")
