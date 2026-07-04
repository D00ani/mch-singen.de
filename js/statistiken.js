
document.addEventListener("DOMContentLoaded", () => {

    // --- ANIMIERTE MEILENSTEINE ---
    const easeOut = t => 1 - Math.pow(1 - t, 3);

    const animateCounter = (counter) => {
        const target = +counter.getAttribute('data-target');
        const suffix = counter.getAttribute('data-suffix') || '';
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

    document.querySelectorAll('.milestone-number').forEach(c => milestoneObserver.observe(c));

    // --- DIAGRAMME ---
    const FONT = "'Outfit', system-ui, sans-serif";

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

    // Werte über den Balken
    const topLabelPlugin = {
        id: 'topLabel',
        afterDatasetsDraw(chart) {
            const { ctx } = chart;
            const isDark = document.body.classList.contains('dark-mode');
            chart.data.datasets[0].data.forEach((val, i) => {
                const bar = chart.getDatasetMeta(0).data[i];
                ctx.save();
                ctx.fillStyle = isDark ? '#e0e0e0' : '#333';
                ctx.font = `700 12px 'Orbitron', sans-serif`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                ctx.fillText(val, bar.x, bar.y - 5);
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

    function buildChart({ id, data }) {
        const canvas = document.getElementById(id);
        if (!canvas) return;

        if (chartInstances[id]) { chartInstances[id].destroy(); }

        renderPodiumTotal(id, data);

        const isDark = document.body.classList.contains('dark-mode');

        const gridColor   = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,71,204,0.07)';
        const tickColor   = isDark ? '#888'                   : '#666';
        const axisColor   = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,71,204,0.1)';
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
                    borderWidth: 2,
                    borderRadius: 0,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 24 } },
                animation: {
                    delay(ctx) { return [1, 0, 2][ctx.dataIndex] * 300; },
                    duration: 800,
                    easing: 'easeOutQuart',
                },
                scales: {
                    x: {
                        border: { color: axisColor },
                        grid: { display: false },
                        ticks: {
                            color: tickColor,
                            font: { family: "'Orbitron', sans-serif", size: 11, weight: '600' },
                        }
                    },
                    y: {
                        beginAtZero: true,
                        border: { color: axisColor, dash: [4, 4] },
                        grid: { color: gridColor },
                        ticks: {
                            stepSize: 1,
                            color: tickColor,
                            font: { family: "'Orbitron', sans-serif", size: 11 },
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

    // Chart erst wenn sichtbar initialisieren
    const chartObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const def = CHART_DEFS.find(c => c.id === entry.target.id);
            if (def) { buildChart(def); obs.unobserve(entry.target); }
        });
    }, { threshold: 0.15 });

    CHART_DEFS.forEach(({ id }) => {
        const el = document.getElementById(id);
        if (el) chartObserver.observe(el);
    });

    // Charts bei Dark-Mode-Umschalten neu rendern
    new MutationObserver(() => {
        CHART_DEFS.forEach(def => {
            if (chartInstances[def.id]) buildChart(def);
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
});
