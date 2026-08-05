# -*- coding: utf-8 -*-
"""
Erzeugt pages/status.html - die Lagemeldung als kleine Seite fuers Handy.

Damit sieht man unterwegs, was ansteht, ohne Rechner. Die Seite wird beim
Veroeffentlichen automatisch neu geschrieben.

Sie ist bewusst NICHT verlinkt, steht auf "noindex" und ist in robots.txt
ausgeschlossen - sie gehoert nicht in Suchmaschinen. Geheim ist sie damit
nicht; es steht aber auch nichts drauf, was nicht ohnehin oeffentlich waere
(fehlende PDFs, anstehende Arbeiten).

Ausfuehren: python tools/statusseite.py
"""
import html as html_modul
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h
import uebersicht

ROOT = h.ROOT
STATUS_HTML = os.path.join(ROOT, "pages", "status.html")

FARBEN = {uebersicht.FAELLIG: "#c62828", uebersicht.HINWEIS: "#b26a00",
          uebersicht.INFO: "#5c6684", uebersicht.LAGE: "#0047cc"}

KOPF = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Status - MCH Singen</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; padding: 16px; background: #eef1f7; color: #131c33;
         font-family: "Segoe UI", system-ui, sans-serif; line-height: 1.5; }}
  h1 {{ font-size: 1.25rem; margin: 0 0 4px; }}
  .stand {{ font-size: .8rem; color: #5c6684; margin-bottom: 18px; }}
  .rennen {{ background: #001b5e; color: #fff; border-radius: 8px;
            padding: 14px 16px; margin-bottom: 18px; }}
  .rennen div + div {{ margin-top: 10px; }}
  .tage {{ font-size: 1.6rem; font-weight: 700; color: #ffcc00; }}
  .klein {{ font-size: .8rem; color: #b9c6e8; }}
  .karte {{ background: #fff; border: 1px solid #d5dce9; border-left: 4px solid #5c6684;
           border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }}
  .karte b {{ display: block; font-size: .95rem; }}
  .karte span {{ font-size: .8rem; color: #5c6684; }}
  .gut {{ text-align: center; color: #1e8e3e; font-weight: 600; padding: 20px; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #0b1020; color: #e4eaf9; }}
    .karte {{ background: #151d33; border-color: #2a3554; }}
    .karte span, .stand {{ color: #94a1c4; }}
  }}
</style>
</head>
<body>
<h1>Was steht an?</h1>
<div class="stand">Stand: {stand}</div>
"""

FUSS = """</body>
</html>
"""


def baue_seite(heute=None):
    # pruefe_veroeffentlichung zaehlt noch nicht veroeffentlichte Arbeit im
    # Arbeitsordner. Auf einer veroeffentlichten Seite ist das sinnlos - und
    # die Zahl aendert sich staendig, wodurch die Seite bei jedem Lauf neu
    # geschrieben wuerde.
    hinweise = uebersicht.sammle(heute, ausser={"pruefe_veroeffentlichung"})
    teile = [KOPF.format(stand=datetime.now().strftime("%d.%m.%Y, %H:%M Uhr"))]

    rennen = [e for e in hinweise if e[0] == uebersicht.LAGE]
    if rennen:
        teile.append('<div class="rennen">')
        for eintrag in uebersicht.naechste_rennen(heute):
            if eintrag["tage"] is None:
                continue
            teile.append(
                f'<div><div class="klein">Nächstes {eintrag["sportart"]}-Rennen</div>'
                f'<span class="tage">{eintrag["tage"]}</span> Tage<br>'
                f'<span class="klein">{html_modul.escape(eintrag["deutsch"])}</span></div>')
        teile.append("</div>")

    offen = [e for e in hinweise if e[0] != uebersicht.LAGE]
    if offen:
        for stufe, text, wohin, _werkzeug in offen:
            farbe = FARBEN.get(stufe, "#5c6684")
            zusatz = f"<span>{html_modul.escape(wohin)}</span>" if wohin else ""
            teile.append(f'<div class="karte" style="border-left-color: {farbe}">'
                         f"<b>{html_modul.escape(text)}</b>{zusatz}</div>")
    else:
        teile.append('<div class="gut">Nichts Offenes — alles auf Stand.</div>')

    teile.append(FUSS)
    return "".join(teile)


def schreiben(still=False):
    inhalt = baue_seite()
    vorher = h.lies_datei(STATUS_HTML) if os.path.isfile(STATUS_HTML) else ""

    # Nur der Zeitstempel unterscheidet sich? Dann nicht neu schreiben -
    # sonst steht bei jedem Veroeffentlichen eine Aenderung im Protokoll.
    def ohne_stand(text):
        return "\n".join(z for z in text.splitlines() if "Stand:" not in z)

    if ohne_stand(inhalt) == ohne_stand(vorher):
        if not still:
            print("Statusseite unveraendert.")
        return False

    h.schreibe_datei(STATUS_HTML, inhalt, sichern=bool(vorher))
    if not still:
        print(f"Geschrieben: {os.path.relpath(STATUS_HTML, ROOT)}")
    return True


def main():
    print("=" * 60)
    print("  Statusseite fuers Handy")
    print("=" * 60)
    schreiben()
    print("\nErreichbar unter https://mch-singen.de/pages/status.html")
    print("Nicht verlinkt, auf 'noindex', in robots.txt ausgeschlossen.")


if __name__ == "__main__":
    main()
