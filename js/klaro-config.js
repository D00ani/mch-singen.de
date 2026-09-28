// js/klaro-config.js
var klaroConfig = {
    elementID: 'klaro',
    lang: 'de',
    default: false,
    acceptAll: true,
    
    // NEU: Diese globale Funktion wird ausgeführt, nachdem der Nutzer gespeichert hat
    callback: function(manager, service) {
        // Wenn der Nutzer die Einstellungen für Google Maps geändert hat, laden wir die Seite neu
        if (service === 'googleMaps') {
            location.reload();
        }
        // Wetter braucht kein Neuladen: index.js holt die Vorhersage direkt
        // nach (siehe onAccept beim Dienst "wetter").
    },

    translations: {
        de: {
            consentModal: {
                title: 'Datenschutz & Cookies',
                description: 'Wir nutzen auf dieser Website zwei externe Dienste: Google Maps für die Anfahrtskarten und Open-Meteo für die Wettervorhersage. Beide werden erst geladen, wenn du zustimmst.',
            },
            consentNotice: {
                description: 'Wir nutzen Google Maps für die Anfahrt und Open-Meteo für die Wettervorhersage. Beides lädt erst mit deiner Zustimmung.',
                learnMore: 'Einstellungen anpassen',
            },
            ok: 'Alles akzeptieren',
            decline: 'Ablehnen',
            googleMaps: {
                description: 'Anzeige von interaktiven Karten.',
            },
            wetter: {
                description: 'Wettervorhersage für Trainings- und Veranstaltungsorte.',
            },
            purposes: {
                functional: 'Funktionale Dienste',
            }
        }
    },
    services: [
        {
            name: 'googleMaps',
            default: false,
            title: 'Google Maps',
            purposes: ['functional'],
            // Falls die Zustimmung erteilt wird, wird beim nächsten Laden die Karte sofort angezeigt
            onAccept: (status) => {
                if (status === true && typeof window.loadGoogleMap === 'function') {
                    window.loadGoogleMap();
                }
            }
        },
        {
            // Wettervorhersage der Startseite. Open-Meteo setzt keine Cookies
            // und braucht keinen Schluessel - der Abruf uebertraegt aber die
            // IP-Adresse des Besuchers an einen Dritten. Deshalb steht er
            // hier und laeuft nicht mehr ungefragt beim Seitenaufruf.
            name: 'wetter',
            default: false,
            title: 'Wettervorhersage (Open-Meteo)',
            purposes: ['functional'],
            // Kein Neuladen noetig: js/index.js holt die Vorhersage sofort nach.
            onAccept: (status) => {
                if (status === true && typeof window.ladeWetter === 'function') {
                    window.ladeWetter();
                }
            }
        }
    ]
};

// Barrierefreiheit-Fix: Der Klaro-Dialog referenziert per aria-labelledby ein
// Element (id-cookie-title), das im Notice-Banner nicht existiert. Ohne
// zugänglichen Namen scheitert der Lighthouse-Audit "dialog has accessible name".
// Wir setzen daher direkt ein aria-label, sobald Klaro rendert.
document.addEventListener('DOMContentLoaded', function () {
    function fixKlaroDialogName() {
        document.querySelectorAll('[role="dialog"]').forEach(function (dialog) {
            var labelId = dialog.getAttribute('aria-labelledby');
            var labelEl = labelId ? document.getElementById(labelId) : null;
            if (!labelEl || !labelEl.textContent.trim()) {
                dialog.removeAttribute('aria-labelledby');
                dialog.setAttribute('aria-label', 'Cookie-Einstellungen');
            }
        });
    }
    // Klaro rendert asynchron ins DOM - Observer fängt Notice UND späteres Modal ab
    var klaroObserver = new MutationObserver(fixKlaroDialogName);
    klaroObserver.observe(document.body, { childList: true, subtree: true });
    fixKlaroDialogName();
});