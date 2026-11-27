# -*- coding: utf-8 -*-
"""
Zeigt die Webseite so an, wie sie spaeter online aussieht - bevor
irgendetwas veroeffentlicht wird.

Ein Doppelklick auf index.html reicht dafuer NICHT: der Browser laedt
Dateien dann ueber file:// und blockt genau die Sachen, die die Seite
braucht (Countdown, Suche, Live-Timing holen ihre Daten per fetch).
Deshalb wird hier ein kleiner Webserver gestartet - wie bei GitHub Pages.

Ausfuehren: python tools/vorschau.py
"""
import functools
import os
import socket
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pflege_hilfen as h

ROOT = h.ROOT
START_PORT = 8000
SEITEN = [
    ("Startseite", "index.html"),
    ("Aktuelles", "pages/aktuelles.html"),
    ("Kartsport", "pages/kartsport.html"),
    ("Trialsport", "pages/trialsport.html"),
    ("Statistiken", "pages/statistiken.html"),
    ("Archiv", "pages/archiv.html"),
    ("Live-Timing", "pages/live.html"),
]


class Handler(SimpleHTTPRequestHandler):
    """Wie GitHub Pages: unbekannte Adressen bekommen 404.html zu sehen."""

    def send_error(self, code, message=None, explain=None):
        seite = os.path.join(ROOT, "404.html")
        if code == 404 and os.path.isfile(seite):
            inhalt = open(seite, "rb").read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(inhalt)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(inhalt)
            return
        super().send_error(code, message, explain)

    def log_message(self, format, *args):
        pass  # Zugriffsprotokoll wuerde die Anleitung im Fenster zumuellen


def freier_port(start=START_PORT, versuche=20):
    for port in range(start, start + versuche):
        with socket.socket() as pruefer:
            if pruefer.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return None


# ------------------------------------------------------------------
# Entwurf ansehen, bevor gespeichert wird
# ------------------------------------------------------------------
# Das Pflege-Fenster reicht den geaenderten Seitentext herein, ohne ihn zu
# speichern. Ein eigener kleiner Server liefert fuer diese Seiten den
# Entwurf aus, fuer alles andere (CSS, Bilder, andere Seiten) die echten
# Dateien - die Seite sieht also genau so aus wie nach dem Speichern.
# Die geaenderten Stellen tragen data-vorschau-neu und werden gelb markiert.

MARKE = "data-vorschau-neu"
_ENTWURF = {"server": None, "port": None, "seiten": {}, "nummer": 0}

_ENTWURF_ZUSATZ = """<style id="mch-entwurf">
[data-vorschau-neu]{outline:3px solid #f2b705!important;outline-offset:3px;background-color:rgba(242,183,5,.25)!important;border-radius:3px;scroll-margin:140px}
mark[data-vorschau-neu]{color:inherit;padding:0 2px}
.mch-entwurf-band{position:fixed;left:0;right:0;bottom:0;z-index:2147483647;background:#1b2440;color:#fff;font:600 14px/1.45 system-ui,sans-serif;padding:10px 16px;text-align:center;box-shadow:0 -2px 12px rgba(0,0,0,.35)}
.mch-entwurf-band b{color:#f2b705}
</style>
<script>
addEventListener('load', function () {
  var stellen = Array.prototype.slice.call(document.querySelectorAll('[data-vorschau-neu]'));
  // Zugeklappte Bereiche (Fragen, "Weiterlesen", <details>) um die Stelle oeffnen
  stellen.forEach(function (e) {
    for (var a = e; a && a !== document.body; a = a.parentElement) {
      if (a.tagName === 'DETAILS') a.open = true;
      if (a.id) {
        var k = document.querySelector('[aria-controls="' + a.id + '"][aria-expanded="false"]');
        if (k) k.click();
      }
    }
  });
  setTimeout(function () {
    var sichtbar = stellen.filter(function (e) { return e.getClientRects().length; });
    var band = document.createElement('div');
    band.className = 'mch-entwurf-band';
    var text = '<b>Vorschau</b> \\u2013 noch nicht gespeichert. ';
    if (!stellen.length) text += 'Auf dieser Seite \\u00e4ndert sich nichts Sichtbares.';
    else text += 'Gelb markiert: ' + stellen.length + (stellen.length === 1 ? ' ge\\u00e4nderte Stelle.' : ' ge\\u00e4nderte Stellen.');
    if (stellen.length && sichtbar.length < stellen.length)
      text += ' ' + (sichtbar.length ? (stellen.length - sichtbar.length) + ' davon' : 'Sie ist') +
        ' in dieser Fensterbreite nicht zu sehen (z.\\u00a0B. nur am Handy oder nur am Computer) \\u2013 Fenster schmaler bzw. breiter ziehen.';
    band.innerHTML = text;
    document.body.appendChild(band);
    if (sichtbar.length) sichtbar[0].scrollIntoView({ block: 'center' });
  }, 400);
});
</script>
"""


class _StillerServer(ThreadingHTTPServer):
    """Bricht der Browser eine Verbindung ab (Video, Seitenwechsel), ist
    das kein Fehler - also auch keine Meldung."""

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


class EntwurfHandler(Handler):
    """Wie Handler, nur dass Seiten mit Entwurf aus dem Speicher kommen."""

    def do_GET(self):
        from urllib.parse import unquote, urlsplit
        pfad = unquote(urlsplit(self.path).path).lstrip("/")
        if pfad == "" or pfad.endswith("/"):
            pfad += "index.html"
        text = _ENTWURF["seiten"].get(pfad)
        if text is None:
            return super().do_GET()
        daten = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(daten)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(daten)

    def end_headers(self):
        # Auch CSS/JS nie aus dem Zwischenspeicher - sonst zeigt der Browser
        # nach einem Build noch den alten Stand
        if not any(z.lower().startswith(b"cache-control") for z in getattr(self, "_headers_buffer", [])):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


def mit_markierung(text):
    """Haengt Markierungsstil und Hinweisband in den <head> der Seite."""
    stelle = text.lower().find("</head>")
    if stelle == -1:
        return _ENTWURF_ZUSATZ + text
    return text[:stelle] + _ENTWURF_ZUSATZ + text[stelle:]


def markiere_tag(oeffnendes_tag):
    """'<p class="x">' -> '<p class="x" data-vorschau-neu>'"""
    if MARKE in oeffnendes_tag:
        return oeffnendes_tag
    ende = -2 if oeffnendes_tag.endswith("/>") else -1
    return oeffnendes_tag[:ende] + " " + MARKE + oeffnendes_tag[ende:]


def entwurf_adresse(seiten, start=None):
    """Legt die Entwuerfe ab und gibt die Adresse der Startseite zurueck.

    seiten: {Pfad ab Wurzel wie "pages/kartsport.html": kompletter neuer Text}
    start:  welche davon geoeffnet wird (Standard: die erste)
    """
    if not seiten:
        raise ValueError("Es gibt nichts zu zeigen - an keiner Seite ändert sich etwas.")
    if _ENTWURF["server"] is None:
        server = _StillerServer(("127.0.0.1", 0),
                                functools.partial(EntwurfHandler, directory=ROOT))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _ENTWURF["server"], _ENTWURF["port"] = server, server.server_address[1]
    _ENTWURF["seiten"] = {pfad.replace("\\", "/"): mit_markierung(text)
                          for pfad, text in seiten.items()}
    _ENTWURF["nummer"] += 1
    start = (start or next(iter(seiten))).replace("\\", "/")
    return f"http://127.0.0.1:{_ENTWURF['port']}/{start}?entwurf={_ENTWURF['nummer']}"


def entwurf_zeigen(seiten, start=None):
    """Wie entwurf_adresse(), oeffnet die Seite aber gleich im Browser."""
    adresse = entwurf_adresse(seiten, start)
    webbrowser.open(adresse)
    return adresse


def entwurf_beenden():
    if _ENTWURF["server"] is not None:
        _ENTWURF["server"].shutdown()
        _ENTWURF["server"].server_close()
    _ENTWURF.update(server=None, port=None, seiten={})


def main():
    print("=" * 60)
    print("  Vorschau im Browser")
    print("=" * 60)

    port = freier_port()
    if port is None:
        print(f"\nKein freier Port zwischen {START_PORT} und {START_PORT + 19} gefunden.")
        print("Laeuft vielleicht noch eine Vorschau in einem anderen Fenster?")
        return

    server = ThreadingHTTPServer(
        ("127.0.0.1", port), functools.partial(Handler, directory=ROOT))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    adresse = f"http://localhost:{port}/"
    print(f"\nDie Seite laeuft jetzt unter:  {adresse}")
    print("\nDirekt zu einer Unterseite:")
    for name, pfad in SEITEN:
        print(f"  {name:<14} {adresse}{pfad}")

    print("\nDas ist NUR auf diesem Rechner sichtbar - es ist nichts veroeffentlicht.")
    print("Aenderungen an HTML/Bildern siehst du sofort nach dem Neuladen (F5).")
    print("Bei Aenderungen an CSS/JS vorher den Build laufen lassen, sonst")
    print("siehst du noch den alten Stand (die Seite laedt die .min-Fassungen).")

    webbrowser.open(adresse)

    try:
        input("\nZum Beenden hier Enter druecken ... ")
    except (EOFError, KeyboardInterrupt):
        pass

    server.shutdown()
    print("\nVorschau beendet.")


if __name__ == "__main__":
    main()
