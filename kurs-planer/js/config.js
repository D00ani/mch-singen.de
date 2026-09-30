/*
 * Zentrale Maße aus der Rahmenausschreibung Bodensee-Kart-Cup (Stand 2025).
 * Alle Längen in Metern. Die Arbeitsfläche rechnet durchgehend in Metern,
 * erst die Stage-Skalierung macht daraus Pixel.
 *
 * Breiten und Pylonenabstände sind lichte Maße zwischen den Pylonenfüßen
 * (6.2 c: „bemessen an der Innenkante des Fußes“, 6.2 d: „ohne Abstand“ =
 * Fuß an Fuß).
 */
(function () {
  'use strict';

  const KP = window.KP = {};

  KP.RULES = Object.freeze({
    pylon: {
      height: 0.50,          // 6.2: 50 cm ± 3 cm
      heightTolerance: 0.03,
      foot: 0.30             // Kantenlänge des Fußes – Annahme, steht nicht im Regelwerk
    },
    gate: { min: 1.65, max: 2.00, preset: 1.80 },         // 6.2 c, Pylonentor
    lane: { min: 1.50, max: 2.50, minPylonsInRow: 3 },    // 6.2 c/d, gerade Spurgasse
    laneExtra: 0.40,                                      // Fahrspurbreite = Spurbreite + 40 cm
    figurePylonGap: 0.50,                                 // Ypsilon, S-Spurgasse, Z-Gasse, Kasten ...
    taskDistance: { min: 4, max: 10 },                    // 6.2 i, Abstand zwischen Aufgaben
    roundabout: { innerDiameter: 10, pylonGap: 1.0, entry: 3 },
    changeGate: { min: 1.5, max: 4, preset: 1.8 },        // Wechseltor, Abstand der Tore (Skizze: gleichmäßig)
    swissSlalom: { preset: 5 },                           // jede Pylone ist eine eigene Aufgabe (4–10 m)
    zLane: { minGap: 2, maxGap: 4, preset: 2.5 },         // Abstand zwischen den Gassen
    snailBox: 3,                                          // Schneckenhaus, Kastenbreite ca. 3 m
    finishLane: { width: 2.50, minLength: 8, maxLength: 10, pylonGap: 0.50 },
    courseMaxLength: 400                                  // 6.2 b
  });

  // Einstellungen, die der Veranstalter im Programm ändern kann.
  KP.settings = {
    trackWidth: 1.10         // Spurbreite des Karts – steht nicht im Regelwerk
  };
})();
