        // --- 3. FORMULAR LOGIK ---
        const contactForm = document.getElementById('my-contact-form');
        const successBox = document.getElementById('success-message');

        const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$/;

        if (contactForm) {
            const emailInput = document.getElementById('email');
            const emailConfirm = document.getElementById('email-confirm');
            const emailError = document.getElementById('email-error');
            const emailFormatError = document.getElementById('email-format-error');
            const sendeFehler = document.getElementById('sende-fehler');

            // Meldung ein- oder ausblenden und das zugehoerige Feld als
            // fehlerhaft markieren. aria-invalid steuert gleichzeitig die rote
            // Kante (siehe style.css) und das, was Screenreader vorlesen -
            // beides bleibt so zwangslaeufig synchron.
            function meldung(el, feld, zeigen) {
                if (el) el.hidden = !zeigen;
                if (feld) {
                    if (zeigen) feld.setAttribute('aria-invalid', 'true');
                    else feld.removeAttribute('aria-invalid');
                }
            }

            function validateEmail() {
                const val = emailInput.value;
                const isValidFormat = emailRegex.test(val);
                meldung(emailFormatError, emailInput, !!val && !isValidFormat);
                const matches = val === emailConfirm.value;
                meldung(emailError, emailConfirm, !!emailConfirm.value && !matches);
                return isValidFormat && matches;
            }

            function formatPruefen() {
                const val = emailInput.value;
                if (val) meldung(emailFormatError, emailInput, !emailRegex.test(val));
            }

            function gleichheitPruefen() {
                if (emailConfirm.value) {
                    meldung(emailError, emailConfirm, emailInput.value !== emailConfirm.value);
                }
            }

            emailInput.addEventListener('blur', formatPruefen);
            emailInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') formatPruefen();
            });
            // Tippt jemand nach einem Fehler weiter, verschwindet die Meldung
            // sofort wieder - sonst steht sie rot da, waehrend man sie behebt.
            emailInput.addEventListener('input', function() {
                if (emailInput.getAttribute('aria-invalid') === 'true' && emailRegex.test(emailInput.value)) {
                    meldung(emailFormatError, emailInput, false);
                }
            });

            emailConfirm.addEventListener('blur', gleichheitPruefen);
            emailConfirm.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') gleichheitPruefen();
            });
            emailConfirm.addEventListener('input', function() {
                if (emailConfirm.getAttribute('aria-invalid') === 'true' && emailInput.value === emailConfirm.value) {
                    meldung(emailError, emailConfirm, false);
                }
            });

            contactForm.addEventListener('submit', function(e) {
                e.preventDefault();
                if (sendeFehler) sendeFehler.hidden = true;

                if (!validateEmail()) {
                    // Zum ersten fehlerhaften Feld springen, nicht pauschal
                    // ins Bestaetigungsfeld: sonst landet man beim falschen.
                    if (!emailRegex.test(emailInput.value)) {
                        meldung(emailFormatError, emailInput, true);
                        emailInput.focus();
                    } else {
                        meldung(emailError, emailConfirm, true);
                        emailConfirm.focus();
                    }
                    return;
                }

                const submitBtn = contactForm.querySelector('button[type="submit"]');
                const originalBtnText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Wird gesendet...';
                submitBtn.disabled = true;

                const formData = new FormData(contactForm);
                formData.delete('_email_confirm');

                // Fehler stehen jetzt im Formular statt in einem alert().
                // Ein Systemdialog reisst aus dem Ablauf, verdeckt das
                // Formular und nennt keinen Ausweg.
                function fehlgeschlagen(text) {
                    if (sendeFehler) {
                        sendeFehler.textContent = text;
                        sendeFehler.hidden = false;
                    }
                    submitBtn.innerHTML = originalBtnText;
                    submitBtn.disabled = false;
                }

                fetch(contactForm.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Accept': 'application/json'
                    }
                })
                .then(response => {
                    if (response.ok) {
                        contactForm.style.display = 'none';
                        successBox.style.display = 'block';
                    } else {
                        fehlgeschlagen('Die Nachricht konnte nicht gesendet werden. '
                            + 'Bitte versuche es noch einmal oder schreib uns direkt '
                            + 'an info@mch-singen.de.');
                    }
                })
                .catch(() => {
                    fehlgeschlagen('Keine Verbindung zum Server. Bitte prüfe deine '
                        + 'Internetverbindung und versuche es erneut. Alternativ '
                        + 'erreichst du uns unter info@mch-singen.de.');
                });
            });
        }
        // NEU: Funktion zum einfachen Schließen der Danke-Box
        function closeSuccess() {
            successBox.style.display = 'none';
            contactForm.style.display = 'flex';
            contactForm.reset();
        }