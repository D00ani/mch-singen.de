# -*- coding: utf-8 -*-
"""
Asset-Build fuer mch-singen.de (kein Framework, kein Node noetig).
Erzeugt:
  css/bundle.min.css   – alle per @import geladenen Stylesheets + style.css
                         als EINE minifizierte Datei (eliminiert die
                         render-blockierende @import-Kette: vorher 10 Requests)
  css/<seite>.min.css  – minifizierte Seiten-Stylesheets
  js/<datei>.min.js    – minifizierte Skripte (Quellen bleiben unveraendert)

Nach JEDER Aenderung an css/*.css oder js/*.js neu ausfuehren:
    python tools/build_assets.py
Benoetigt: pip install csscompressor rjsmin
"""
import os
import re
import csscompressor
import rjsmin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return f.read()

def write(p, content):
    with open(os.path.join(ROOT, p), "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"{p}: {os.path.getsize(os.path.join(ROOT, p)) // 1024} KB")

# --- 1. CSS-Bundle: exakt in @import-Reihenfolge von style.css ---
IMPORT_ORDER = ["fonts.css", "header.css", "sidebar.css", "main.css",
                "footer.css", "modules.css", "dark.css", "mobile.css",
                "cookie.css"]

parts = [read(f"css/{name}") for name in IMPORT_ORDER]
# style.css selbst, ohne die @import-Zeilen (die sind jetzt inline enthalten)
style = re.sub(r"@import\s+url\([^)]*\)\s*;", "", read("css/style.css"))
parts.append(style)
write("css/bundle.min.css", csscompressor.compress("\n".join(parts)))

# --- 2. Seiten-CSS minifizieren ---
for name in ["index", "kartsport", "live"]:
    write(f"css/{name}.min.css", csscompressor.compress(read(f"css/{name}.css")))

# --- 3. JS minifizieren (Vendor-Dateien sind bereits minifiziert) ---
for name in ["main", "index", "aktuelles", "faq", "kontakt", "live",
             "statistiken", "suche", "klaro-config"]:
    write(f"js/{name}.min.js", rjsmin.jsmin(read(f"js/{name}.js")))

print("Fertig.")
