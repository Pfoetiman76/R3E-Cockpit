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

import updater  # 0.3.0: Update-Pruefung ueber GitHub Releases

# Hilfsprozesse unsichtbar ausfuehren: Ohne dieses Flag oeffnet Windows fuer
# JEDEN tasklist-Aufruf ein eigenes schwarzes Konsolenfenster (die App selbst
# hat keine Konsole). Auf anderen Plattformen ist das Flag 0.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

APP_NAME = "R3E Cockpit"
APP_VERSION = "0.3.1"
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
            "path": "",
            "search_hints": [
                r"{ProgramFiles}\PitBoss R3E\PitBossR3E.exe",
                r"{ProgramFilesX86}\PitBoss R3E\PitBossR3E.exe",
                r"{LocalAppData}\Programs\PitBoss R3E\PitBossR3E.exe",
            ],
            "process": "PitBossR3E.exe",
        },
        {
            "id": "resultate",
            "name": "R3E-Resultate",
            "group": "r3e",
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
    "profiles": [
        {"id": "rennabend", "name": "Rennabend",
         "apps": ["raceroom", "pitboss_r3e", "simhub", "crewchief", "conspit_link", "simucube_tuner"]},
        {"id": "analyse", "name": "Analyse", "apps": ["resultate", "setup_coach"]},
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
        if not isinstance(cfg.get("profiles"), list):
            # aeltere launcher.json: Startprofile ergaenzen und speichern
            cfg["profiles"] = DEFAULT_CONFIG["profiles"]
            save_config(cfg)
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
            creationflags=NO_WINDOW,
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
        return "bereit", "info"
    return "Pfad fehlt", "warn"


def profile_plan(cfg, profile, procs):
    """(starten, laufen_bereits, ohne_pfad) fuer ein Startprofil ermitteln."""
    apps_by_id = {a.get("id"): a for a in cfg.get("apps", [])}
    start, already, nopath = [], [], []
    for app_id in profile.get("apps", []):
        a = apps_by_id.get(app_id)
        if not a:
            continue
        if app_is_running(a, procs):
            already.append(a)
        elif a.get("path") or a.get("fixed"):
            start.append(a)
        else:
            nopath.append(a)
    return start, already, nopath


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
            subprocess.Popen([path] + list(args), cwd=os.path.dirname(path),
                             creationflags=NO_WINDOW)
        return None
    except OSError as exc:
        return str(exc)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

STYLE = """
QWidget { font-family: 'Montserrat', 'Segoe UI', 'Inter', sans-serif; font-size: 13px; color: #f1f1f3; background-color: #0c0c0e; }
QLabel#groupLabel { color: #8f8f99; font-size: 11px; font-weight: 800; letter-spacing: 1px; }
QLabel#title { color: #f1f1f3; font-size: 19px; font-weight: 800; }
QLabel#version { color: #8f8f99; font-size: 11px; }
QFrame#tile { background-color: #131316; border: 1px solid #26262c; border-radius: 0; }
QFrame#accent { background-color: #e8212b; border-radius: 0; }
QFrame#accentW { background-color: #8f8f99; border-radius: 0; }
QLabel#appName { color: #f1f1f3; font-size: 15px; font-weight: 700; }
QLabel#appStatus { color: #8f8f99; font-size: 11px; }
QPushButton {
    background-color: rgba(52,51,56,0.92); color: #f1f1f3; font-weight: 700;
    border: 1px solid rgba(255,255,255,0.07); border-radius: 0; padding: 7px 16px;
}
QPushButton:hover { border-color: #e8212b; background-color: rgba(80,79,86,0.96); }
QPushButton:pressed { background-color: #131316; }
QPushButton:disabled { color: #8f8f99; background-color: #15151a; border-color: #26262c; }
QPushButton#primary { background-color: #e8212b; color: #ffffff; border: 1px solid #e8212b; }
QPushButton#primary:hover { background-color: #ff3a45; border-color: #ff3a45; }
QPushButton#primary:pressed { background-color: #a81119; }
QPushButton#linkBtn {
    background-color: #131316; color: #ff5a63; border: 1px solid #26262c;
    text-align: left; padding: 10px 12px; border-radius: 0;
}
QPushButton#linkBtn:hover { border-color: #e8212b; }
QLabel#feedback { color: #ff5a63; font-size: 12px; }
QPushButton#editBtn {
    background-color: transparent; color: #8f8f99; border: 1px solid #26262c;
    border-radius: 0; padding: 7px 10px; font-weight: 700;
}
QPushButton#editBtn:hover { border-color: #e8212b; color: #f1f1f3; }
QPushButton#updBtn {
    background-color: transparent; color: #ff5a63; font-weight: 700;
    border: 1px solid #e8212b; border-radius: 0; padding: 5px 12px;
}
QPushButton#updBtn:hover { background-color: #e8212b; color: #ffffff; }
"""


def main():
    from PySide6.QtCore import Qt, QTimer, QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import (
        QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
        QCheckBox, QDialog, QDialogButtonBox, QMessageBox, QPushButton,
        QVBoxLayout, QWidget,
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
    upd_btn = QPushButton("Update verfuegbar ↓")
    upd_btn.setObjectName("updBtn")
    upd_btn.setVisible(False)
    upd_btn.clicked.connect(lambda: on_update_clicked())
    head.addWidget(upd_btn)
    outer.addLayout(head, 0, 0, 1, 3)

    tiles = {}

    # --- Automatisches Update (0.3.0) ---------------------------------------
    update_info = {}

    def check_update():
        res = updater.check_for_update(APP_VERSION)
        if res.get("available"):
            update_info.update(res)
            upd_btn.setText("v%s herunterladen ↓" % res.get("tag", "?").lstrip("v"))
            upd_btn.setVisible(True)
        elif res.get("error"):
            upd_btn.setText("Update-Pruefung fehlgeschlagen")
            upd_btn.setVisible(True)
        # sonst: aktuell, Button bleibt unsichtbar

    def on_update_clicked():
        if not update_info.get("url"):
            reply = QMessageBox.information(
                root, "R3E Cockpit Update",
                "Kein Update verfuegbar. Du nutzt bereits Version %s." % APP_VERSION)
            return
        reply = QMessageBox.question(
            root, "R3E Cockpit Update",
            "Version %s ist verfuegbar (installiert: %s).\n\n"
            "Herunterladen und Installation jetzt starten?\n"
            "Der Cockpit schliesst sich dafuer." % (update_info.get("tag", "?"), APP_VERSION),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply != QMessageBox.Yes:
            return
        upd_btn.setText("Lade herunter …")
        upd_btn.setEnabled(False)
        path = updater.download_asset(update_info.get("url"))
        upd_btn.setEnabled(True)
        if not path:
            upd_btn.setText("Download fehlgeschlagen")
            QMessageBox.warning(root, "R3E Cockpit Update",
                                "Der Download ist fehlgeschlagen. Bitte spaeter erneut "
                                "probieren oder manuell von der Releases-Seite laden.")
            return
        if updater.run_installer(path):
            app.quit()
        else:
            QMessageBox.warning(root, "R3E Cockpit Update",
                                "Installer konnte nicht gestartet werden: %s" % path)

    def make_tile(app_cfg):
        tile = QFrame()
        tile.setObjectName("tile")
        accent = QFrame()
        accent.setObjectName("accent" if app_cfg.get("group") == "r3e" else "accentW")
        accent.setFixedHeight(4)
        name = QLabel(app_cfg.get("name", ""))
        name.setObjectName("appName")
        status = QLabel("pruefe …")
        status.setObjectName("appStatus")
        status.setWordWrap(True)
        btn = QPushButton("Starten")
        btn.setObjectName("primary")
        btn.clicked.connect(lambda: on_start(app_cfg, btn))
        col = QVBoxLayout(tile)
        col.setContentsMargins(20, 14, 20, 14)
        col.addWidget(accent)
        col.addSpacing(6)
        col.addWidget(name)
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

    # --- Startprofile --------------------------------------------------------
    prof_feedback = QLabel("")
    prof_feedback.setObjectName("feedback")
    links_row = next_row

    def on_profile(prof):
        procs = running_process_names()
        start, already, nopath = profile_plan(cfg, prof, procs)
        errs = 0
        for a in start:
            if start_app(a):
                errs += 1
        msg = "%s: %d gestartet" % (prof.get("name", "Profil"), len(start) - errs)
        if already:
            msg += ", %d lief bereits" % len(already)
        if nopath:
            msg += ", %d ohne Pfad uebersprungen" % len(nopath)
        if errs:
            msg += ", %d Fehler" % errs
        prof_feedback.setText(msg)
        QTimer.singleShot(8000, lambda: prof_feedback.setText(""))
        refresh()

    def edit_profile(prof):
        # Eigenes Menue je Profil: Auswahl der zu startenden Programme.
        # Haken = beim Profilstart beruecksichtigt; Speicherung in launcher.json.
        dlg = QDialog(root)
        dlg.setWindowTitle("Profil bearbeiten: %s" % prof.get("name", ""))
        dlg.setModal(True)
        dlg.resize(320, 380)
        col = QVBoxLayout(dlg)
        hint = QLabel("Welche Programme soll das Profil \"%s\" starten?"
                      % prof.get("name", ""))
        hint.setObjectName("appStatus")
        hint.setWordWrap(True)
        col.addWidget(hint)
        col.addSpacing(6)
        checks = {}
        for app_cfg in cfg.get("apps", []):
            cb = QCheckBox(app_cfg.get("name", ""))
            cb.setChecked(app_cfg.get("id") in (prof.get("apps") or []))
            checks[app_cfg.get("id")] = cb
            col.addWidget(cb)
        col.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Speichern")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        col.addWidget(buttons)
        if dlg.exec() == QDialog.Accepted:
            prof["apps"] = [app_id for app_id, cb in checks.items() if cb.isChecked()]
            save_config(cfg)
            prof_feedback.setText("Profil %s gespeichert: %d Programme."
                                  % (prof.get("name", ""), len(prof["apps"])))
            QTimer.singleShot(8000, lambda: prof_feedback.setText(""))

    if cfg.get("profiles"):
        lbl = QLabel("STARTPROFILE")
        lbl.setObjectName("groupLabel")
        outer.addWidget(lbl, next_row, 0, 1, 3, Qt.AlignTop)
        prow = QHBoxLayout()
        for prof in cfg.get("profiles", []):
            pbtn = QPushButton(prof.get("name", ""))
            pbtn.setObjectName("primary")
            pbtn.clicked.connect(lambda _=False, p=prof: on_profile(p))
            prow.addWidget(pbtn)
            ebtn = QPushButton("⚙")
            ebtn.setObjectName("editBtn")
            ebtn.setToolTip("Programmauswahl für %s bearbeiten" % prof.get("name", ""))
            ebtn.clicked.connect(lambda _=False, p=prof: edit_profile(p))
            prow.addWidget(ebtn)
        prow.addStretch(1)
        outer.addLayout(prow, next_row + 1, 0, 1, 3)
        outer.addWidget(prof_feedback, next_row + 2, 0, 1, 3)
        links_row = next_row + 3

    # --- Links ---------------------------------------------------------------
    lbl = QLabel("LINKS")
    lbl.setObjectName("groupLabel")
    outer.addWidget(lbl, links_row, 0, 1, 3, Qt.AlignTop)
    col = 0
    for link in cfg.get("links", []):
        btn = QPushButton(link.get("name", "") + "  ↗")
        btn.setObjectName("linkBtn")
        url = link.get("url", "")
        btn.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
        outer.addWidget(btn, links_row + 1, col)
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
    QTimer.singleShot(1500, check_update)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
