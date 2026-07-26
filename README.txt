=======================================================
HINWEISE ZUR WARTUNG UND PFLEGE DER MCH SINGEN WEBSEITE
=======================================================

Dieses Dokument ist ein Leitfaden zur Pflege der Webseite. Es erklärt dir, wie du
Rennen aktualisierst, PDFs verknüpfst, Downloads steuerst und Statistiken eintragen kannst.

Bitte bearbeite die Dateien (wie HTML oder TXT) immer mit einem einfachen
Texteditor (z. B. Notepad, Notepad++, VS Code).

-------------------------------------------------------
1. DIE ORDNER-STRUKTUR (Wo finde ich was?)
-------------------------------------------------------

/ (Hauptverzeichnis)
  index.html              -> Startseite
  404.html                -> Fehlerseite
  robots.txt, sitemap.xml -> SEO-Dateien

/pages/                   -> Alle Unterseiten (statistiken.html, aktuelles.html etc.)
/css/                     -> Design-Dateien (Farben, Layouts, Abstände)
/js/                      -> Eigene Steuerungs-Skripte (Timer, Kalender-Downloads etc.)
/js/vendor/               -> Eingebundene Bibliotheken (chart.js, klaro.js) - NICHT bearbeiten!
/webfonts/                -> Schriftarten

/tools/                   -> Hilfsskripte für die Performance-Optimierung (siehe Abschnitt 9!)

/data/                    -> Textdateien und JSON für Timer, Countdown und Live-Daten
  timer.txt               -> Kart-Renntermine und Countdown
  timer_trial.txt         -> Trial-Termine und Countdown
  trainingstermine2026.txt -> Trainingstermine fürs Kalender-Download (jährlich aktualisieren)
  livedata.json           -> Live-Timing-Daten (wird von live.html genutzt)

/media/                   -> Alle Medien-Dateien
  /logos/                 -> Vereinslogo (favicon.png) und DMV-Logo (dmv.png)
  /bilder/                -> Fotos, nach Thema sortiert
    /kartsport/           -> Kart-Bilder (kart_abteilung.jpg, mach1-kart.png)
    /trial/               -> Trial-Bilder (trial1.jpg, trial2.jpg, trial_abteilung.jpg)
    /geschichte/          -> Historische Fotos
    /ueber-uns/           -> Team-Fotos
    mch_pic.jpg           -> Allgemeines Vereinsbild
  /videos/                -> Videos (onboard.mp4)
  /sponsoren/             -> Sponsoren-Logos
  /dokumente/             -> Alle PDFs und Dokumente
    /archiv/              -> Jahresauswertungen nach Jahr sortiert (2016 - aktuell)
    /wertungen/           -> Aktuelle Saisonwertungen (BKC etc.)
    /termine/             -> Terminpläne als PDF
    regelwerk.pdf         -> Aktuelles Regelwerk
    anmeldeformular.pdf   -> Anmeldeformular (Mitgliedschaft)
    kurzausschreibung*.pdf -> Kurzausschreibungen für Rennen

-------------------------------------------------------
2. RENN-KALENDER & COUNTDOWN ÄNDERN (timer.txt)
-------------------------------------------------------
Der Countdown auf der Startseite ("Nächstes Rennen...") berechnet sich automatisch.
Datei-Pfad: /data/timer.txt

Aufbau einer Zeile (strikt getrennt durch Semikolon ';'):
Tag;Monat;Jahr;Uhrzeit;Verein;Ort;GoogleMaps-Link;PDF-Link

Beispiel-Zeile:
07;June;2026;09:00;AC;Engen;https://maps.app.goo.gl/aUnnexHkVk5SySza6;/media/dokumente/kurzausschreibungacengen2026.pdf

WICHTIGE REGELN für die timer.txt:
1. Die Monate MÜSSEN zwingend auf ENGLISCH geschrieben werden! (June, July, etc.)
2. Es dürfen KEINE Leerzeichen vor oder nach dem Semikolon (;) stehen.

-------------------------------------------------------
3. KURZAUSSCHREIBUNG (PDF) VERKNÜPFEN
-------------------------------------------------------
Wird eine PDF verlinkt, erscheint unter dem Timer automatisch ein Download-Button.

Die PDF-Pfade für alle Rennen der laufenden Saison sind bereits in der timer.txt
vorausgeplant. Die Webseite prüft beim Laden automatisch per HEAD-Anfrage, ob die
Datei auf dem Server tatsächlich existiert:
  - Datei NICHT vorhanden -> Button bleibt unsichtbar, kein Fehler
  - Datei vorhanden       -> Button erscheint beim nächsten Seitenaufruf automatisch

DU MUSST NUR NOCH:
  PDF-Datei mit dem richtigen Namen in /media/dokumente/ hochladen - fertig!

Wichtig beim Dateinamen (GitHub-Server sind streng):
  - Nur Kleinbuchstaben, keine Leerzeichen, keine Umlaute
  - Beispiel: kurzausschreibungmchsingen2026.pdf
  - Den erwarteten Dateinamen für jedes Rennen findest du in /data/timer.txt
    (letztes Feld jeder Zeile, nach dem 7. Semikolon)

NEUES RENNEN EINTRAGEN (wenn ein Termin noch nicht in der timer.txt steht):
  Zeile am Ende ergänzen nach dem Schema aus Abschnitt 2.
  Den PDF-Pfad als 8. Feld eintragen. Sobald du die Datei hochlädst, erscheint
  der Button automatisch. Fehlt die PDF noch, bleibt das Feld leer oder du trägst
  den Pfad schon vor - der Button bleibt solange unsichtbar bis die Datei da ist.

-------------------------------------------------------
4. TERMINE FÜR DEN KALENDER-DOWNLOAD (Aktuelles)
-------------------------------------------------------
Auf der Seite "Aktuelles" können Mitglieder Termine in ihren Handy-Kalender speichern.

- RENN-TERMINE:
  Werden völlig automatisch aus der Datei /data/timer.txt (Siehe Punkt 2) generiert.

- TRAININGSTERMINE:
  Werden über eine eigene Textdatei gesteuert.
  Datei-Pfad: /data/trainingstermine2026.txt
  Jedes Jahr diese Datei aktualisieren (Inhalt ersetzen, Dateiname mit neuem Jahr benennen,
  dann auch in /js/aktuelles.js den Dateinamen anpassen).

  Aufbau der Zeile: Tag;Monat;Jahr;Uhrzeit;Gruppe
  Beispiel: 15;Mai;2026;10:00-13:30;1

  WICHTIG hierbei: Schreibe die Monate in dieser Datei auf DEUTSCH! (Mai, Juni, Juli etc.).

-------------------------------------------------------
5. STATISTIKEN PFLEGEN (Vereinsmeister etc.)
-------------------------------------------------------
Die Bestenlisten und Vereinsmeister sind fest in die Webseite eingebaut.

Um ein neues Jahr einzutragen:
1. Öffne die Datei /pages/statistiken.html
2. Suche nach der gewünschten Tabelle (z. B. Trial oder Kart).
3. Kopiere die oberste HTML-Tabellenzeile (alles von <tr> bis zum dazugehörigen </tr>).
4. Füge diese kopierte Zeile direkt darunter (oder darüber) als neue Zeile ein.
5. Ändere das Jahr und den Namen zwischen den <td>...</td> Klammern.
   Beispiel: <td>2026</td> <td>Max Mustermann</td>

HINWEIS ZUM DATENSCHUTZ: Du kannst in der HTML-Datei den vollen Namen eintragen.
Ein Skript auf der Webseite sorgt automatisch dafür, dass der Nachname der Fahrer
auf der fertigen Webseite nur mit einem Buchstaben abgekürzt wird (z. B. "Max M.").

-------------------------------------------------------
5b. CHART "DIESES JAHR (BISHER)" AUTOMATISCH AKTUALISIEREN
-------------------------------------------------------
Der Balken-Chart "Dieses Jahr (Bisher)" auf der Statistik-Seite (1./2./3.-Plätze
von MCH Singen) muss NICHT mehr von Hand aus der PDF abgezählt werden.

SO GEHT'S:
1. Neue/aktualisierte Wertungs-PDF wie gewohnt hochladen nach:
   /media/dokumente/wertungen/bkcgesamtwertung_<JAHR>.pdf
2. Einmal ausführen:
       python tools/update_statistik.py
   Das Skript sucht in der PDF die Vereinswertungs-Tabelle, findet automatisch
   die Zeile von "MCH Singen" (unabhängig davon, auf welchem Rang/in welcher
   Zeile der Verein gerade steht) und schreibt die Zahlen nach
   /data/statistik.json.
3. Fertig - die Webseite liest diese Datei beim Aufruf der Statistik-Seite
   automatisch ein. KEIN Build-Schritt nötig (nur eine JSON-Datei, kein JS/CSS).

Einmalige Vorbereitung auf einem neuen PC: pip install pdfplumber

Betrifft NUR den Chart "Dieses Jahr (Bisher)". Die Charts "Gesamt (seit 2016)"
und "Saison 2025" sind feste Werte in js/statistiken.js und müssten dort von
Hand geändert werden (siehe Abschnitt 9 für den nötigen Build-Schritt danach).

-------------------------------------------------------
6. JAHRESARCHIV ERWEITERN
-------------------------------------------------------
Am Ende einer Saison die Gesamtauswertung ins Archiv aufnehmen:

Schritt 1: PDF hochladen
Neuen Ordner unter /media/dokumente/archiv/JAHR/ anlegen und PDF dort hinein.
Beispiel: /media/dokumente/archiv/2026/BKC_Gesamtauswertung_2026.pdf

Schritt 2: In archiv.html verlinken
Öffne /pages/archiv.html und ergänze oben in der Liste einen neuen Eintrag nach dem
Muster der bestehenden Einträge.

-------------------------------------------------------
7. TEXTE UND BILDER AUSTAUSCHEN
-------------------------------------------------------
TEXTE: Öffne die .html Datei, suche die Textpassage und ändere den Text ZWISCHEN
den spitzen HTML-Klammern (z.B. <p>Dein Text</p>).

BILDER: Lade das neue Bild in den passenden Unterordner unter /media/bilder/ hoch.
Suche in der .html Datei nach dem <img src="..."> Code und ersetze den Pfad.
HINWEIS: Die meisten Bilder werden zusätzlich als schnelles WebP-Format
ausgeliefert (<picture>-Blöcke im HTML). Wenn du ein Bild ERSETZT (gleicher
Dateiname), führe danach einmal aus:  python tools/optimize_images.py
Das erzeugt die passenden .webp-Dateien neu (siehe Abschnitt 9).

LOGOS: Das MCH-Logo (favicon.png) und das DMV-Logo (dmv.png) liegen unter /media/logos/.
Im Header/Footer wird die kleine Version mch-logo-128.png verwendet (Ladezeit!).

-------------------------------------------------------
8. WICHTIGE HINWEISE ZU GITHUB PAGES
-------------------------------------------------------
- ACHTUNG GROSS-/KLEINSCHREIBUNG: Die Linux-Server von GitHub sind extrem streng.
  Wenn im Code steht: <img src="media/Foto.jpg">, die Datei aber foto.jpg heißt,
  wird sie auf GitHub nicht angezeigt!
- LADEZEIT: Wenn du etwas hochlädst, dauert es 1-3 Minuten, bis die Änderungen online sind.
- BROWSER-CACHE: Drücke auf der Webseite Strg + F5 (oder Cmd + Shift + R am Mac),
  um das Laden der neuesten Version zu erzwingen!

-------------------------------------------------------
9. PERFORMANCE-BUILD (WICHTIG BEI CSS/JS-ÄNDERUNGEN!)
-------------------------------------------------------
Die Webseite lädt aus Geschwindigkeitsgründen NICHT die Original-Dateien,
sondern minifizierte Versionen:
  - css/bundle.min.css  = alle css/*.css Basis-Dateien zusammengefasst
  - css/index.min.css, kartsport.min.css, live.min.css
  - js/*.min.js         = minifizierte Kopien der js/*.js Dateien

DAS BEDEUTET: Wenn du eine .css- oder .js-Datei änderst, ist die Änderung
ERST online sichtbar, nachdem du einmal dieses Kommando ausgeführt hast:

    python tools/build_assets.py

(Einmalige Vorbereitung auf einem neuen PC: Python installieren, dann
 "pip install csscompressor rjsmin Pillow" ausführen.)

Bei neuen oder ersetzten BILDERN entsprechend:

    python tools/optimize_images.py

HTML-Dateien und /data/-Dateien kannst du wie gewohnt direkt ändern,
dafür ist KEIN Build nötig.

-------------------------------------------------------
10. JÄHRLICHES UPDATE (jahres-update.bat)
-------------------------------------------------------
Eine Ebene über /mch-arbeit/ und /mch-singen.de-main/ liegt
jahres-update.bat. Einmal im Jahr per Doppelklick starten:

1. Zeigt zuerst eine Checkliste der Dinge, die NICHT automatisch gehen
   und echtes Saisonwissen brauchen (timer.txt, trainingstermine-Datei,
   Vereinsmeister-Zeile in statistiken.html, Archiv-Eintrag) - vorher
   erledigen, dann im Skript mit einer Taste bestätigen.
2. Führt automatisch aus: update_statistik.py, optimize_images.py,
   update_copyright_year.py (setzt "© <Jahr>" im Footer aller Seiten
   auf das aktuelle Jahr) und build_assets.py.
3. Zeigt die geänderten Dateien und fragt vor dem Commit/Push nach
   Bestätigung (j/n) - committet dann in arbeit, merged nach main
   und pusht.

Das Skript liegt bewusst außerhalb beider Git-Ordner (ist also nicht
Teil des Repos) und muss bei einem neuen PC neu angelegt werden.
=======================================================
