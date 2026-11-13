# -*- coding: utf-8 -*-
"""Update-Pruefung fuer R3E Cockpit (Muster: pitboss-r3e/updater.py).

Fragt das neueste GitHub-Release ab, vergleicht Tag gegen APP_VERSION und
laedt bei Bedarf den Inno-Setup-Installer herunter. Qt-frei und damit testbar.
"""
import json
import os
import re
import tempfile
import time
import urllib.request

RELEASES_API = "https://api.github.com/repos/Pfoetiman76/R3E-Cockpit/releases/latest"
ASSET_PREFIX = "R3ECockpit-Setup-"
USER_AGENT = "R3E-Cockpit-Updater"
RETRY_DELAYS = (0, 2, 5, 10)


def parse_version(text):
    """'v0.3.0' -> (0, 3, 0). Ungueltige Teile werden zu 0."""
    nums = re.findall(r"\d+", str(text or ""))
    return tuple(int(n) for n in nums[:4])


def is_newer(remote_tag, local_version):
    """True, wenn remote_tag (mit 'v') strikt neuer als local_version ist."""
    rt = parse_version(remote_tag)
    lv = parse_version(local_version)
    if not rt or not lv:
        return False
    return rt > lv


def _http_get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def pick_asset(assets):
    """Installer-Asset aus der Release-Liste waehlen."""
    for a in assets or []:
        name = str(a.get("name") or "")
        if name.startswith(ASSET_PREFIX) and name.endswith(".exe"):
            return a
    return None


def check_for_update(local_version, fetch=None, api_url=RELEASES_API):
    """Update-Status ermitteln.

    Rueckgabe dict mit:
      available: bool
      tag: str            Tag des neuesten Releases
      url / name: str     Download-URL und Dateiname des Installers (falls Update)
      error: str          Fehlermeldung (falls verfügbar False wegen Fehler)
    """
    fetch = fetch or _http_get_json
    last_err = None
    for delay in RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            data = fetch(api_url)
            tag = str(data.get("tag_name") or "").strip()
            asset = pick_asset(data.get("assets"))
            if not tag:
                return {"available": False, "error": "Release ohne Tag-Angabe"}
            if is_newer(tag, local_version) and asset:
                return {"available": True, "tag": tag,
                        "url": asset.get("browser_download_url") or "",
                        "name": asset.get("name") or ""}
            return {"available": False, "tag": tag}
        except Exception as exc:  # Netz/GitHub-Ausfaelle: weiter probieren
            last_err = exc
    return {"available": False,
            "error": "GitHub nicht erreichbar (%d Versuche): %s" % (len(RETRY_DELAYS), last_err)}


def download_asset(url, dest_dir=None, retries=3):
    """Installer herunterladen, Pfad zur Datei zurueckgeben oder None."""
    if not url:
        return None
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="r3ecockpit_update_")
    dest = os.path.join(dest_dir, os.path.basename(url.split("?")[0]) or "update.exe")
    delays = (0, 3, 8)
    for i in range(retries):
        try:
            if i:
                time.sleep(delays[min(i, len(delays) - 1)])
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as fh:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    fh.write(chunk)
            if os.path.getsize(dest) < 100000:
                raise OSError("Download unvollstaendig (< 100 KB)")
            return dest
        except Exception:
            continue
    return None


def run_installer(path):
    """Installer starten (App muss sich danach selbst beenden)."""
    if not path or not os.path.isfile(path):
        return False
    os.startfile(path)
    return True
