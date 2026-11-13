# -*- coding: utf-8 -*-
"""Tests fuer die Qt-freie Update-Logik (updater.py)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import updater

fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)

# 1) parse_version
check("parse einfach", updater.parse_version("v0.3.0") == (0, 3, 0))
check("parse mit 'v'", updater.parse_version("0.2.10") == (0, 2, 10))
check("parse leer", updater.parse_version("") == ())

# 2) is_newer
check("neuer Tag", updater.is_newer("v0.3.0", "0.2.0"))
check("gleicher Stand", not updater.is_newer("v0.2.0", "0.2.0"))
check("aelterer Tag", not updater.is_newer("v0.1.9", "0.2.0"))
check("ungueltig nie neu", not updater.is_newer("", "0.2.0"))

# 3) pick_asset
assets = [
    {"name": "quelltext.zip"},
    {"name": "R3ECockpit-Setup-0.3.0.exe", "browser_download_url": "https://x/setup.exe"},
    {"name": "sonst.exe"},
]
picked = updater.pick_asset(assets)
check("Installer-Asset erkannt", picked and picked["name"].startswith("R3ECockpit-Setup-"))
check("Asset-Liste leer", updater.pick_asset([]) is None)
check("Asset-Liste None", updater.pick_asset(None) is None)

# 4) check_for_update mit Fake-Fetch
def make_release(tag, with_asset=True):
    return {"tag_name": tag,
            "assets": ([{"name": "R3ECockpit-Setup-%s.exe" % tag.lstrip("v"),
                         "browser_download_url": "https://x/%s.exe" % tag}] if with_asset else [])}

res = updater.check_for_update("0.2.0", fetch=lambda url: make_release("v0.3.0"))
check("Update verfuegbar", res["available"] and res["tag"] == "v0.3.0")
check("Update-URL uebergeben", res.get("url", "").endswith("v0.3.0.exe"))

res = updater.check_for_update("0.3.0", fetch=lambda url: make_release("v0.3.0"))
check("aktuell -> kein Update", not res["available"])

res = updater.check_for_update("0.2.0", fetch=lambda url: make_release("v0.3.0", with_asset=False))
check("Update ohne Installer-Asset -> kein Update", not res["available"])

# 5) Retry bei GitHub-Fehlern (kurze Delays, damit der Test schnell ist)
updater.RETRY_DELAYS = (0, 0, 0, 0)
calls = {"n": 0}
def flaky(url):
    calls["n"] += 1
    if calls["n"] < 3:
        raise OSError("504")
    return make_release("v0.3.0")
res = updater.check_for_update("0.2.0", fetch=flaky)
check("Retry greift (3. Versuch ok)", res["available"] and calls["n"] == 3)

def always_down(url):
    raise OSError("504")
res = updater.check_for_update("0.2.0", fetch=always_down)
check("alle Versuche fehlgeschlagen -> Fehlermeldung", not res["available"] and "nicht erreichbar" in res.get("error", ""))

# 6) check_for_update lokal gegen echtes GitHub (Netz optional; nur Hinweis)
print()
print("ERGEBNIS: %s" % ("ALLE TESTS BESTANDEN" if not fails else "FEHLGESCHLAGEN: %s" % fails))
sys.exit(1 if fails else 0)
