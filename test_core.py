# -*- coding: utf-8 -*-
"""Tests fuer die Qt-freien Kernfunktionen von main.py."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main

fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)

# 1) Standardkonfiguration: alle geforderten Apps vorhanden
ids = {a["id"] for a in main.DEFAULT_CONFIG["apps"]}
required = {"pitboss_r3e", "resultate", "setup_coach", "raceroom",
            "simhub", "crewchief", "simucube_tuner", "conspit_link"}
check("alle Apps in Standardkonfiguration", required <= ids)

# 2) save_config + load_config: atomar, Roundtrip
tmpdir = tempfile.mkdtemp()
monkey = main.base_dir
main.base_dir = (lambda: tmpdir)
cfg = {"schema_version": 1, "apps": [{"id": "x", "name": "Test", "path": "C:/a/b.exe"}]}
check("save_config ok", main.save_config(cfg))
check("load_config Roundtrip", main.load_config()["apps"][0]["name"] == "Test")
check("kein .tmp-Ueberbleibsel", not os.path.exists(main.config_path() + ".tmp"))
# korrupte Datei -> Default statt Absturz
open(main.config_path(), "w").write("{kaputt")
check("korrupte Datei toleriert", main.load_config() == main.DEFAULT_CONFIG)
main.base_dir = monkey

# 3) app_process_name / app_is_running
app_cfg = {"path": r"C:\Tools\App\App.exe", "process": ""}
check("Prozessname aus Pfad", main.app_process_name(app_cfg) == "app.exe")
app_cfg2 = {"path": "", "process": "PitBossR3E.exe"}
check("Prozessname override", main.app_process_name(app_cfg2) == "pitbossr3e.exe")
check("app_is_running Treffer", main.app_is_running(app_cfg2, {"pitbossr3e.exe"}))
check("app_is_running kein Treffer", not main.app_is_running(app_cfg2, set()))

# 4) status_file-Pruefung entfallen (v0.1.4)
# 5) app_status_text Pfaelle
check("Status Pfad fehlt", main.app_status_text({"path": ""}, set())[1] == "warn")
check("Status bereit", main.app_status_text({"path": "C:/a.exe"}, set())[0] == "bereit")
check("Status laeuft", main.app_status_text({"path": "C:/a.exe", "process": "a.exe"}, {"a.exe"})[0] == "laeuft")

# 6) expand_hint
os.environ["LOCALAPPDATA"] = "C:/Users/x/AppData/Local"  # explizit setzen: auf Windows-CI-Runnern existiert die Variable ech
check("expand_hint ersetzt Platzhalter",
      main.expand_hint(r"{LocalAppData}\Test").startswith("C:/Users/x/AppData/Local"))

# 7) results_db_info auf Linux: Datei nicht vorhanden -> (False, 0)
check("results_db fehlt ok", main.results_db_info()[0] is False)

# 8) Startprofile: Standardprofile vorhanden und konsistent
profiles = {p["id"]: p for p in main.DEFAULT_CONFIG.get("profiles", [])}
check("Standardprofile vorhanden", {"rennabend", "analyse"} <= set(profiles))
app_ids = {a["id"] for a in main.DEFAULT_CONFIG["apps"]}
for pid, prof in profiles.items():
    check("Profil %s verweist nur auf bekannte Apps" % pid, set(prof["apps"]) <= app_ids)

# 9) profile_plan: starten/laeuft/ohne Pfad sauber trennen
cfg = {"apps": [
    {"id": "a", "path": "C:/x/a.exe", "process": "a.exe"},
    {"id": "b", "path": "C:/x/b.exe", "process": "b.exe"},
    {"id": "c", "path": "", "process": ""},
    {"id": "d", "path": "C:/x/d.exe", "process": "d.exe", "fixed": True},
]}
prof = {"id": "p", "name": "P", "apps": ["a", "b", "c", "d", "unbekannt"]}
s, al, np_ = main.profile_plan(cfg, prof, {"b.exe"})
check("profile_plan starten", [x["id"] for x in s] == ["a", "d"])
check("profile_plan laeuft bereits", [x["id"] for x in al] == ["b"])
check("profile_plan ohne Pfad", [x["id"] for x in np_] == ["c"])

# 10) load_config ergaenzt Profile in alten Konfigurationen
import tempfile
tmpdir = tempfile.mkdtemp()
monkey = main.base_dir
main.base_dir = (lambda: tmpdir)
old_cfg = {"schema_version": 1, "apps": [{"id": "x", "name": "T", "path": "C:/a.exe"}]}
main.save_config(old_cfg)
loaded = main.load_config()
check("alte Konfig erhaelt Startprofile", loaded.get("profiles") == main.DEFAULT_CONFIG["profiles"])
main.base_dir = monkey

print()
print("ERGEBNIS: %s" % ("ALLE TESTS BESTANDEN" if not fails else "FEHLGESCHLAGEN: %s" % fails))
sys.exit(1 if fails else 0)


def test_icon_candidates():
    """0.3.2: drei moegliche Icon-Speicherorte, Windows-Separator, base_dir relativ."""
    cands = mod.icon_candidates()
    assert len(cands) == 3
    assert all("cockpit.ico" in c for c in cands)
    assert any("_internal" in c for c in cands)
    assert all(os.path.isabs(c) for c in cands)


def test_new_program_id():
    """0.3.2: IDs klein, alphanumerisch, robust gegen Sonderzeichen/Leerzeichen."""
    assert mod.new_program_id("Trading Dashboard") == "trading_dashboard"
    assert mod.new_program_id("Conspit Link 2.0!") == "conspit_link_2_0"
    assert mod.new_program_id("") == "programm"
    assert mod.new_program_id("Ünïcödé") == "n_c_d"
