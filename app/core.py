import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "NeverSinkDev/NeverSink-Filter-for-PoE2"
_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
_HEADERS = {"User-Agent": "PoE2-Filter-Updater"}

APP_DIR: Path = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).parent
)
CACHE_ZIP = APP_DIR / "filter_cache.zip"
_VERSION_FILE = APP_DIR / "cached_version.txt"
_CONFIG_FILE = APP_DIR / "config.json"
POE2_DIR = Path.home() / "Documents" / "My Games" / "Path of Exile 2"


def load_config() -> dict:
    """Load config.json if it exists, otherwise return an empty dict."""

    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass

    return {}


def save_config(data: dict) -> None:
    """Save config.json with the provided data."""

    _CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_latest_release() -> dict:
    """Return the latest release info from GitHub API."""

    req = urllib.request.Request(_API_URL, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_cached_version() -> str:
    """Return the cached version string, or empty string if not cached."""

    return _VERSION_FILE.read_text().strip() if _VERSION_FILE.exists() else ""


def save_cached_version(version: str) -> None:
    """Save the cached version string to file."""

    _VERSION_FILE.write_text(version)


def download_archive(url: str, on_progress=None) -> None:
    """Download the zip archive to CACHE_ZIP, calling on_progress(fraction) if provided."""

    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        with open(CACHE_ZIP, "wb") as f:
            while chunk := resp.read(32768):
                f.write(chunk)
                done += len(chunk)
                if on_progress and total:
                    on_progress(done / total)


def list_filters() -> dict:
    """Return {group: [zip_entry, ...]}. Empty string key = root-level (Main Filters)."""

    groups: dict = {}
    with zipfile.ZipFile(CACHE_ZIP) as zf:
        for entry in sorted(zf.namelist()):
            if not entry.endswith(".filter"):
                continue

            parts = Path(entry).parts
            if len(parts) < 2:
                continue

            rel = parts[1:]  # strip GitHub-generated root prefix (repo-name-hash/)
            group = "" if len(rel) == 1 else rel[0]
            groups.setdefault(group, []).append(entry)

    return groups


def install_filters(entries: list, dest: Path) -> int:
    """Extract selected zip entries to dest. Returns number of installed filters."""

    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CACHE_ZIP) as zf:
        for entry in entries:
            with zf.open(entry) as src, open(dest / Path(entry).name, "wb") as dst:
                shutil.copyfileobj(src, dst)

    return len(entries)
