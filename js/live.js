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

    // --- 4. TABELLE BAUEN (HTML GENERIEREN) ---
    function renderTable() {
        if (!liveData || liveData.length === 0) {
            headerBar.innerText = "Keine Daten verfügbar / Warte auf Signal...";
            gridContainer.innerHTML = "";
            return;
        }

        // A) Daten filtern (Robust gegen fehlende Leerzeichen, z.B. "1.WL" vs "1. WL")
        let filteredData;
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

            headerBar.innerText = `${titleLauf} | ${activeClass}`;
        } else {
            // Das Gesamtergebnis ist ein eigener Lauf ("Gesamt" = beide
            // Wertungsläufe zusammen), nicht einfach alle Zeilen auf einmal -
            // sonst stünden Einzel- und Gesamtzeiten wild gemischt in einer Tabelle.
            filteredData = liveData.filter(d => vereinfacht(d.lauf) === "GESAMT");
            headerBar.innerText = `Gesamtergebnis (Alle Klassen)`;
        }
        if (lastUpdate) headerBar.innerText += `  ·  Stand ${lastUpdate}`;

        // B) AUTOMATISCHES SORTIEREN & PLATZIERUNG KORRIGIEREN
        // Nach Gesamtzeit sortieren (schnellste Zeit zuerst)
        filteredData.sort((a, b) => {
            return parseTimeToMs(a.zeit_total) - parseTimeToMs(b.zeit_total);
        });

        // Den Platz (1, 2, 3...) streng von oben nach unten neu durchnummerieren!
        filteredData.forEach((driver, index) => {
            driver.platz = index + 1;
        });

        // C) Tabellenkopf einfügen
        let html = `
            <div class="grid-header" style="text-align: center;">Platz</div>
            <div class="grid-header" style="text-align: center;">#</div>
            <div class="grid-header">Fahrer<br>Ortsclub</div>
            <div class="grid-header" style="text-align: right;">Zeit</div>
            <div class="grid-header-diff">Differenz<br>Intervall</div>
            <div class="grid-header gap-fill" style="grid-column: 3 / 5;"></div>
        `;

        if(filteredData.length === 0) {
            html += `<div style="grid-column: 1/5; padding: 20px; text-align: center; color: #666;">Noch keine Zeiten für diese Auswahl.</div>`;
            gridContainer.innerHTML = html;
            return;
        }

        // D) Fahrer-Zeilen & Differenzen generieren
        filteredData.forEach((driver) => {
            // Die eigentliche Fahrer-Zeile
            html += `
                <div class="driver-row">
                    <div class="driver-cell" style="text-align: center; font-weight: bold;">${driver.platz}</div>
                    <div class="driver-cell" style="text-align: center;">${escapeHtml(driver.startnummer)}</div>
                    <div class="driver-cell">
                        <div class="driver-name">${escapeHtml(driver.name)}</div>
                        <div class="driver-club">${escapeHtml(driver.club)}</div>
                    </div>
                    <div class="driver-cell time-cell">
                        ${escapeHtml(driver.zeit_raw)}<br>
                        ${driver.fehler ? escapeHtml(driver.fehler) + '<br>' : ''}
                        ${escapeHtml(driver.zeit_total)}
                    </div>
                </div>
            `;

            // Der Differenz-Kasten (wird bei JEDEM Fahrer direkt unter ihm angezeigt)
            html += `
                <div class="gap-row">
                    <div class="gap-cell" style="grid-column: 1 / 3;">
                        ${String(driver.platz) === "1" ? '00:00,00<br><br><br>' : `${escapeHtml(driver.diff_first)}<br>${escapeHtml(driver.diff_prev)}<br><br>`}
                    </div>
                    <div class="gap-empty" style="grid-column: 3 / 5;"></div>
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