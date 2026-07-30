document.addEventListener("DOMContentLoaded", function() {
    
    // --- 1. ZUSTAND SPEICHERN ---
    let activeClass = "Klasse 3"; // Start-Klasse
    let activeRun = "1. WL";      // Start-Lauf
    let isGesamt = false;         // Gesamtergebnis-Modus
    
    let liveData = [];            // Zwischenspeicher für die JSON-Daten
    let lastUpdate = "";          // Uhrzeit des letzten Abgleichs mit der Zeitmessung

    const gridContainer = document.getElementById('live-grid');
    const headerBar = document.getElementById('live-header-bar');
    const eventDate = document.querySelector('.event-date');
    const liveStatus = document.getElementById('live-status');

    // --- 2. KLICK-LOGIK FÜR DIE BUTTONS ---
    const classButtons = document.querySelectorAll('#class-filters .btn-filter');
    const runButtons = document.querySelectorAll('#run-filters .btn-filter');
    const allBtn = document.querySelector('.btn-filter[data-type="all"]');

    // Sobald der Besucher selbst filtert, wird nicht mehr automatisch
    // umgeschaltet (siehe waehleBelegteAnsicht weiter unten).
    let nutzerHatGewaehlt = false;

    classButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            classButtons.forEach(b => b.classList.remove('active'));
            if(allBtn) allBtn.classList.remove('active');
            this.classList.add('active');

            activeClass = this.innerText.trim();
            isGesamt = false;
            nutzerHatGewaehlt = true;
            renderTable();
        });
    });

    runButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            runButtons.forEach(b => b.classList.remove('active'));
            if(allBtn) allBtn.classList.remove('active');
            this.classList.add('active');

            activeRun = this.innerText.trim();
            isGesamt = false;
            nutzerHatGewaehlt = true;
            renderTable();
        });
    });

    if(allBtn) {
        allBtn.addEventListener('click', function() {
            classButtons.forEach(b => b.classList.remove('active'));
            runButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            isGesamt = true;
            nutzerHatGewaehlt = true;
            renderTable();
        });
    }

    // --- 3. HILFSFUNKTION: ZEIT IN MILLISEKUNDEN UMRECHNEN ---
    // Macht aus "01:00,39" eine echte Zahl (60390), mit der der Browser sortieren kann.
    // Alles, was keine Zeit ist (leer oder "ADW" bei Ausschluss), kommt ans Ende.
    const ZEIT_MUSTER = /^(\d{1,3}):([0-5]?\d),(\d{1,2})$/;
    function parseTimeToMs(timeStr) {
        let treffer = ZEIT_MUSTER.exec((timeStr || "").trim());
        if (!treffer) return 999999999;
        let m = parseInt(treffer[1], 10);
        let s = parseInt(treffer[2], 10);
        let hundertstel = parseInt(treffer[3].padEnd(2, '0'), 10);
        return (m * 60 * 1000) + (s * 1000) + (hundertstel * 10);
    }

    // Aus 60390 wird wieder "01:00,39"
    function msToZeit(ms) {
        const hundertstel = Math.round(Math.abs(ms) / 10);
        const m = Math.floor(hundertstel / 6000);
        const s = Math.floor(hundertstel / 100) % 60;
        const h = hundertstel % 100;
        return String(m).padStart(2, '0') + ':' +
               String(s).padStart(2, '0') + ',' +
               String(h).padStart(2, '0');
    }

    // Strafsekunden kommen als "(12)" aus der Zeitnahme - lesbarer als "+12 s"
    function strafeLesbar(fehler) {
        const zahl = /^\((\d+)\)$/.exec(String(fehler || "").trim());
        return zahl ? `+${zahl[1]} s` : String(fehler || "");
    }

    // Namen und Vereine kommen aus der Zeitmessung und werden dort von Hand
    // getippt - vor dem Einsetzen ins HTML also entschaerfen.
    function escapeHtml(wert) {
        return String(wert === undefined || wert === null ? "" : wert)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    const vereinfacht = t => (t || "").replace(/\s+/g, '').toUpperCase();

    // Beim ersten Laden auf eine Ansicht springen, in der auch wirklich Zeiten
    // stehen. Sonst landet der Besucher auf der Voreinstellung (Klasse 3 / TL)
    // und sieht eine leere Tabelle, obwohl das Rennen längst läuft.
    function waehleBelegteAnsicht() {
        if (nutzerHatGewaehlt || isGesamt || liveData.length === 0) return;

        const hatDaten = (klasse, lauf) => liveData.some(d =>
            vereinfacht(d.klasse) === vereinfacht(klasse) &&
            vereinfacht(d.lauf) === vereinfacht(lauf));

        if (hatDaten(activeClass, activeRun)) {
            nutzerHatGewaehlt = true;   // Voreinstellung passt, nicht mehr eingreifen
            return;
        }

        for (const laufBtn of runButtons) {
            for (const klasseBtn of classButtons) {
                const lauf = laufBtn.innerText.trim();
                const klasse = klasseBtn.innerText.trim();
                if (!hatDaten(klasse, lauf)) continue;

                runButtons.forEach(b => b.classList.remove('active'));
                classButtons.forEach(b => b.classList.remove('active'));
                laufBtn.classList.add('active');
                klasseBtn.classList.add('active');
                activeRun = lauf;
                activeClass = klasse;
                nutzerHatGewaehlt = true;
                return;
            }
        }
    }

    // Zustandsmeldung statt leerer Tabelle
    function zeigeHinweis(titel, text, icon) {
        gridContainer.innerHTML = `
            <div class="live-empty">
                <i class="fa-solid ${icon}"></i>
                <h2>${titel}</h2>
                <p>${text}</p>
            </div>`;
    }

    // --- 4. TABELLE BAUEN (HTML GENERIEREN) ---
    function renderTable() {
        if (!liveData || liveData.length === 0) {
            headerBar.innerHTML = `Live-Timing`;
            zeigeHinweis("Noch keine Zeiten",
                "Sobald die Zeitnahme an der Strecke läuft, erscheinen die Ergebnisse " +
                "hier von selbst - die Seite muss nicht neu geladen werden.",
                "fa-stopwatch");
            return;
        }

        // A) Daten filtern (Robust gegen fehlende Leerzeichen, z.B. "1.WL" vs "1. WL")
        let filteredData;
        let titel;
        if (!isGesamt) {
            let normalizedActiveRun = vereinfacht(activeRun);
            let normalizedActiveClass = vereinfacht(activeClass);

            filteredData = liveData.filter(d =>
                vereinfacht(d.klasse) === normalizedActiveClass &&
                vereinfacht(d.lauf) === normalizedActiveRun);

            // Schöner Name für den blauen Balken (aus 1. WL wird 1. Wertungslauf)
            let titleLauf = activeRun;
            if (activeRun === "1. WL") titleLauf = "1. Wertungslauf";
            if (activeRun === "2. WL") titleLauf = "2. Wertungslauf";

            titel = `${titleLauf} &middot; ${activeClass}`;
        } else {
            // Das Gesamtergebnis ist ein eigener Lauf ("Gesamt" = beide
            // Wertungsläufe zusammen), nicht einfach alle Zeilen auf einmal -
            // sonst stünden Einzel- und Gesamtzeiten wild gemischt in einer Tabelle.
            filteredData = liveData.filter(d => vereinfacht(d.lauf) === "GESAMT");
            titel = "Gesamtergebnis &middot; alle Klassen";
        }

        // B) AUTOMATISCHES SORTIEREN & PLATZIERUNG KORRIGIEREN
        // Nach Gesamtzeit sortieren (schnellste Zeit zuerst)
        filteredData.sort((a, b) => {
            return parseTimeToMs(a.zeit_total) - parseTimeToMs(b.zeit_total);
        });

        // Den Platz (1, 2, 3...) streng von oben nach unten neu durchnummerieren!
        // Die Rückstände werden hier ebenfalls neu gerechnet und NICHT aus der
        // JSON übernommen: dort stehen sie je Klasse, im Gesamtergebnis werden
        // aber alle Klassen zusammen gewertet - die Werte passten dann nicht.
        let bestzeit = null;
        let vorherige = null;
        filteredData.forEach((driver, index) => {
            driver.platz = index + 1;

            const zeit = parseTimeToMs(driver.zeit_total);
            const gueltig = zeit !== 999999999;
            if (gueltig && bestzeit === null) bestzeit = zeit;

            driver._aufErsten = (gueltig && bestzeit !== null && index > 0)
                ? '+' + msToZeit(zeit - bestzeit) : "";
            driver._aufVordermann = (gueltig && vorherige !== null && index > 0)
                ? '+' + msToZeit(zeit - vorherige) : "";
            if (gueltig) vorherige = zeit;
        });

        // C) Kopfzeile über der Tabelle
        headerBar.innerHTML = titel +
            `<span class="results-count">${filteredData.length} ` +
            `${filteredData.length === 1 ? "Starter" : "Starter"}</span>`;

        if (filteredData.length === 0) {
            headerBar.innerHTML = titel;
            zeigeHinweis("Für diese Auswahl liegen noch keine Zeiten vor",
                "Wähle eine andere Klasse oder einen anderen Lauf - oder warte, " +
                "bis diese Gruppe gefahren ist.",
                "fa-filter-circle-xmark");
            return;
        }

        // D) Tabellenkopf: fünf echte Spalten
        let html = `
            <div class="grid-header grid-header--mitte">Platz</div>
            <div class="grid-header grid-header--mitte">Nr.</div>
            <div class="grid-header">Fahrer &middot; Ortsclub</div>
            <div class="grid-header grid-header--rechts">Gesamtzeit</div>
            <div class="grid-header grid-header--rechts">Differenz<br>Intervall</div>
        `;

        // E) Eine Zeile je Fahrer
        filteredData.forEach((driver) => {
            const ausgefallen = parseTimeToMs(driver.zeit_total) === 999999999;

            // Zweite Zeile der Zeit-Spalte: reine Fahrzeit und Strafsekunden.
            // Nur zeigen, wenn sie etwas hinzufügt (bei Strafzeit null ist die
            // Fahrzeit gleich der Gesamtzeit).
            let zeitDetail = "";
            if (driver.fehler) {
                zeitDetail = `${escapeHtml(driver.zeit_raw)} ` +
                             `<span class="zeit-strafe">${escapeHtml(strafeLesbar(driver.fehler))}</span>`;
            } else if (ausgefallen && driver.zeit_raw) {
                zeitDetail = escapeHtml(driver.zeit_raw);
            }

            // Rückstand: der Führende bekommt kein "+00:00,00", sondern ein Wort
            let rueckstand;
            if (driver.platz === 1) {
                rueckstand = `<span class="diff-fuehrend">Führend</span>`;
            } else if (driver._aufErsten) {
                // Reihenfolge wie im Spaltenkopf: Differenz zum Führenden,
                // darunter das Intervall zum Vordermann
                rueckstand =
                    `<span class="diff-first">${driver._aufErsten}</span>` +
                    (driver._aufVordermann
                        ? `<span class="diff-prev">${driver._aufVordermann}</span>`
                        : "");
            } else {
                rueckstand = `<span class="diff-prev">&ndash;</span>`;
            }

            html += `
                <div class="driver-row driver-row--platz${driver.platz}">
                    <div class="cell-platz">
                        <span class="platz-badge">${driver.platz}</span>
                    </div>
                    <div class="cell-nr">
                        <span class="startnummer">${escapeHtml(driver.startnummer)}</span>
                    </div>
                    <div class="cell-fahrer">
                        <span class="driver-name">${escapeHtml(driver.name)}</span>
                        <span class="driver-club">${escapeHtml(driver.club)}</span>
                    </div>
                    <div class="cell-zeit">
                        <span class="zeit-gesamt${ausgefallen ? ' zeit-gesamt--ausfall' : ''}">${escapeHtml(driver.zeit_total)}</span>
                        ${zeitDetail ? `<span class="zeit-detail">${zeitDetail}</span>` : ''}
                    </div>
                    <div class="cell-diff">${rueckstand}</div>
                </div>
            `;
        });

        gridContainer.innerHTML = html;
    }

    // --- 5. DATEN VOM SERVER LADEN (Der "Puls") ---
    // data/livedata.json wird von tools/livetiming_sync.py aus der Datenbank
    // der Zeitmessung erzeugt und bei jeder Änderung neu veröffentlicht.
    async function fetchLiveData() {
        try {
            // Das "?t=" am Ende umgeht den Browser-Cache, damit immer die neuste Datei geladen wird
            const response = await fetch(`../data/livedata.json?t=${new Date().getTime()}`);
            if (response.ok) {
                const data = await response.json();
                liveData = Array.isArray(data.results) ? data.results : [];
                lastUpdate = data.last_update || "";
                // Renntag aus den Daten übernehmen, damit im Kopf nicht das
                // Datum einer vergangenen Veranstaltung stehen bleibt
                if (eventDate && data.datum) eventDate.innerText = data.datum;
                if (liveStatus) {
                    liveStatus.innerText = lastUpdate
                        ? `Stand ${lastUpdate}`
                        : "Warte auf Zeitnahme";
                }
                waehleBelegteAnsicht();
                renderTable(); // Tabelle sofort mit neuen Daten zeichnen
            }
        } catch (error) {
            console.log("Warte auf Verbindung zur Zeitnahme...");
        }
    }

    // Beim Start sofort einmal laden...
    fetchLiveData();
    
    // ...und ab dann alle 3 Sekunden nach neuen Daten schauen
    setInterval(fetchLiveData, 3000); 

});