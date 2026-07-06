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
    },

    translations: {
        de: {
            consentModal: {
                title: 'Datenschutz & Cookies',
                description: 'Wir nutzen auf dieser Website externe Dienste (wie Google Maps), um dir zusätzliche Funktionen anzubieten.',
            },
            consentNotice: {
                description: 'Wir nutzen Cookies und Google Maps, um unsere Webseite optimal für dich zu gestalten.',
                learnMore: 'Einstellungen anpassen',
            },
            ok: 'Alles akzeptieren',
            decline: 'Ablehnen',
            googleMaps: {
                description: 'Anzeige von interaktiven Karten.',
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
    // Klaro rendert asynchron ins DOM — Observer fängt Notice UND späteres Modal ab
    var klaroObserver = new MutationObserver(fixKlaroDialogName);
    klaroObserver.observe(document.body, { childList: true, subtree: true });
    fixKlaroDialogName();
});