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
