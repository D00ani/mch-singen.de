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

/tools/                   -> Alle Pflege- und Hilfsskripte (siehe Abschnitt 10!)

/data/                    -> Textdateien und JSON für Timer, Countdown und Live-Daten
  timer.txt               -> Kart-Renntermine und Countdown
  timer_trial.txt         -> Trial-Termine und Countdown
  trainingstermine2026.txt -> Trainingstermine fürs Kalender-Download (jährlich aktualisieren)
  trainingstermine2026_excel-export.txt -> unveränderter Excel-Export als Beleg
  statistik.json          -> Zahlen der Diagramme auf der Statistik-Seite
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

EINFACHER GEHT'S MIT DEM TOOL statt von Hand zu tippen:
    python tools/termine_verwalten.py
(oder per Doppelklick auf website-pflege.bat eine Ebene über mch-arbeit/ ->
Menüpunkt "Renntermine verwalten", siehe Abschnitt 10)
Fragt Kart/Trial ab, dann Hinzufuegen/Bearbeiten/Loeschen:
  - Hinzufuegen: laesst bekannte Vereine/Orte per Nummer auswaehlen
    (Maps-Link wird automatisch uebernommen), prueft Datum/Uhrzeit auf
    Gueltigkeit, erkennt Duplikate und schlaegt den PDF-Dateinamen
    automatisch vor.
  - Bearbeiten/Loeschen: zeigt alle vorhandenen Termine nummeriert an,
    Termin auswaehlen und Werte anpassen (Enter = behalten) oder loeschen.
Schreibt danach direkt in timer.txt bzw. timer_trial.txt.

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

-------------------------------------------------------
3b. MEDIEN RICHTIG VERLINKEN (PDFs, Bilder)
-------------------------------------------------------
Drei Stolpersteine - die Werkzeuge korrigieren sie inzwischen automatisch
und sagen dir, was sie geändert haben:

1. IMMER Schrägstriche "/", NIE Backslashes "\"
   Der Windows-Explorer zeigt "\", das Web kennt nur "/".
       \media\dokumente\datei.pdf     -> kaputt
       ../media/dokumente/datei.pdf   -> richtig

2. Der Anfang hängt davon ab, WO die Datei steht, in der der Link steht:
       Seiten in /pages/ (aktuelles.html, archiv.html, ...):  ../media/...
       index.html und 404.html (Hauptverzeichnis):            media/...
   Das "../" heißt "einen Ordner nach oben" - von /pages/ aus muss man
   erst hoch, bevor man /media/ findet.

3. AUSNAHME /data/timer.txt und timer_trial.txt: dort OHNE "../"
       ...;media/dokumente/kurzausschreibungacengen2026.pdf
   Grund: Der Countdown läuft nur auf index.html, und das Skript setzt den
   Pfad unverändert als Link ein.

WOHIN GEHÖRT WAS:
   Wertungen    -> /media/dokumente/wertungen/
   Terminpläne  -> /media/dokumente/termine/
   Jahresarchiv -> /media/dokumente/archiv/<JAHR>/
   Bilder       -> /media/bilder/<thema>/

Externe Links (auf fremde Webseiten) bekommen zusätzlich
target="_blank" rel="noopener noreferrer" - das setzen die Werkzeuge
ebenfalls von allein.

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

  Aufbau der Zeile: Tag;Monat;Jahr;Startzeit-Endzeit;Gruppe
  Beispiel: 15;Mai;2026;10:00-13:30;1
  (Gruppe 3 = Termin gilt für BEIDE Gruppen)

  WICHTIG hierbei: Schreibe die Monate in dieser Datei auf DEUTSCH! (Mai, Juni, Juli etc.).

  DAS MACHT DAS TOOL FÜR DICH - von Hand ist das fehleranfällig:
      python tools/trainingstermine_import.py
  (oder website-pflege.bat -> "Trainingstermine importieren")
  Du legst einfach den Excel-Export als .txt in /data/ ab. Das Tool erkennt
  die Trainingszeiten-Spalten, wandelt die Tab-Tabelle in obiges Format um,
  repariert die Excel-Kodierung (Umlaute!), überspringt Zeilen ohne Gruppe
  (Stammtische, Rennen) und passt den Dateinamen in /js/aktuelles.js an.
  Der unveränderte Export bleibt als *_excel-export.txt liegen.

  ACHTUNG (war bis Juli 2026 ein Fehler): Wird der Excel-Export ungewandelt
  abgelegt, findet die Webseite KEINE Termine und der Kalender-Download
  liefert eine leere Datei - ohne sichtbare Fehlermeldung.

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

EINFACHER GEHT'S MIT DEM TOOL statt HTML-Zeilen von Hand zu kopieren:
    python tools/statistiken_pflege.py
(oder per Doppelklick auf website-pflege.bat -> Menüpunkt "Statistiken-Seite
pflegen", siehe Abschnitt 10)
Deckt ALLE Bereiche der Statistik-Seite ab, jeweils mit nummerierter Auswahl
zum Hinzufügen/Bearbeiten/Löschen, ohne HTML anzufassen:
  - Tabelle "Unsere Top-Platzierungen" (inkl. Fett-Hervorhebung der Platzierung)
  - Wanderpokal-Sieger Jugend und Erwachsen
  - Die "Vereinsbestleistungen"-Boxen
  - Die Meilenstein-Zahlen oben (Gegründet, Aktive Fahrer, Pokale, Mitglieder)
  - Die Diagramm-Werte und deren Überschriften

ZU DEN DIAGRAMMEN: Die Zahlen stehen seit Juli 2026 in /data/statistik.json
und NICHT mehr in js/statistiken.js. Dadurch ist nach einer Änderung KEIN
Build-Schritt mehr nötig. Das Diagramm "Dieses Jahr (Bisher)" wird weiterhin
automatisch aus der Wertungs-PDF berechnet (Abschnitt 5b) und lässt sich
deshalb nicht von Hand ändern.

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

EINFACHER GEHT'S MIT DEM TOOL statt HTML von Hand zu ergaenzen:
    python tools/archiv_pflege.py
(oder per Doppelklick auf website-pflege.bat -> Menüpunkt "Jahresarchiv
pflegen", siehe Abschnitt 10)
Legt bei einer neuen Saison automatisch den Ordner media/dokumente/archiv/JAHR/
an, erkennt eine bereits hochgeladene bkcgesamtwertung_JAHR.pdf aus
media/dokumente/wertungen/ und bietet an, sie direkt als Archiv-PDF zu
kopieren. Danach koennen weitere Eintraege pro Saison hinzugefuegt,
bearbeitet oder geloescht werden.

-------------------------------------------------------
7. TEXTE UND BILDER AUSTAUSCHEN
-------------------------------------------------------
TEXTE: Öffne die .html Datei, suche die Textpassage und ändere den Text ZWISCHEN
den spitzen HTML-Klammern (z.B. <p>Dein Text</p>).

BILDER: Lade das neue Bild in den passenden Unterordner unter /media/bilder/ hoch.
Suche in der .html Datei nach dem <img src="..."> Code und ersetze den Pfad.
HINWEIS: Die meisten Bilder werden zusätzlich als schnelles WebP-Format
ausgeliefert (<picture>-Blöcke im HTML).

  NEUES Bild aufnehmen -> das Tool nimmt dir die Arbeit ab:
      python tools/bilder_pflege.py
  (oder website-pflege.bat -> "Bilder aufnehmen")
  Es zeigt alle Bilder ohne WebP-Fassung, fragt nach dem Verwendungszweck
  (Kopfbereich/Textbereich/Vorschaubild/Logo), erzeugt die passenden Größen
  und gibt den fertigen <picture>-Block zum Einfügen aus.

  BESTEHENDES Bild ERSETZT (gleicher Dateiname) -> wie bisher:
      python tools/optimize_images.py
  Das erzeugt die vorhandenen .webp-Fassungen neu (siehe Abschnitt 9).

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
10. WEBSEITEN-PFLEGE - EIN WERKZEUG FÜR ALLES (website-pflege.bat)
-------------------------------------------------------
Eine Ebene über /mch-arbeit/ und /mch-singen.de-main/ liegt
website-pflege.bat - der EINE Startpunkt für die gesamte Wartung.
Einfach per Doppelklick starten, dann im Menü wählen:

 1) Renntermine (Kart/Trial) verwalten          -> Abschnitt 2
 2) Trainingstermine importieren (Excel-Export) -> Abschnitt 4
 3) Statistiken-Seite pflegen                   -> Abschnitt 5
    (Top-Platzierungen, Vereinsmeister, Rekorde, Meilensteine, Diagramme)
 4) News-Karten auf "Aktuelles" pflegen
    Neue Meldung anlegen (Datum, Titel, Text, Kennzeichen, Link),
    bestehende ändern oder löschen - ohne HTML-Blöcke zu kopieren.
 5) Jahresarchiv pflegen                        -> Abschnitt 6
 5b) Sponsoren-Seite pflegen
    Deckt die KOMPLETTE Seite sponsoren-links.html ab, kein HTML nötig:
      - Sponsoren (Logos): hinzufügen, bearbeiten, entfernen
      - Befreundete Vereine: Einträge samt Sinnbild verwalten
      - Nützliche Links: dito
      - Zahlen oben (Gegründet, Mitglieder, Events, Sportarten)
      - Aufruf "Werde Sponsor": Einleitung, die drei Vorteils-Kästen,
        Beschriftung der Schaltfläche

    NEUEN SPONSOR ANLEGEN: Logo-Datei nach /media/sponsoren/ legen (Dateiname
    klein, ohne Umlaute und Leerzeichen), dann im Werkzeug auswählen. Es
    erzeugt die WebP-Fassung, berechnet die Anzeigegröße und legt die
    Banden-Karte an der gewünschten Stelle an.

    ZUR ANZEIGEGRÖSSE: Die Logos haben sehr unterschiedliche Seitenverhältnisse.
    Würde man alle gleich hoch anzeigen, wirkten hochkante Logos halb so groß
    wie querformatige. Das Werkzeug rechnet deshalb für jedes Logo eine eigene
    Größe aus, sodass alle dieselbe FLÄCHE einnehmen - deswegen stehen in
    sponsoren-links.html bei jedem Logo andere width/height-Werte.
    Nach einem Logo-Tausch "Alle Logo-Größen neu berechnen" aufrufen.

    "Logos in WebP umwandeln" wandelt noch vorhandene JPG/PNG-Logos um und
    bindet sie direkt ein (spart deutlich Ladezeit - bei den sieben Logos
    waren es 532 KB vorher, 116 KB nachher). Die alten Dateien können dabei
    gelöscht werden.
 6) Bilder aufnehmen (WebP + HTML-Block)        -> Abschnitt 7
 7) Webseite prüfen
    Findet tote Links, falsche Groß-/Kleinschreibung (die auf dem
    GitHub-Server Bilder verschwinden lässt!), vergessene Build-Schritte
    und noch nicht hochgeladene Kurzausschreibungen.
 8) Saisonwechsel-Assistent
    Führt beim Jahreswechsel Schritt für Schritt durch alles: Archiv,
    Diagramm einfrieren, Vereinsmeister, Trainings- und Renntermine,
    technisches Update. Jeder Schritt lässt sich überspringen.
 9) Technisches Update (Statistik/Bilder/Copyright/Build + Push)
    Führt aus: update_statistik.py, optimize_images.py,
    update_copyright_year.py (setzt "© <Jahr>" im Footer aller Seiten)
    und build_assets.py.
10) Letzte Änderung rückgängig machen
    Vor jeder Änderung legt das Werkzeug automatisch eine Sicherung an
    (Ordner .pflege-sicherungen/, bleibt lokal). Damit lässt sich ein
    Vertipper zurückholen - auch nachdem er schon gepusht wurde.

MIT "x" IMMER EINEN SCHRITT ZURÜCK: An JEDER Eingabestelle bringt dich
ein "x" einen Schritt zurück - im Menü eine Ebene höher, in einem Formular
zu der Frage davor (die falsche Eingabe wird verworfen und neu gestellt).
"x" in der ersten Frage bricht die Aktion ab, ohne etwas zu speichern.
Man kann sich also nie "verrennen" und muss ein Formular nicht mehr zu
Ende ausfüllen, nur weil man sich vertippt hat.
(Nebenwirkung: Ein einzelnes "x" lässt sich dadurch nicht als Wert
eingeben - bei einem Namen o. ä. einfach "X." schreiben.)

NEUE EINTRÄGE WERDEN AUTOMATISCH EINSORTIERT - sie landen nicht mehr
einfach oben, sondern an der Stelle, wo sie hingehören. Das Werkzeug sagt
dir vorher, wo der Eintrag landet ("Wird an Position 5 von 9 einsortiert"):
  - Wanderpokal-Sieger und Top-Platzierungen: neuestes Jahr zuerst
    (trägst du 2021 nach, rutscht es unter 2022)
  - Jahresarchiv: neueste Saison oben
  - Renntermine: chronologisch nach Datum und Uhrzeit
  - News-Karten: hier steht im Datum Freitext ("Saison 2026"), das lässt
    sich nicht zuverlässig sortieren - deshalb fragt das Werkzeug, an
    welcher Stelle des Abschnitts die Karte stehen soll.

VERÖFFENTLICHEN PASSIERT AUTOMATISCH: Beim Beenden mit "0" prüft das
Werkzeug die Seite, aktualisiert die Datumsangaben in sitemap.xml und
veröffentlicht dann alles Geänderte (Commit in arbeit -> Merge nach main
-> Push). Werden beim Prüfen Fehler gefunden, wird vorher gefragt, ob
trotzdem veröffentlicht werden soll.

Nach jedem Menüpunkt kommt man wieder zurück ins Hauptmenü - so lassen
sich in einem Durchgang z. B. Renntermine eintragen, die Statistik-Seite
aktualisieren und eine News-Karte anlegen, bevor alles zusammen online geht.

website-pflege.bat liegt bewusst außerhalb beider Git-Ordner (ist also
nicht Teil des Repos) und muss bei einem neuen PC neu angelegt werden;
die Python-Werkzeuge selbst liegen in /tools/ und sind versioniert.

Einmalige Vorbereitung auf einem neuen PC: Python installieren, dann
"pip install pdfplumber csscompressor rjsmin Pillow" ausführen.
=======================================================
