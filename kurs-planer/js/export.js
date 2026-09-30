/*
 * PDF-Export: der ganze Platz auf einer DIN-A4-Seite, damit der Streckenplan
 * am Veranstaltungsort ausgehängt werden kann (Rahmenausschreibung 6.2 h).
 */
(function (KP) {
  'use strict';

  const PAGE_MARGIN = 10;      // mm
  const HEADER_HEIGHT = 10;    // mm
  const IMAGE_PIXELS = 3000;   // längere Bildkante, rund 270 dpi auf A4

  KP.buildPdf = function () {
    const plan = KP.editor.renderPlan(IMAGE_PIXELS);
    const field = KP.editor.field;
    const pdf = new window.jspdf.jsPDF({
      orientation: plan.widthMeters >= plan.heightMeters ? 'landscape' : 'portrait',
      unit: 'mm',
      format: 'a4'
    });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();

    // Bild so groß wie möglich unter die Kopfzeile setzen
    const mmPerMeter = Math.min(
      (pageWidth - 2 * PAGE_MARGIN) / plan.widthMeters,
      (pageHeight - 2 * PAGE_MARGIN - HEADER_HEIGHT) / plan.heightMeters
    );
    const width = plan.widthMeters * mmPerMeter;
    const height = plan.heightMeters * mmPerMeter;
    const left = (pageWidth - width) / 2;

    pdf.setFontSize(14);
    pdf.text('Streckenplan Kart-Slalom', left, PAGE_MARGIN + 5);
    pdf.setFontSize(9);
    pdf.text(
      'Platz ' + field.width + ' × ' + field.height + ' m  ·  1 Kästchen = 1 m  ·  Maßstab ca. 1:' +
        Math.round(1000 / mmPerMeter) + '  ·  Stand ' + new Date().toLocaleDateString('de-DE'),
      left + width, PAGE_MARGIN + 5, { align: 'right' }
    );
    pdf.addImage(plan.dataUrl, 'PNG', left, PAGE_MARGIN + HEADER_HEIGHT, width, height, undefined, 'FAST');
    return pdf;
  };

  document.getElementById('btn-export').addEventListener('click', () => {
    KP.buildPdf().save('streckenplan.pdf');
  });
})(window.KP);
