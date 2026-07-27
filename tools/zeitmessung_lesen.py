# -*- coding: utf-8 -*-
"""
Liest die Ergebnistabelle des Zeitmessungs-Programms "Zeitmessung_Kart".

Die Zeitmessung legt ihre Ergebnisse in einer Access-Datenbank ab
(Tabelle "Laufergebnisse"). Dieses Modul holt sie dort NUR LESEND ab -
weder das Programm noch seine Datenbank werden veraendert.

Zugriffsweg: Windows bringt den Access-Treiber (Microsoft ACE OLEDB) bereits
mit, den auch die Zeitmessung selbst benutzt. Angesprochen wird er ueber
PowerShell, damit keinerlei Zusatzpakete installiert werden muessen.
Weil die Zeitmessung als 32-Bit-Programm laeuft, ist der Treiber auf manchen
Rechnern nur in der 32-Bit-Fassung vorhanden - deshalb werden nacheinander
64-Bit- und 32-Bit-PowerShell probiert.
"""
import json
import os
import shutil
import subprocess
import tempfile

# Spalten der Tabelle "Laufergebnisse", so wie envDB.LaufergebnisseSave sie
# befuellt (siehe Zeitmessung_Kart/envDB.vb).
SPALTEN = [
    ("Datum", "datum"),
    ("Uhrzeit", "uhrzeit"),
    ("StarterNr", "starternr"),
    ("StarterName", "name"),
    ("Klasse", "klasse"),
    ("Verein", "verein"),
    ("LaufNr", "laufnr"),
    ("Fahrzeit", "fahrzeit"),
    ("Pylonen", "pylonen"),
    ("ADW", "adw"),
    ("Strafzeit", "strafzeit"),
    ("Gesamtzeit", "gesamtzeit"),
]

FELDER = [ziel for _, ziel in SPALTEN]


class LeseFehler(Exception):
    """Die Datenbank konnte nicht gelesen werden."""


# ------------------------------------------------------------------
# PowerShell-Skript, das die Tabelle als JSON herausschreibt
# ------------------------------------------------------------------

_ZUWEISUNGEN = "\n".join(
    f"            {ziel:<11}= [string]$z['{quelle}']" for quelle, ziel in SPALTEN
)

_PS_SKRIPT = """
param([Parameter(Mandatory=$true)][string]$Datenbank,
      [Parameter(Mandatory=$true)][string]$Ziel)

$ErrorActionPreference = 'Stop'

$spalten  = '%(spalten)s'
$tabelle  = $null
$probleme = @()

# ACE 16 zuerst (neuere Office-Installationen), sonst ACE 12.
foreach ($provider in @('Microsoft.ACE.OLEDB.16.0', 'Microsoft.ACE.OLEDB.12.0')) {
    $verbindung = $null
    try {
        $verbindung = New-Object System.Data.OleDb.OleDbConnection(
            "Provider=$provider;Data Source=$Datenbank;Mode=Read")
        $verbindung.Open()
        $adapter = New-Object System.Data.OleDb.OleDbDataAdapter(
            "SELECT $spalten FROM Laufergebnisse", $verbindung)
        $tabelle = New-Object System.Data.DataTable
        [void]$adapter.Fill($tabelle)
        break
    } catch {
        $probleme += ("{0}: {1}" -f $provider, $_.Exception.Message)
        $tabelle = $null
    } finally {
        if ($verbindung -and $verbindung.State -eq 'Open') { $verbindung.Close() }
    }
}

if ($null -eq $tabelle) { throw ($probleme -join ' | ') }

$zeilen = New-Object System.Collections.ArrayList
foreach ($z in $tabelle.Rows) {
    [void]$zeilen.Add([ordered]@{
%(zuweisungen)s
    })
}

$json = ConvertTo-Json -InputObject @{ zeilen = $zeilen.ToArray() } -Depth 4
[System.IO.File]::WriteAllText($Ziel, $json, (New-Object System.Text.UTF8Encoding($false)))
""" % {"spalten": ",".join(quelle for quelle, _ in SPALTEN), "zuweisungen": _ZUWEISUNGEN}


def _powershell_kandidaten():
    """PowerShell-Varianten in der Reihenfolge, in der sie probiert werden.
    Die 32-Bit-Fassung zum Schluss - sie rettet Rechner, auf denen nur der
    32-Bit-Access-Treiber installiert ist (so laeuft auch die Zeitmessung)."""
    windows = os.environ.get("SystemRoot", r"C:\Windows")
    kandidaten = [
        shutil.which("pwsh"),
        os.path.join(windows, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
        os.path.join(windows, "SysWOW64", "WindowsPowerShell", "v1.0", "powershell.exe"),
    ]
    return [k for k in kandidaten if k and os.path.isfile(k)]


def _skript_ausfuehren(powershell, skriptdatei, db_pfad, ausgabedatei):
    ergebnis = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", skriptdatei, "-Datenbank", db_pfad, "-Ziel", ausgabedatei],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if ergebnis.returncode != 0 or not os.path.isfile(ausgabedatei):
        meldung = (ergebnis.stderr or ergebnis.stdout or "").strip()
        raise LeseFehler(meldung or f"{os.path.basename(powershell)} meldete Fehlercode "
                                    f"{ergebnis.returncode}")


def lies_laufergebnisse(db_pfad):
    """Gibt alle Zeilen der Tabelle "Laufergebnisse" als Liste von dicts
    zurueck (Schluessel siehe FELDER). Loest LeseFehler aus, wenn die
    Datenbank nicht erreichbar ist."""
    db_pfad = os.path.abspath(db_pfad)
    if not os.path.isfile(db_pfad):
        raise LeseFehler(f"Datenbank nicht gefunden: {db_pfad}")

    powershells = _powershell_kandidaten()
    if not powershells:
        raise LeseFehler("Keine PowerShell gefunden - ohne sie kann die "
                         "Access-Datenbank nicht gelesen werden.")

    arbeitsordner = tempfile.mkdtemp(prefix="mch-livetiming-")
    skriptdatei = os.path.join(arbeitsordner, "lies_zeitmessung.ps1")
    ausgabedatei = os.path.join(arbeitsordner, "laufergebnisse.json")
    try:
        with open(skriptdatei, "w", encoding="utf-8-sig", newline="\r\n") as f:
            f.write(_PS_SKRIPT)

        probleme = []
        for powershell in powershells:
            try:
                _skript_ausfuehren(powershell, skriptdatei, db_pfad, ausgabedatei)
                break
            except LeseFehler as fehler:
                probleme.append(f"{os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(powershell))))}"
                                f"/{os.path.basename(powershell)}: {fehler}")
        else:
            raise LeseFehler(" || ".join(probleme))

        with open(ausgabedatei, encoding="utf-8") as f:
            roh = json.load(f)
    finally:
        shutil.rmtree(arbeitsordner, ignore_errors=True)

    return _vereinheitliche(roh.get("zeilen"))


def _vereinheitliche(zeilen):
    """PowerShell macht aus einer einzelnen Zeile kein Array und aus einer
    leeren Tabelle null - beides hier geradebiegen."""
    if zeilen is None:
        zeilen = []
    elif isinstance(zeilen, dict):
        zeilen = [zeilen]

    sauber = []
    for zeile in zeilen:
        sauber.append({feld: (zeile.get(feld) or "").strip() for feld in FELDER})
    return sauber
