# PoE2 Filter Autoupdater

PowerShell script that automatically downloads and updates the [NeverSink loot filter](https://github.com/NeverSinkDev/NeverSink-Filter-for-PoE2) for Path of Exile 2.

On each run it checks the latest GitHub release. If a newer version is available — downloads the archive, extracts only `.filter` files, and copies them directly to the PoE2 filter directory. Temporary files are cleaned up automatically.

## Requirements

- Windows 10/11
- PowerShell 5.1 or later (included with Windows)
- Internet connection

## Setup

### 1. Download the script

Clone the repo or download `updater.ps1` directly:

```
git clone https://github.com/<your-username>/poe-filter-autoupdater.git
```

### 2. Allow script execution (one-time)

PowerShell blocks unsigned scripts by default. Open PowerShell **as Administrator** and run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 3. Configure (optional)

Open `updater.ps1` and edit the **SETTINGS** block at the top:

```powershell
$repo         = "NeverSinkDev/NeverSink-Filter-for-PoE2"  # GitHub repo (no need to change)
$poeFilterDir = "$env:USERPROFILE\Documents\My Games\Path of Exile 2"  # Filter destination
```

The default destination path matches where PoE2 reads filters on Windows.

## Usage

### Manual run

Right-click `updater.ps1` → **Run with PowerShell**, or from a terminal:

```powershell
.\updater.ps1
```

### Automatic updates on Windows startup (Task Scheduler)

1. Open **Task Scheduler** → *Create Basic Task*
2. Trigger: **At log on**
3. Action: **Start a program**
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\updater.ps1"`
4. Finish.

The script exits immediately if no update is available, so it won't slow down your login.

## How it works

1. Calls the GitHub API to get the latest release tag.
2. Compares it to `current_version.txt` stored next to the script.
3. If versions differ — downloads the source archive via `zipball_url`.
4. Extracts only `*.filter` files into a temp folder, then copies them to `$poeFilterDir`.
5. Cleans up all temp files and saves the new version tag.

## File layout

```
poe-filter-autoupdater/
├── updater.ps1          # Main script
├── current_version.txt  # Created on first run (gitignored)
├── .gitignore
└── README.md
```

## License

MIT
