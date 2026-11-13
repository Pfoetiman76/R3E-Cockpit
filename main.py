# -*- coding: utf-8 -*-
"""R3E Cockpit - Launcher fuer das R3E-Okosystem und weitere Simracing-Programme.

Schlanke PySide6-App im PitBoss-Stil. Startet Programme per EXE-Aufruf und
prueft Status ausschliesslich LESEND (Prozesse, Dateiexistenz, SQLite-Count).
Der Launcher besitzt selbst nur launcher.json und schreibt in nichts anderes.
"""
import json
import os
import sqlite3
import subprocess
import sys

APP_NAME = "R3E Cockpit"
APP_VERSION = "0.1.1"
CONFIG_NAME = "launcher.json"
SCHEMA_VERSION = 1

COMPETITIONS_URL = "https://game.raceroomracing.com/competitions/"

DEFAULT_CONFIG = {
    "schema_version": 1,
    "apps": [
        {
            "id": "pitboss_r3e",
            "name": "PitBoss R3E",
            "group": "r3e",
            "version": "0.4.2.10 Beta",
            "path": "",
            "search_hints": [
                r"{ProgramFiles}\PitBoss R3E\PitBossR3E.exe",
                r"{ProgramFilesX86}\PitBoss R3E\PitBossR3E.exe",
                r"{LocalAppData}\Programs\PitBoss R3E\PitBossR3E.exe",
            ],
            "process": "PitBossR3E.exe",
            "status_file": r"{Documents}\PitBoss R3E\overlay_prefs.json",
        },
        {
            "id": "resultate",
            "name": "R3E-Resultate",
            "group": "r3e",
            "version": "",
            "path": "",
            "search_hints": [
                r"{ProgramFiles}\RaceRoom Results Companion\R3EResultate.exe",
                r"{ProgramFilesX86}\RaceRoom Results Companion\R3EResultate.exe",
                r"{LocalAppData}\Programs\RaceRoom Results Companion\R3EResultate.exe",
            ],
            "process": "",
            "results_db": True,
        },
        {
            "id": "setup_coach",
            "name": "Setup-Coach",
            "group": "r3e",
            "version": "in Entwicklung",
            "path": "",
            "search_hints": [],
            "process": "",
        },
        {
            "id": "raceroom",
            "name": "RaceRoom Racing Experience",
            "group": "weitere",
            "path": "steam://rungameid/518790",
            "process": "RRRE.exe",
            "fixed": True,
        },
        {
            "id": "simhub",
            "name": "SimHub",
            "group": "weitere",
            "path": "",
            "search_hints": [
                r"{ProgramFiles}\SimHub\SimHubWPF.exe",
                r"{ProgramFilesX86}\SimHub\SimHubWPF.exe",
                r"{LocalAppData}\SimHub\SimHubWPF.exe",
            ],
            "process": "SimHubWPF.exe",
        },
        {
            "id": "crewchief",
            "name": "CrewChief",
            "group": "weitere",
            "path": "",
            "search_hints": [
                r"{ProgramFiles}\CrewChiefV4\CrewChiefV4.exe",
                r"{ProgramFilesX86}\CrewChiefV4\CrewChiefV4.exe",
                r"{LocalAppData}\CrewChiefV4\CrewChiefV4.exe",
            ],
            "process": "CrewChiefV4.exe",
        },
        {
            "id": "simucube_tuner",
            "name": "Simucube Tuner",
            "group": "weitere",
            "path": "",
            "search_hints": [
                r"{ProgramFiles}\Simucube 2 Tuner\SimucubeTuner.exe",
                r"{ProgramFilesX86}\Simucube 2 Tuner\SimucubeTuner.exe",
                r"{LocalAppData}\Simucube 2 Tuner\SimucubeTuner.exe",
            ],
            "process": "",
        },
        {
            "id": "conspit_link",
            "name": "Conspit Link 2.0",
            "group": "weitere",
            "path": "",
            "search_hints": [
                r"{ProgramFiles}\Conspit\Conspit Link\ConspitLink.exe",
                r"{ProgramFilesX86}\Conspit\Conspit Link\ConspitLink.exe",
                r"{LocalAppData}\Conspit\ConspitLink.exe",
            ],
            "process": "",
        },
    ],
    "links": [
        {"id": "competitions", "name": "RaceRoom Wettbewerbe", "url": COMPETITIONS_URL},
    ],
}


# ---------------------------------------------------------------------------
# Hilfsfunktionen (ohne Qt, damit testbar)
# ---------------------------------------------------------------------------

def base_dir():
    """Konfiguration liegt neben der EXE (PyInstaller) bzw. neben main.py."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def config_path():
    return os.path.join(base_dir(), CONFIG_NAME)


def env_map():
    """Platzhalter -> Windows-Sonderordner (unabhaengig von der Sprachversion)."""
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    return {
        "{Documents}": docs,
        "{ProgramFiles}": os.environ.get("ProgramFiles", r"C:\Program Files"),
        "{ProgramFilesX86}": os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        "{LocalAppData}": os.environ.get("LOCALAPPDATA", ""),
        "{AppData}": os.environ.get("APPDATA", ""),
    }


def expand_hint(hint):
    out = hint
    for key, val in env_map().items():
        out = out.replace(key, val)
    return out


def load_config():
    path = config_path()
    if not os.path.isfile(path):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        if not isinstance(cfg, dict) or not isinstance(cfg.get("apps"), list):
            raise ValueError("Struktur ungueltig")
        return cfg
    except Exception:
        # Korrupte Datei toleriert laden (Leerzustand statt Absturz)
        return DEFAULT_CONFIG


def save_config(cfg):
    """Atomar schreiben: .tmp dann os.replace (Muster aus rrc/fuelcalc.py)."""
    path = config_path()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def detect_app_path(app):
    """Ersten existierenden Pfad aus den search_hints uebernehmen."""
    changed = False
    if not app.get("path") and not app.get("fixed"):
        for hint in app.get("search_hints", []):
            cand = expand_hint(hint)
            if cand and os.path.isfile(cand):
                app["path"] = cand
                changed = True
                break
    return changed


def detect_all(cfg):
    changed = False
    for app in cfg.get("apps", []):
        if detect_app_path(app):
            changed = True
    if changed:
        save_config(cfg)
    return changed


def running_process_names():
    """Menge der laufenden Prozessnamen (kleingeschrieben) per tasklist."""
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception:
        return set()
    names = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or not line.startswith('"'):
            continue
        try:
            name = line.split('"')[1].lower()
            if name:
                names.add(name)
        except IndexError:
            continue
    return names


def app_process_name(app):
    proc = app.get("process") or ""
    if proc:
        return proc.lower()
    path = app.get("path") or ""
    if path and not path.startswith(("steam://", "http://", "https://")):
        norm = path.replace("\\", "/").rstrip("/")
        return norm.rsplit("/", 1)[-1].lower()
    return ""


def app_is_running(app, procs):
    name = app_process_name(app)
    return bool(name) and name in procs


def results_db_info():
    """results.db NUR LESEND: Existenz + Sitzungsanzahl (Eigentuemer: R3E-Resultate)."""
    path = os.path.join(os.path.expanduser("~"), "Documents",
                        "RaceRoom Results Companion", "results.db")
    if not os.path.isfile(path):
        return False, 0
    try:
        con = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
        try:
            cur = con.execute("SELECT COUNT(*) FROM sessions")
            count = int(cur.fetchone()[0])
        finally:
            con.close()
        return True, count
    except Exception:
        return True, -1


def status_file_ok(app):
    """Optionale Vorbedingung: angegebene Datei existiert (z. B. App-Config)."""
    sf = app.get("status_file") or ""
    if not sf:
        return True
    return os.path.isfile(expand_hint(sf))


def app_status_text(app, procs):
    if app_is_running(app, procs):
        return "laeuft", "ok"
    if app.get("results_db"):
        ok, count = results_db_info()
        if ok:
            txt = "results.db lesbar"
            if count >= 0:
                txt += " · %d Sitzungen" % count
            return txt, "info"
        return "results.db nicht gefunden", "warn"
    if app.get("fixed") or app.get("path"):
        if not status_file_ok(app):
            return "Konfiguration nicht gefunden", "warn"
        return "bereit", "info"
    return "Pfad fehlt", "warn"


def start_app(app):
    """Programm starten. Rueckgabe: Fehlermeldung oder None."""
    path = app.get("path") or ""
    if not path:
        return "Kein Pfad festgelegt."
    try:
        if path.startswith(("steam://", "http://", "https://")):
            os.startfile(path)
        else:
            args = app.get("args") or []
            subprocess.Popen([path] + list(args), cwd=os.path.dirname(path))
        return None
    except OSError as exc:
        return str(exc)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

STYLE = """
QWidget { background-color: #14181d; color: #e8eef3; font-family: 'Segoe UI'; font-size: 12px; }
QLabel#groupLabel { color: #7d93a3; font-size: 12px; letter-spacing: 1px; }
QLabel#title { color: #00e5ff; font-size: 20px; font-weight: 600; }
QLabel#version { color: #5a6b78; font-size: 12px; }
QFrame#tile { background-color: #1a2129; border: 1px solid #2a3642; border-radius: 10px; }
QFrame#accent { background-color: #00e5ff; border-radius: 2px; }
QFrame#accentW { background-color: #f5a623; border-radius: 2px; }
QLabel#appName { color: #e8eef3; font-size: 15px; font-weight: 600; }
QLabel#appVersion { color: #7d93a3; font-size: 11px; }
QLabel#appStatus { color: #5a6b78; font-size: 10px; }
QPushButton {
    background-color: #00b8cc; color: #0d1114; font-weight: 600;
    border: none; border-radius: 6px; padding: 5px 14px;
}
QPushButton:hover { background-color: #00e5ff; }
QPushButton:disabled { background-color: #26333f; color: #7d93a3; }
QPushButton#linkBtn {
    background-color: #1a2129; color: #00e5ff; border: 1px solid #2a3642;
    text-align: left; padding: 10px 12px;
}
QPushButton#linkBtn:hover { border-color: #00b8cc; }
"""


def main():
    from PySide6.QtCore import Qt, QTimer, QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
        QPushButton, QVBoxLayout, QWidget,
    )

    cfg = load_config()
    detect_all(cfg)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLE)

    root = QWidget()
    root.setWindowTitle("%s %s" % (APP_NAME, APP_VERSION))
    root.resize(920, 640)
    outer = QGridLayout(root)
    outer.setContentsMargins(24, 18, 24, 18)
    outer.setVerticalSpacing(10)

    # --- Kopfzeile -----------------------------------------------------------
    head = QHBoxLayout()
    title = QLabel(APP_NAME.upper())
    title.setObjectName("title")
    version = QLabel("Launcher · v%s" % APP_VERSION)
    version.setObjectName("version")
    rr_label = QLabel("RaceRoom: pruefe …")
    rr_label.setObjectName("appVersion")
    head.addWidget(title)
    head.addSpacing(10)
    head.addWidget(version)
    head.addStretch(1)
    head.addWidget(rr_label)
    outer.addLayout(head, 0, 0, 1, 3)

    tiles = {}

    def make_tile(app_cfg):
        tile = QFrame()
        tile.setObjectName("tile")
        accent = QFrame()
        accent.setObjectName("accent" if app_cfg.get("group") == "r3e" else "accentW")
        accent.setFixedHeight(4)
        name = QLabel(app_cfg.get("name", ""))
        name.setObjectName("appName")
        sub = QLabel(app_cfg.get("version") or "")
        sub.setObjectName("appVersion")
        status = QLabel("pruefe …")
        status.setObjectName("appStatus")
        status.setWordWrap(True)
        btn = QPushButton("Starten")
        btn.clicked.connect(lambda: on_start(app_cfg, btn))
        col = QVBoxLayout(tile)
        col.setContentsMargins(20, 14, 20, 14)
        col.addWidget(accent)
        col.addSpacing(6)
        col.addWidget(name)
        col.addWidget(sub)
        col.addWidget(status)
        col.addStretch(1)
        row = QHBoxLayout()
        row.addWidget(btn)
        row.addStretch(1)
        col.addLayout(row)
        tile.setLayout(col)
        return tile, btn, status

    def on_start(app_cfg, btn):
        if not app_cfg.get("path") and not app_cfg.get("fixed"):
            path, _ = QFileDialog.getOpenFileName(
                root, "Programm wählen (%s)" % app_cfg.get("name", ""),
                "", "Programme (*.exe)")
            if path:
                app_cfg["path"] = path
                save_config(cfg)
        err = start_app(app_cfg)
        if err:
            btn.setText("Fehler")
            QTimer.singleShot(2000, lambda: btn.setText("Starten"))
        refresh()

    def add_group(label_text, group_id, row_start):
        lbl = QLabel(label_text)
        lbl.setObjectName("groupLabel")
        outer.addWidget(lbl, row_start, 0, 1, 3, Qt.AlignTop)
        idx = 0
        row = row_start + 1
        for app_cfg in cfg.get("apps", []):
            if group_id and app_cfg.get("group") != group_id:
                continue
            tile, btn, status = make_tile(app_cfg)
            tiles[app_cfg["id"]] = (app_cfg, btn, status)
            outer.addWidget(tile, row, idx % 3)
            idx += 1
            if idx % 3 == 0:
                row += 1
        return row + (1 if idx % 3 else 0)

    next_row = add_group("R3E-ÖKOSYSTEM", "r3e", 1)
    next_row = add_group("WEITERE PROGRAMME", "weitere", next_row)

    # --- Links ---------------------------------------------------------------
    lbl = QLabel("LINKS")
    lbl.setObjectName("groupLabel")
    outer.addWidget(lbl, next_row, 0, 1, 3, Qt.AlignTop)
    col = 0
    for link in cfg.get("links", []):
        btn = QPushButton(link.get("name", "") + "  ↗")
        btn.setObjectName("linkBtn")
        url = link.get("url", "")
        btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
        outer.addWidget(btn, next_row + 1, col)
        col += 1

    footer = QLabel("Statusprüfung ausschließlich lesend · der Launcher schreibt nur launcher.json")
    footer.setObjectName("appStatus")
    outer.addWidget(footer, outer.rowCount(), 0, 1, 3)
    outer.setRowStretch(outer.rowCount() - 1, 1)

    # --- Status-Aktualisierung ----------------------------------------------
    def refresh():
        procs = running_process_names()
        if "rrre.exe" in procs:
            rr_label.setText("RaceRoom: läuft")
        else:
            rr_label.setText("RaceRoom: nicht aktiv")
        for app_id, (app_cfg, btn, status_lbl) in tiles.items():
            txt, _kind = app_status_text(app_cfg, procs)
            status_lbl.setText(txt)
            running = app_is_running(app_cfg, procs)
            btn.setEnabled(True)
            if not app_cfg.get("path") and not app_cfg.get("fixed"):
                btn.setText("Pfad festlegen")
            elif running:
                btn.setText("Läuft")
            else:
                btn.setText("Starten")

    timer = QTimer(root)
    timer.timeout.connect(refresh)
    timer.start(5000)

    root.show()
    refresh()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
