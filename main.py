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
APP_VERSION = "0.3.3"
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


def icon_candidates():
    """Moegliche Speicherorte des App-Icons (Qt-frei, testbar).
    Gefrorene Onedir-EXE: Icon liegt via --add-data im _internal-Ordner."""
    b = base_dir()
    return [os.path.join(b, "cockpit.ico"),
            os.path.join(b, "_internal", "cockpit.ico"),
            os.path.join(b, "assets", "cockpit.ico")]


def new_program_id(name):
    """Aus einem Anzeigenamen eine stabile ID ableiten (klein, alphanumerisch)."""
    import re as _re
    slug = _re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return slug or "programm"


def profile_id_from_name(name):
    """ID fuer ein neues Profil aus dem Namen ableiten (stabil, alphanumerisch)."""
    import re as _re
    slug = _re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return slug or "profil"


def profile_add(cfg, name):
    """Neues benanntes Profil anlegen. Rueckgabe: Profil oder None bei leerem Namen."""
    name = (name or "").strip()
    if not name:
        return None
    pid = profile_id_from_name(name)
    ids = {p.get("id") for p in cfg.get("profiles", [])}
    base, n = pid, 2
    while pid in ids:
        pid = "%s_%d" % (base, n)
        n += 1
    prof = {"id": pid, "name": name, "apps": []}
    cfg.setdefault("profiles", []).append(prof)
    return prof


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
    from PySide6.QtGui import QDesktopServices, QIcon
    from PySide6.QtWidgets import (
        QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
        QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
        QInputDialog, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
    )

    cfg = load_config()
    detect_all(cfg)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(STYLE)
    # 0.3.2: Fenster- und Taskleisten-Icon. Ohne AppUserModelID gruppiert
    # Windows Taskleiste/Alt-Tab falsch und zeigt das Standard-Python-Icon.
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Pfoetiman76.R3ECockpit")
    except Exception:
        pass  # Nicht-Windows oder kein ctypes
    for cand in icon_candidates():
        if os.path.isfile(cand):
            app.setWindowIcon(QIcon(cand))
            break

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
    manage_btn = QPushButton("⚙ Programme")
    manage_btn.setObjectName("editBtn")
    manage_btn.setToolTip("Programme ändern, hinzufügen oder entfernen")
    manage_btn.clicked.connect(lambda: manage_programs())
    head.addWidget(manage_btn)
    upd_btn = QPushButton("Update verfuegbar ↓")
    upd_btn.setObjectName("updBtn")
    upd_btn.setVisible(False)
    upd_btn.clicked.connect(lambda: on_update_clicked())
    head.addWidget(upd_btn)
    outer.addLayout(head, 0, 0, 1, 3)

    tiles = {}

    # --- Programmverwaltung (0.3.2) ------------------------------------------
    def manage_programs():
        dlg = QDialog(root)
        dlg.setWindowTitle("Programme verwalten")
        dlg.setModal(True)
        dlg.resize(460, 300)
        col = QVBoxLayout(dlg)

        combo = QComboBox()
        combo.addItem("— Neues Programm —", None)
        for a in cfg.get("apps", []):
            combo.addItem(a.get("name", ""), a.get("id"))
        col.addWidget(combo)

        form = QFormLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Anzeigename, z. B. Trading Dashboard")
        path_edit = QLineEdit()
        path_edit.setPlaceholderText(r"C:\Programme\Beispiel\App.exe oder steam://…")
        proc_edit = QLineEdit()
        proc_edit.setPlaceholderText("leer lassen = automatisch (Dateiname des Pfads)")
        form.addRow("Name:", name_edit)
        form.addRow("Pfad:", path_edit)
        row_path = QHBoxLayout()
        browse = QPushButton("Durchsuchen …")
        browse.clicked.connect(lambda: (path_edit.setText(
            QFileDialog.getOpenFileName(dlg, "Programm wählen", "",
                                        "Programme (*.exe)")[0] or path_edit.text())))
        row_path.addWidget(path_edit, 1)
        row_path.addWidget(browse)
        form.addRow("", row_path)
        form.addRow("Prozessname:", proc_edit)
        col.addLayout(form)
        col.addSpacing(6)

        hint = QLabel("Änderungen und neue Programme erscheinen als Kachel nach dem "
                      "nächsten Start des Cockpits.")
        hint.setObjectName("appStatus")
        hint.setWordWrap(True)
        col.addWidget(hint)
        col.addStretch(1)

        btns = QHBoxLayout()
        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("primary")
        del_btn = QPushButton("Löschen …")
        close_btn = QPushButton("Schließen")
        btns.addWidget(save_btn)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        btns.addWidget(close_btn)
        col.addLayout(btns)

        def load_selection():
            app_id = combo.currentData()
            if app_id is None:
                name_edit.setText("")
                path_edit.setText("")
                proc_edit.setText("")
                return
            for a in cfg.get("apps", []):
                if a.get("id") == app_id:
                    name_edit.setText(a.get("name", ""))
                    path_edit.setText(a.get("path", ""))
                    proc_edit.setText(a.get("process", ""))
                    return

        combo.currentIndexChanged.connect(lambda _i: load_selection())
        load_selection()

        def on_save():
            name = name_edit.text().strip()
            path = path_edit.text().strip().replace('"', "")
            proc = proc_edit.text().strip()
            if not name:
                QMessageBox.warning(dlg, "Programme verwalten",
                                    "Bitte einen Namen angeben.")
                return
            if not path:
                QMessageBox.warning(dlg, "Programme verwalten",
                                    "Bitte einen Pfad (EXE oder steam://…) angeben.")
                return
            app_id = combo.currentData()
            if app_id is None:
                new_id = new_program_id(name)
                existing = {a.get("id") for a in cfg.get("apps", [])}
                if new_id in existing:
                    new_id += "_2"
                cfg.setdefault("apps", []).append(
                    {"id": new_id, "name": name, "group": "weitere",
                     "path": path, "process": proc})
            else:
                for a in cfg.get("apps", []):
                    if a.get("id") == app_id:
                        a["name"] = name
                        a["path"] = path
                        a["process"] = proc
                        break
            if not save_config(cfg):
                QMessageBox.warning(dlg, "Programme verwalten",
                                    "Konnte launcher.json nicht speichern.")
                return
            QMessageBox.information(
                dlg, "Programme verwalten",
                "Gespeichert. Neue oder geänderte Kacheln erscheinen nach dem "
                "nächsten Start des Cockpits.")
            dlg.accept()

        def on_delete():
            app_id = combo.currentData()
            if app_id is None:
                QMessageBox.information(dlg, "Programme verwalten",
                                        "Zum Löschen bitte ein bestehendes Programm auswählen.")
                return
            for a in cfg.get("apps", []):
                if a.get("id") == app_id:
                    if a.get("fixed"):
                        reply = QMessageBox.question(
                            dlg, "Programme verwalten",
                            "„%s“ ist ein Systemeintrag. Wirklich entfernen?" % a.get("name", ""),
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if reply != QMessageBox.Yes:
                            return
                    cfg["apps"].remove(a)
                    break
            if not save_config(cfg):
                QMessageBox.warning(dlg, "Programme verwalten",
                                    "Konnte launcher.json nicht speichern.")
                return
            QMessageBox.information(
                dlg, "Programme verwalten",
                "Entfernt. Die Kachel verschwindet nach dem nächsten Start.")
            dlg.accept()

        save_btn.clicked.connect(on_save)
        del_btn.clicked.connect(on_delete)
        close_btn.clicked.connect(dlg.reject)
        dlg.exec()

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
        nrow = QHBoxLayout()
        ren_btn = QPushButton("Umbenennen")
        ren_btn.setObjectName("editBtn")

        def do_rename(_=False, p=prof):
            new_name, ok = QInputDialog.getText(dlg, "Profil umbenennen",
                                                "Neuer Name:", text=p.get("name", ""))
            new_name = (new_name or "").strip()
            if not ok or not new_name or new_name == p.get("name"):
                return
            p["name"] = new_name
            save_config(cfg)
            prof_feedback.setText('Profil umbenannt in "%s" - erscheint nach Neustart.'
                                  % new_name)
            QTimer.singleShot(8000, lambda: prof_feedback.setText(""))
            dlg.reject()

        ren_btn.clicked.connect(do_rename)
        nrow.addWidget(ren_btn)
        del_btn = QPushButton("Löschen")
        del_btn.setObjectName("editBtn")

        def do_delete(_=False, p=prof):
            reply = QMessageBox.question(dlg, "Profil löschen",
                                         'Profil "%s" wirklich löschen?' % p.get("name", ""),
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            pl = cfg.get("profiles", [])
            if p in pl:
                pl.remove(p)
            save_config(cfg)
            prof_feedback.setText('Profil "%s" gelöscht - verschwindet nach Neustart.'
                                  % p.get("name", ""))
            QTimer.singleShot(8000, lambda: prof_feedback.setText(""))
            dlg.reject()

        del_btn.clicked.connect(do_delete)
        nrow.addWidget(del_btn)
        nrow.addStretch(1)
        col.addLayout(nrow)
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
        addbtn = QPushButton("＋ Profil")
        addbtn.setObjectName("editBtn")
        addbtn.setToolTip("Neues eigenes Profil anlegen")

        def on_add_profile(_=False):
            name, ok = QInputDialog.getText(root, "Neues Profil", "Name des Profils:")
            prof_new = profile_add(cfg, name)
            if prof_new is None:
                if ok:
                    QMessageBox.warning(root, "Neues Profil",
                                        "Bitte einen Namen eingeben.")
                return
            save_config(cfg)
            prof_feedback.setText('Profil "%s" angelegt - Kachel erscheint nach Neustart.'
                                  % prof_new["name"])
            QTimer.singleShot(8000, lambda: prof_feedback.setText(""))

        addbtn.clicked.connect(on_add_profile)
        prow.addWidget(addbtn)
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
