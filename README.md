# R3E Cockpit

Schlanker Launcher für das R3E-Ökosystem und weitere Simracing-Programme — im Stil von PitBoss R3E (dunkles Theme, Türkis-Akzent).

## Enthaltene Kacheln

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

## Erste Einrichtung

Die App versucht, Installationspfade automatisch zu erkennen. Kacheln ohne gefundenen Pfad zeigen den Button **„Pfad festlegen“**:

1. Klick auf „Pfad festlegen“.
2. EXE-Datei des Programms auswählen.
3. Pfad wird in `launcher.json` gespeichert und die Kachel zeigt „bereit“.

Die `launcher.json` kann auch direkt editiert werden (UTF-8, JSON). Jeder Eintrag hat: `id`, `name`, `group`, `path`, `process` (Prozessname für die Läuft-Prüfung, Standard: Dateiname des Pfads), optional `args` (Startparameter) und `search_hints` (automatische Pfad-Vorschläge).

## Architektur-Grundsätze

- Der Launcher **besitzt selbst nur** `launcher.json` — keine App schreibt in Dateien anderer Apps (konsistent mit dem R3E-Datenkonzept).
- Statusprüfung ausschließlich lesend: `tasklist` (Prozesse), Dateiexistenz, `results.db` im SQLite-Lesemodus (Eigentümer bleibt R3E-Resultate).
- Konfiguration wird atomar geschrieben (`.tmp` + Ersetzen).

## Entwicklung

```bash
pip install PySide6
python main.py
python test_core.py   # 16 Kernfunktionstests
```

## Veröffentlichen (Klick-Weg)

Neue Version: Code-Änderung mit `APP_VERSION`-Bump auf `main` mergen, dann auf GitHub: **Releases → Draft a new release → Tag `v<genau die Nummer aus main.py>` → Target main → Publish**. Der Workflow baut die EXE automatisch und hängt sie an das Release an.
