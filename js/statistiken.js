
document.addEventListener("DOMContentLoaded", () => {

    // --- ANIMIERTE MEILENSTEINE ---
    const easeOut = t => 1 - Math.pow(1 - t, 3);

    // Jahreszahlen werden nicht hochgezaehlt. "Gegruendet" ist ein Datum,
    // keine Menge - ein von 0 auf 1954 laufender Zaehler las sich wie eine
    // Mitgliederzahl und wirkte dadurch unseriös.
    const istJahreszahl = (el) => el.hasAttribute('data-mode')
        ? el.getAttribute('data-mode') === 'year'
        : /^(19|20)\d{2}$/.test(el.getAttribute('data-target') || '');

    const animateCounter = (counter) => {
        const target = +counter.getAttribute('data-target');
        const suffix = counter.getAttribute('data-suffix') || '';

        if (istJahreszahl(counter)) {
            counter.textContent = target + suffix;
            return;
        }

        const duration = Math.min(1800, 600 + target * 0.4);
        const start = performance.now();
        const tick = (now) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            counter.textContent = Math.round(easeOut(progress) * target) + suffix;
            if (progress < 1) requestAnimationFrame(tick);
            else counter.textContent = target + suffix;
        };
        requestAnimationFrame(tick);
    };

    const milestoneObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) { animateCounter(entry.target); obs.unobserve(entry.target); }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('.milestone-number').forEach(c => {
        // Im HTML steht der echte Wert, damit ohne JavaScript keine "0"
        // stehenbleibt. Fuer die Animation wird er hier zurueckgesetzt -
        // sonst zeigt die Kachel beim Heranscrollen erst die Endzahl und
        // springt dann sichtbar auf 0 zurueck.
        if (!istJahreszahl(c)) c.textContent = '0';
        milestoneObserver.observe(c);
    });

    // --- DIAGRAMME ---
    const FONT = "'Outfit', system-ui, sans-serif";

    // Fallback-Werte, falls data/statistik.json nicht erreichbar ist.
    // Gepflegt werden die Zahlen ueber tools/statistiken_pflege.py in der JSON -
    // dadurch ist bei einer Aenderung KEIN Build-Schritt noetig.
    const CHART_DEFS = [
        { id: 'chartCurrent', data: [5, 6, 4] },
        { id: 'chartGesamt',  data: [121, 112, 115] },
        { id: 'chart2025',    data: [14, 12, 23] },
    ];

    const PODIUM = {
        bg:     ['rgba(255,204,0,0.90)', 'rgba(0,71,204,0.85)',  'rgba(66,133,244,0.75)'],
        border: ['#c8a000',              '#0033a0',               '#2a6bd6'],
    };

    // Rennpodium-Reihenfolge: links 2., Mitte 1., rechts 3.
    const PODIUM_ORDER  = [1, 0, 2];
    const PODIUM_LABELS = ['2. Platz', '1. Platz', '3. Platz'];

    // Werte über den Balken. Gezeichnet wird nicht gleich der Endwert,
    // sondern der Wert, den der Balken gerade erreicht hat - so zaehlt die
    // Zahl mit dem wachsenden Balken hoch, statt von Anfang an fertig
    // ueber einem halb hohen Balken zu stehen.
    const topLabelPlugin = {
        id: 'topLabel',
        afterDatasetsDraw(chart) {
            const { ctx } = chart;
            const skala = chart.scales.y;
            const isDark = document.body.classList.contains('dark-mode');
            chart.data.datasets[0].data.forEach((val, i) => {
                const bar = chart.getDatasetMeta(0).data[i];
                const erreicht = Math.round(skala.getValueForPixel(bar.y));
                ctx.save();
                // Der Wert ueber dem Balken ist eine reine Zahl - hier bleibt
                // Orbitron, etwas groesser, damit er als Wert lesbar ist.
                ctx.fillStyle = isDark ? '#e8ecf8' : '#26292f';
                ctx.font = `700 14px 'Orbitron', sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillText(Math.max(0, Math.min(val, erreicht)), bar.x, bar.y - 5);
                ctx.restore();
            });
        }
    };

    function renderPodiumTotal(id, data) {
        const el = document.getElementById(id + '-total');
        if (!el) return;
        const total = data.reduce((a, b) => a + b, 0);
        el.innerHTML =
            `Gesamt <strong>${total}</strong> Podien &nbsp;&mdash;&nbsp;` +
            `<span class="podium-badge podium-gold">${data[0]}&times; 1.</span>` +
            `<span class="podium-badge podium-silver">${data[1]}&times; 2.</span>` +
            `<span class="podium-badge podium-bronze">${data[2]}&times; 3.</span>`;
    }

    const chartInstances = {};

    // animiert = false: nur neu einfaerben (Dark-Mode), ohne dass die
    // Balken noch einmal von 0 hochfahren.
    function buildChart({ id, data }, animiert = true) {
        const canvas = document.getElementById(id);
        if (!canvas) return;

        if (chartInstances[id]) { chartInstances[id].destroy(); }

        renderPodiumTotal(id, data);

        const isDark = document.body.classList.contains('dark-mode');

        // Neutrale Rasterfarben statt blau eingefaerbter - wie im uebrigen
        // Design auch. Ein blaustichiges Gitter konkurriert mit den Balken.
        const gridColor   = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(15,23,42,0.07)';
        const tickColor   = isDark ? '#8b93ad'                : '#555b66';
        const axisColor   = isDark ? 'rgba(255,255,255,0.10)' : 'rgba(15,23,42,0.12)';
        const tooltipBg   = isDark ? '#16203a'                : '#ffffff';
        const tooltipTitle= isDark ? '#ffffff'                : '#001b5e';
        const tooltipBody = isDark ? '#aaa'                   : '#555555';
        const tooltipBord = isDark ? 'rgba(66,133,244,0.3)'   : 'rgba(0,71,204,0.2)';

        chartInstances[id] = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            plugins: [topLabelPlugin],
            data: {
                labels: PODIUM_LABELS,
                datasets: [{
                    data: PODIUM_ORDER.map(i => data[i]),
                    backgroundColor: PODIUM_ORDER.map(i => PODIUM.bg[i]),
                    borderColor: PODIUM_ORDER.map(i => PODIUM.border[i]),
                    // Vorher 2px Rahmen und scharfe Ecken. Der Rahmen machte
                    // die Balken schwer, die scharfen Ecken passten nicht zu
                    // den abgerundeten Karten der uebrigen Seite.
                    borderWidth: 0,
                    borderRadius: { topLeft: 6, topRight: 6 },
                    borderSkipped: 'bottom',
                    maxBarThickness: 120,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 24 } },
                // Gestaffelt wird nur der erste Aufbau (Podest-Reihenfolge).
                // Ohne die Abfrage galt die Verzoegerung auch fuer jeden
                // Hover-Effekt, der dadurch bis zu 0,6 s hinterherhing.
                animation: animiert ? {
                    delay(ctx) {
                        return ctx.type === 'data' && ctx.mode === 'default'
                            ? [1, 0, 2][ctx.dataIndex] * 300 : 0;
                    },
                    duration: 800,
                    easing: 'easeOutQuart',
                } : false,
                scales: {
                    x: {
                        border: { color: axisColor },
                        grid: { display: false },
                        ticks: {
                            color: tickColor,
                            // "1. Platz" ist Text, keine Zahl -> Fliesstext-Schrift.
                            // Orbitron bleibt den reinen Ziffern vorbehalten.
                            font: { family: FONT, size: 12, weight: '600' },
                        }
                    },
                    y: {
                        beginAtZero: true,
                        border: { display: false },
                        grid: { color: gridColor },
                        ticks: {
                            stepSize: 1,
                            color: tickColor,
                            font: { family: FONT, size: 11 },
                            padding: 6,
                        }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: tooltipBg,
                        titleColor:      tooltipTitle,
                        bodyColor:       tooltipBody,
                        borderColor:     tooltipBord,
                        borderWidth:     1,
                        padding:         12,
                        cornerRadius:    8,
                        displayColors:   false,
                        titleFont: { family: FONT, size: 13, weight: '700' },
                        bodyFont:  { family: FONT, size: 12 },
                        callbacks: {
                            label(item) { return `  ${item.raw}× erreicht`; }
                        }
                    }
                }
            }
        });
    }

    // Werte aus /data/statistik.json nachladen:
    //   podium -> "Dieses Jahr (Bisher)", erzeugt aus der BKC-Wertungs-PDF
    //             (tools/update_statistik.py)
    //   charts -> die uebrigen Diagramme, gepflegt per tools/statistiken_pflege.py
    function uebernehmen(def, daten) {
        if (!Array.isArray(daten) || daten.length !== 3) return;
        if (daten.every((wert, i) => wert === def.data[i])) return;  // unveraendert
        def.data = daten;
        // Nur neu zeichnen, wenn das Diagramm schon steht (die Datei kam
        // erst nach der Wartezeit unten) - sonst uebernimmt es die neuen
        // Zahlen ohnehin beim ersten Aufbau.
        if (chartInstances[def.id]) buildChart(def);
    }

    const datenGeladen = fetch('../data/statistik.json')
        .then(res => res.ok ? res.json() : null)
        .then(stat => {
            if (!stat) return;
            const current = CHART_DEFS.find(c => c.id === 'chartCurrent');
            if (current && stat.podium) {
                uebernehmen(current, [stat.podium.platz1, stat.podium.platz2, stat.podium.platz3]);
            }
            (stat.charts || []).forEach(({ id, data }) => {
                const def = CHART_DEFS.find(c => c.id === id);
                if (def) uebernehmen(def, data);
            });
        })
        .catch(() => {}); // nicht erreichbar -> die Ausweichzahlen oben bleiben stehen

    // Gezeichnet wird erst, wenn die JSON da ist. Vorher fuhren die Balken
    // sofort mit den Ausweichzahlen hoch; kam die JSON mit den echten
    // Werten, begann die Animation von vorn - die Zahlen stimmten
    // zwischendurch nicht und die Balken liefen zweimal hoch.
    // Damit die Diagramme nicht wie frueher dauerhaft leer bleiben, wenn
    // die Datei haengt, wird nach spaetestens 1,5 s trotzdem gezeichnet
    // (Ausweichzahlen). Lokal per Doppelklick geoeffnet schlaegt fetch
    // sofort fehl - dann geht es ohne Wartezeit los.
    const datenBereit = Promise.race([
        datenGeladen,
        new Promise(fertig => setTimeout(fertig, 1500)),
    ]);

    const chartObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            obs.unobserve(entry.target);
            const def = CHART_DEFS.find(c => c.id === entry.target.id);
            if (def) datenBereit.then(() => buildChart(def));
        });
    }, { threshold: 0.15 });

    CHART_DEFS.forEach(({ id }) => {
        const el = document.getElementById(id);
        if (el) chartObserver.observe(el);
    });

    // Charts bei Dark-Mode-Umschalten neu einfaerben.
    // Der Beobachter meldet JEDE Klassenaenderung am <body> - auch
    // 'transitions-ready', das js/main.js kurz nach dem Laden setzt.
    // Frueher wurden die Diagramme dadurch mitten in der Animation neu
    // aufgebaut und die Balken fuhren ein zweites Mal von 0 hoch. Darum
    // nur reagieren, wenn der Dark-Mode wirklich gewechselt hat.
    let warDunkel = document.body.classList.contains('dark-mode');
    new MutationObserver(() => {
        const istDunkel = document.body.classList.contains('dark-mode');
        if (istDunkel === warDunkel) return;
        warDunkel = istDunkel;
        CHART_DEFS.forEach(def => {
            if (chartInstances[def.id]) buildChart(def, false);
        });
    }).observe(document.body, { attributes: true, attributeFilter: ['class'] });

    // --- DATENSCHUTZ: Namen abkürzen ---
    document.querySelectorAll('.stats-table').forEach(table => {
        let col = -1;
        table.querySelectorAll('thead th').forEach((th, i) => {
            if (['fahrer/in', 'gewinner/in'].includes(th.textContent.trim().toLowerCase())) col = i;
        });
        if (col < 0) return;
        table.querySelectorAll('tbody tr').forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length <= col) return;
            const name = cells[col].textContent.trim();
            if (name.includes(' ') && !name.endsWith('.')) {
                const parts = name.split(' ');
                const last = parts.pop();
                cells[col].textContent = parts.join(' ') + ' ' + last.charAt(0) + '.';
            }
        });
    });

    // --- HANDY: PLATZ ALS GELBE TAFEL ---
    // Am Handy steht die Platzierung der Top-Platzierungen als kleine gelbe
    // Tafel (css/unterseiten-handy.css, Abschnitt 10). Dafuer wird "Platz"
    // abgetrennt und nur noch fuer Vorleseprogramme gefuehrt - in der Tafel
    // steht "1.". Am Desktop ist das Wort weiter zu sehen.
    document.querySelectorAll('table.ergebnis-tabelle tbody td:nth-child(5)').forEach(zelle => {
        const ziel = zelle.querySelector('strong') || zelle;
        const treffer = ziel.textContent.trim().match(/^(\d+\.)\s*(Platz)$/);
        if (!treffer) return;
        const wort = document.createElement('span');
        wort.className = 'platz-wort';
        wort.textContent = ` ${treffer[2]}`;
        ziel.textContent = treffer[1];
        ziel.appendChild(wort);
    });
});
