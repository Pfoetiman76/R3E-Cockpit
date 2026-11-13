# R3E Cockpit

Schlanker Launcher für das R3E-Ökosystem und weitere Simracing-Programme — im Stil von PitBoss R3E (dunkles Theme, Türkis-Akzent).

## Enthaltene Kacheln

### HidHide · Simracing-Geräte verstecken (ab v0.4.0)
Über die Kopfzeilen-Schaltfläche „HidHide“ lässt sich das komplette Simracing-Equipment
(Lenkradbasis, Pedale, Shifter, …) dauerhaft für alle anderen Programme unsichtbar
schalten — automatisch über die mitgelieferte `HidHideCLI.exe` der
[HidHide](https://docs.nefarius.at/projects/HidHide/)-Treiberlösung von Nefarius.

Funktionsweise:

1. **Cloaking dauerhaft aktiv:** Versteckte Geräte sind für alle Programme unsichtbar,
   außer für die freigegebenen Anwendungen auf der HidHide-Whitelist. Wenn Sie nicht
   fahren, sieht kein Programm Ihr Equipment — ein Ein-/Ausschalten pro Fahrt ist nicht
   nötig.
2. **Geräte suchen:** Der Dialog listet alle angeschlossenen Gaming-Geräte
   (`--dev-gaming`, JSON-Inventar). Pro Gerät werden automatisch alle nötigen
   Instanzpfade versteckt: bei normalen HID-Geräten (Lenkrad, Pedale) nur der
   `HID\…`-Pfad, bei XInput-Geräten zusätzlich USB-Basis-Container und XUSB-Knoten
   (bekannte Umgehung, die das grafische HidHide-Tool nicht zuverlässig schafft).
3. **Whitelist:** SimHub, CrewChief, PitBoss R3E & Co. per Häkchen freigeben.
   RaceRoom startet über Steam — dessen `RRRE.exe` (z. B.
   `…\steamapps\common\raceport\RRRE.exe`) bitte im Feld „Zusätzliche EXE-Pfade“
   eintragen, sonst sieht RaceRoom das Equipment nicht.
4. **Anwenden:** Ein Klick schreibt Hide-Liste, Whitelist und Cloaking-Zustand in
   einem Aufruf an den Treiber (`--inv-off --dev-hide … --app-reg … --cloak-on`) und
   speichert die Konfiguration in `launcher.json`. „Status anzeigen“ zeigt den
   aktuellen Treiberzustand (Cloak-State, Listen).

Wichtige Hinweise:

- Der **HidHide Configuration Client muss geschlossen** sein, wenn der Cockpit die
  CLI aufruft (nur ein Prozess darf den Treiber gleichzeitig öffnen).
- Nach dem ersten Verstecken bitte das Equipment **kurz ab- und wieder anstecken**
  (oder Windows neu starten), damit der Filter greift.
- Die Einstellungen bleiben dauerhaft; ein Rechnerneustart ändert sie nicht.

### Programmverwaltung (ab v0.3.2)
Über die Kopfzeilen-Schaltfläche „⚙ Programme" lassen sich Einträge bearbeiten,
neue Programme hinzufügen und bestehende entfernen. Es gilt dieselbe Pfadlogik
wie bei den Startprofilen: EXE-Dateien oder `steam://`-Links, Anführungszeichen
werden automatisch entfernt. Neue oder geänderte Kacheln erscheinen nach dem
nächsten Start des Cockpits. Systemeinträge (z. B. RaceRoom) können mit
Sicherheitsabfrage gelöscht werden.

### Taskleisten-Icon (ab v0.3.2)
Das Fenster- und Taskleisten-Icon (assets/cockpit.ico, erzeugt von
scripts/make_icon.py) wird im Release-Build per PyInstaller `--add-data` neben
die EXE gepackt und über eine AppUserModelID korrekt zugeordnet, damit Windows
nicht das Standard-Python-Icon zeigt.

**R3E-Ökosystem** (mit Statusprüfung):
- PitBoss R3E
- R3E-Resultate (zeigt Sitzungsanzahl aus results.db — ausschließlich lesend)
- Setup-Coach (Platzhalter bis zur ersten Version)

**Weitere Programme:**
- RaceRoom Racing Experience (Start über Steam)
- SimHub
- CrewChief
- Simucube Tuner
- Conspit Link 2.0

**Links:**
- RaceRoom Wettbewerbe (https://game.raceroomracing.com/competitions/)

## Installation

1. Auf der GitHub-Releases-Seite die neueste Version herunterladen: `R3ECockpit-Setup-*.exe`.
2. Falls Windows den Sperrhinweis zeigt: Rechtsklick auf die Datei → Eigenschaften → Häkchen „Zulassen“.
3. Installer starten und den Anweisungen folgen (Standardordner: Eigene Programme\R3E Cockpit; optional Desktop-Verknüpfung).
4. Über Startmenü oder Desktop starten. Beim ersten Start wird automatisch eine `launcher.json` im Programmordner angelegt.

Hinweis: Ausgeliefert wird wie bei PitBoss R3E ein Inno-Setup-Installationsprogramm; die App liegt danach als Ordner (Onedir) und startet sofort ohne das kurze schwarze Entpack-Fenster des Onefile-Modus.

## Automatisches Update

Der Cockpit prüft 1,5 Sekunden nach dem Start automatisch die GitHub-Releases. Liegt eine neuere Version vor, erscheint oben rechts der rote Button „v… herunterladen“:

1. Button anklicken → Herunterladen bestätigen.
2. Der Cockpit lädt den Installer, schließt sich und startet die Installation; danach einfach den Cockpit neu starten.

Schlägt die Prüfung fehl (GitHub gerade nicht erreichbar), zeigt der Button dies an — der Cockpit läuft sonst ganz normal weiter. Manuell geht es immer über die Releases-Seite.

## Profile anpassen

Jedes Startprofil („Rennabend“, „Analyse“) hat rechts einen eigenen Bearbeiten-Knopf (⚙). Er öffnet ein Menü mit allen Programmen als Auswahlkästchen:

- Haken gesetzt = das Profil startet dieses Programm.
- „Speichern“ schreibt die Auswahl in die `launcher.json`.

### Eigene Profile (ab v0.3.3)
- Knopf „＋ Profil“ in der Profilzeile: Namen eingeben, fertig — das neue Profil erscheint beim nächsten Start mit eigenem roten Start-Button und ⚙-Menü.
- Im ⚙-Menü jedes Profils gibt es zusätzlich „Umbenennen“ und „Löschen“ (mit Sicherheitsabfrage).
- Änderungen an Namen und neue Profile erscheinen erst nach dem nächsten Start des Cockpits, die Programmauswahl wirkt sofort.

## Erste Einrichtung

Die App versucht, Installationspfade automatisch zu erkennen. Kacheln ohne gefundenen Pfad zeigen den Button **„Pfad festlegen“**:

1. Klick auf „Pfad festlegen“.
2. EXE-Datei des Programms auswählen.
3. Pfad wird in `launcher.json` gespeichert und die Kachel zeigt „bereit“.

Die `launcher.json` kann auch direkt editiert werden (UTF-8, JSON). Jeder Eintrag hat: `id`, `name`, `group`, `path`, `process` (Prozessname für die Läuft-Prüfung, Standard: Dateiname des Pfads), optional `args` (Startparameter) und `search_hints` (automatische Pfad-Vorschläge). Die HidHide-Sektion (`cli_path`, `hidden`, `whitelist_apps`, `extra_whitelist`, `cloak`) wird vom HidHide-Dialog verwaltet.

## Architektur-Grundsätze

- Der Launcher **besitzt selbst nur** `launcher.json` — keine App schreibt in Dateien anderer Apps (konsistent mit dem R3E-Datenkonzept).
- Statusprüfung ausschließlich lesend: `tasklist` (Prozesse), Dateiexistenz, `results.db` im SQLite-Lesemodus (Eigentümer bleibt R3E-Resultate).
- Konfiguration wird atomar geschrieben (`.tmp` + Ersetzen).
- HidHide-Änderungen gehen ausschließlich über die offizielle `HidHideCLI.exe`; der Cockpit erweitert die Treiberlisten, ohne fremde Einträge zu entfernen.

## Voraussetzungen für HidHide

- Installiertes HidHide (https://www.nefarius.at/projects/HidHide/) — der Cockpit findet die `HidHideCLI.exe` automatisch unter `%ProgramFiles%\Nefarius Software Solutions\HidHide\`, alternativ per Durchsuchen-Button.

## Entwicklung

```bash
pip install PySide6
python main.py
python test_core.py   # Kernfunktionstests
```

## Veröffentlichen (Klick-Weg)

Neue Version: Code-Änderung mit `APP_VERSION`-Bump auf `main` mergen, dann auf GitHub: **Releases → Draft a new release → Tag `v<genau die Nummer aus main.py>` → Target main → Publish**. Der Workflow baut die EXE automatisch und hängt sie an das Release an.
