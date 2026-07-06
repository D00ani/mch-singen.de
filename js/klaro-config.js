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