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

# 4) status_file_ok: Datei im Arbeitsverzeichnis
open("___test_status.txt", "w").write("x")
check("status_file_ok vorhanden", main.status_file_ok({"status_file": "___test_status.txt"}))
check("status_file_ok fehlt", not main.status_file_ok({"status_file": "gibtsnich.xyz"}))
os.remove("___test_status.txt")

# 5) app_status_text Pfaelle
check("Status Pfad fehlt", main.app_status_text({"path": ""}, set())[1] == "warn")
check("Status bereit", main.app_status_text({"path": "C:/a.exe"}, set())[0] == "bereit")
check("Status laeuft", main.app_status_text({"path": "C:/a.exe", "process": "a.exe"}, {"a.exe"})[0] == "laeuft")

# 6) expand_hint
os.environ.setdefault("LOCALAPPDATA", "C:/Users/x/AppData/Local")
check("expand_hint ersetzt Platzhalter",
      main.expand_hint(r"{LocalAppData}\Test").startswith("C:/Users/x/AppData/Local"))

# 7) results_db_info auf Linux: Datei nicht vorhanden -> (False, 0)
check("results_db fehlt ok", main.results_db_info()[0] is False)

print()
print("ERGEBNIS: %s" % ("ALLE TESTS BESTANDEN" if not fails else "FEHLGESCHLAGEN: %s" % fails))
sys.exit(1 if fails else 0)
