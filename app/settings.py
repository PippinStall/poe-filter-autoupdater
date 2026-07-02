import sys
from pathlib import Path

# Version number of the application
APP_VERSION = "0.2.0"
# Rate limit for checking updates (in seconds)
RATE_LIMIT_SECONDS = 20  # 20 seconds between manual checks
# Color codes for different status messages
STATUS_COLORS = {
    "progress": "#2980b9",
    "info": "gray60",
    "success": "#27ae60",
    "error": "#c0392b",
}
# GitHub repository and API settings
REPO = "NeverSinkDev/NeverSink-Filter-for-PoE2"
# API URL for fetching the latest release information
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
# Headers for the HTTP requests to GitHub API
HEADERS = {"User-Agent": "PoE2-Filter-Updater"}
# File paths for caching and configuration
BASE_DIR: Path = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).parent.parent
)
# Directory for storing application data (cache, config, etc.)
APP_DIR = BASE_DIR / "data"
# Create the APP_DIR if it doesn't exist
APP_DIR.mkdir(exist_ok=True)
# Path to the cached zip file of filters
CACHE_ZIP = APP_DIR / "filter_cache.zip"
# Path to the cached version string file
VERSION_FILE = APP_DIR / "cached_version.txt"
# Path to the configuration file
CONFIG_FILE = APP_DIR / "config.json"
# Path to the Path of Exile 2 installation directory (default location)
POE2_DIR = Path.home() / "Documents" / "My Games" / "Path of Exile 2"
