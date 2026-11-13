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

# 11) HidHide (0.4.0)
# a) Sektion ergaenzt fehlende Felder
check("alte Konfig erhaelt HidHide-Sektion", isinstance(loaded.get("hidhide"), dict))
sec = main.hidhide_section({})
check("hidhide_section Default-Felder",
      set(sec) == {"cli_path", "hidden", "whitelist_apps", "extra_whitelist", "cloak"})
check("hidhide_section Default-Werte",
      sec["cli_path"] == "" and sec["hidden"] == [] and sec["cloak"] is True)
# b) find_cli: gespeicherter Pfad wird ignoriert, wenn die Datei fehlt
cfg2 = {"hidhide": {"cli_path": "C:/gibt/es/nicht/HidHideCLI.exe"}}
check("hidhide_find_cli ignoriert fehlenden Pfad", main.hidhide_find_cli(cfg2) == "")
# c) find_cli: Suchhint mit echter Datei
tmp_pf = tempfile.mkdtemp()
os.makedirs(os.path.join(tmp_pf, "Nefarius Software Solutions", "HidHide"))
cli_fake = os.path.join(tmp_pf, "Nefarius Software Solutions", "HidHide", "HidHideCLI.exe")
open(cli_fake, "wb").write(b"fake")
old_pf = os.environ.get("ProgramFiles")
os.environ["ProgramFiles"] = tmp_pf
cfg3 = {"hidhide": {"cli_path": ""}}
found = main.hidhide_find_cli(cfg3)
check("hidhide_find_cli findet Hint", os.path.normcase(found) == os.path.normcase(cli_fake))
check("hidhide_find_cli speichert Fund", cfg3["hidhide"]["cli_path"] == found)
os.environ["ProgramFiles"] = old_pf or ""
# d) hide_paths: normales HID-Geraet (Lenkrad/Pedale) -> nur HID-Pfad
dev_hid = {"deviceInstancePath": "HID\\VID_044F&PID_0001\\6&1234&0&0000",
           "baseContainerDeviceInstancePath": "USB\\VID_044F&PID_0001\\5&1234&0&1",
           "xusbDeviceInstancePath": ""}
check("hidhide_hide_paths nur HID",
      main.hidhide_hide_paths(dev_hid) == ["HID\\VID_044F&PID_0001\\6&1234&0&0000"])
# e) hide_paths: XInput-Geraet -> alle drei Pfade, dedupliziert
dev_xinput = {"deviceInstancePath": "HID\\VID_045E&PID_028E\\6&abcd&0&0000",
              "baseContainerDeviceInstancePath": "USB\\VID_045E&PID_028E\\5&abcd&0&1",
              "xusbDeviceInstancePath": "XUSB\\VID_045E&PID_028E\\6&abcd&0&0000"}
check("hidhide_hide_paths XInput alle drei", len(main.hidhide_hide_paths(dev_xinput)) == 3)
check("hidhide_hide_paths leer bei leeres Geraet", main.hidhide_hide_paths({}) == [])
# f) parse_devices: Container+Geraete flach, Name aus description/product
sample = json.dumps([
    {"friendlyName": "Simucube 2 Sport",
     "devices": [
         {"description": "Simucube 2 Sport", "product": "SC2",
          "deviceInstancePath": "HID\\VID_16C0&PID_04D8\\6&aa&0&0000"},
         {"description": "", "product": "Pedale",
          "deviceInstancePath": "HID\\VID_16C0&PID_04D9\\6&bb&0&0000"},
     ]},
    {"friendlyName": "Xbox Pad",
     "devices": [
         {"description": "Controller", "product": "Xbox",
          "deviceInstancePath": "HID\\VID_045E&PID_028E\\6&cc&0&0000",
          "baseContainerDeviceInstancePath": "USB\\VID_045E&PID_028E\\5&cc&0&1",
          "xusbDeviceInstancePath": "XUSB\\VID_045E&PID_028E\\6&cc&0&0000"},
     ]},
])
devs = main.hidhide_parse_devices(sample)
check("hidhide_parse_devices Anzahl", len(devs) == 3)
check("hidhide_parse_devices Namen",
      devs[0]["name"] == "Simucube 2 Sport" and devs[1]["name"] == "Pedale"
      and devs[2]["container"] == "Xbox Pad")
check("hidhide_parse_devices Pfade XInput", len(devs[2]["paths"]) == 3)
check("hidhide_parse_devices ungueltiges JSON", main.hidhide_parse_devices("kein json") == [])
# g) build_args: Reihenfolge inv-off, dev-hide, app-reg, cloak
args = main.hidhide_build_args(["HID\\A"], ["C:/x/SimHub.exe"], True)
check("hidhide_build_args Reihenfolge", args == [
    "--inv-off", "--dev-hide", "HID\\A", "--app-reg", "C:/x/SimHub.exe", "--cloak-on"])
check("hidhide_build_args cloak aus", main.hidhide_build_args([], [], False)[-1] == "--cloak-off")
# h) app_whitelist_paths: nur echte EXE-Apps, steam:// ignoriert, extras angehaengt
cfg4 = {"apps": [
    {"id": "raceroom", "path": "steam://rungameid/518790"},
    {"id": "simhub", "path": "C:/Program Files/SimHub/SimHubWPF.exe"},
    {"id": "crewchief", "path": "C:/Program Files/CrewChiefV4/CrewChiefV4.exe"},
], "hidhide": {"whitelist_apps": ["raceroom", "simhub"],
               "extra_whitelist": ["C:/Steam/RRRE.exe"]}}
wl = main.app_whitelist_paths(cfg4)
check("app_whitelist_paths filtert steam und nimmt EXE + Extra",
      wl == ["C:/Program Files/SimHub/SimHubWPF.exe", "C:/Steam/RRRE.exe"])

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


def test_profile_id_from_name():
    """0.3.3: Profil-IDs klein, alphanumerisch, Fallback bei Leertext."""
    assert mod.profile_id_from_name("Quali Warmup") == "quali_warmup"
    assert mod.profile_id_from_name("") == "profil"


def test_profile_add():
    """0.3.3: Eigenes Profil anlegen: Name, eindeutige ID, leere App-Liste."""
    cfg = {"profiles": [{"id": "rennabend", "name": "Rennabend", "apps": []}]}
    p = mod.profile_add(cfg, "Quali")
    assert p["name"] == "Quali" and p["id"] == "quali" and p["apps"] == []
    assert cfg["profiles"][-1] is p
    # gleicher Name -> Suffix _2
    p2 = mod.profile_add(cfg, "Quali")
    assert p2["id"] == "quali_2"
    # Leerer Name -> None, nichts angehaengt
    assert mod.profile_add(cfg, "   ") is None
    assert len(cfg["profiles"]) == 3
    # Leerer Name mit Whitespace wird normalisiert
    p3 = mod.profile_add(cfg, "  Test Lauf  ")
    assert p3["name"] == "Test Lauf"
