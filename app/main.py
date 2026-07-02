import time
import core
import platform
import threading
import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from translation import TranslationEnum, get_string

RATE_LIMIT_SECONDS = 20  # 20 seconds between manual checks


STATUS_COLORS = {
    "progress": "#2980b9",
    "info": "gray60",
    "success": "#27ae60",
    "error": "#c0392b",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Collapsible section widget ────────────────────────────────────────────────


class CollapsibleSection(ctk.CTkFrame):
    """Titled group with a toggle button that shows/hides its children."""

    def __init__(self, parent, title: str, expanded: bool = True, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._title = title
        self._open = expanded

        self._btn = ctk.CTkButton(
            self,
            text=self._label(),
            anchor="w",
            height=32,
            corner_radius=6,
            fg_color=("gray80", "gray25"),
            hover_color=("gray70", "gray32"),
            text_color=("gray10", "gray90"),
            font=ctk.CTkFont(weight="bold"),
            command=self._toggle,
        )
        self._btn.grid(row=0, column=0, sticky="ew", pady=(6, 2))

        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.grid_columnconfigure(0, weight=1)
        if self._open:
            self._body.grid(row=1, column=0, sticky="ew", padx=(16, 0))

    def _label(self) -> str:
        return f"{'▼' if self._open else '▶'}  {self._title}"

    def _toggle(self):
        self.set_expanded(not self._open)

    def set_expanded(self, value: bool) -> None:
        if self._open == value:
            return
        self._open = value
        self._btn.configure(text=self._label())
        if self._open:
            self._body.grid(row=1, column=0, sticky="ew", padx=(16, 0))
        else:
            self._body.grid_remove()

    @property
    def body(self) -> ctk.CTkFrame:
        return self._body


# ── Main application ──────────────────────────────────────────────────────────


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        cfg = core.load_config()
        self._lang: str = cfg.get("lang", "en")

        self.geometry("720x720")
        self.minsize(600, 520)

        self._release = None
        self._groups: dict = {}
        self._vars: dict = {}
        self._sections: list = []
        self._installed_vars: dict = {}
        self._installed_names: set = set()  # filenames currently in dest folder
        self._tab_names: list = []
        self._active_tab_idx: int = 0
        self._is_loading: bool = False
        self._dest = ctk.StringVar(value=str(core.POE2_DIR))

        self._setup_ui()
        self.after(200, self._start_load)

    # ── Translation helper ────────────────────────────────────────────────────

    def t(self, key: str, *args) -> str:
        """Return the translated string for the current language, or fallback to English."""

        text = get_string(TranslationEnum(self._lang), key)

        return text.format(*args) if args else text

    # ── Layout ────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.title(self.t("window_title"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # Title row with settings gear
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 6))
        title_row.grid_columnconfigure(0, weight=1)
        self._title_lbl = ctk.CTkLabel(
            title_row,
            text=self.t("window_title"),
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        )
        self._title_lbl.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            title_row,
            text="⚙",
            width=36,
            height=36,
            command=self._open_settings,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=18),
        ).grid(row=0, column=1, sticky="e")

        # Version info card — label left, Check for Updates button right
        info = ctk.CTkFrame(self)
        info.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        info.grid_columnconfigure(0, weight=1)
        self._version_lbl = ctk.CTkLabel(info, text=self.t("ver_unknown"), anchor="w")
        self._version_lbl.grid(row=0, column=0, padx=12, pady=8, sticky="ew")
        self._check_update_btn = ctk.CTkButton(
            info,
            text=self.t("check_update"),
            width=170,
            state="disabled",  # enabled after first load completes
            command=self._on_check_update,
        )
        self._check_update_btn.grid(row=0, column=1, padx=(0, 8), pady=6)

        # Status + progress
        status_area = ctk.CTkFrame(self, fg_color="transparent")
        status_area.grid(row=2, column=0, sticky="ew", padx=16, pady=2)
        self._status_lbl = ctk.CTkLabel(
            status_area,
            text="",
            anchor="w",
            text_color="gray60",
            wraplength=670,
        )
        self._status_lbl.pack(fill="x")
        self._progress = ctk.CTkProgressBar(status_area)
        self._progress.set(0)

        # Destination row
        dest_row = ctk.CTkFrame(self)
        dest_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 2))
        dest_row.grid_columnconfigure(1, weight=1)
        self._dest_lbl = ctk.CTkLabel(
            dest_row, text=self.t("destination"), width=70, anchor="w"
        )
        self._dest_lbl.grid(row=0, column=0, padx=(10, 2), pady=6)
        ctk.CTkEntry(dest_row, textvariable=self._dest).grid(
            row=0, column=1, padx=2, pady=6, sticky="ew"
        )
        self._browse_btn = ctk.CTkButton(
            dest_row, text=self.t("browse"), width=80, command=self._browse
        )
        self._browse_btn.grid(row=0, column=2, padx=(2, 10), pady=6)
        self._open_directory_btn = ctk.CTkButton(
            dest_row,
            text=self.t("open_directory"),
            width=80,
            command=self._open_directory,
        )
        self._open_directory_btn.grid(row=0, column=3, padx=(1, 10), pady=6)

        # Tabview
        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=4, column=0, sticky="nsew", padx=16, pady=(2, 16))
        self._tab_names = [self.t("tab_install"), self.t("tab_installed")]
        for name in self._tab_names:
            self._tabs.add(name)

        self._setup_install_tab()
        self._setup_installed_tab()

    def _setup_install_tab(self):
        """Create the Install tab with scrollable filter list and buttons."""

        tab = self._tabs.tab(self._tab_names[0])
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(
            tab, label_text=self.t("install_list_label")
        )
        self._scroll.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        self._scroll.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._scroll, text=self.t("loading"), text_color="gray60").grid(
            row=0, column=0, pady=40
        )

        btn = ctk.CTkFrame(tab)
        btn.grid(row=1, column=0, sticky="ew")
        btn.grid_columnconfigure(2, weight=1)  # spacer

        self._collapse_btn = ctk.CTkButton(
            btn, text=self.t("collapse_all"), width=120, command=self._collapse_all
        )
        self._collapse_btn.grid(row=0, column=0, padx=(4, 2), pady=6)

        self._expand_btn = ctk.CTkButton(
            btn, text=self.t("expand_all"), width=120, command=self._expand_all
        )
        self._expand_btn.grid(row=0, column=1, padx=(0, 2), pady=6)

        # col 2 = spacer

        self._select_btn = ctk.CTkButton(
            btn, text=self.t("select_all"), width=105, command=self._select_all
        )
        self._select_btn.grid(row=0, column=3, padx=2, pady=6)

        self._deselect_btn = ctk.CTkButton(
            btn, text=self.t("deselect_all"), width=105, command=self._deselect_all
        )
        self._deselect_btn.grid(row=0, column=4, padx=2, pady=6)

        self._install_btn = ctk.CTkButton(
            btn,
            text=self.t("install_selected"),
            width=130,
            state="disabled",
            command=self._on_install,
        )
        self._install_btn.grid(row=0, column=5, padx=(2, 4), pady=6)

    def _setup_installed_tab(self):
        tab = self._tabs.tab(self._tab_names[1])
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        self._installed_scroll = ctk.CTkScrollableFrame(
            tab, label_text=self.t("installed_list_label")
        )
        self._installed_scroll.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        self._installed_scroll.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self._installed_scroll, text=self.t("click_refresh"), text_color="gray60"
        ).grid(row=0, column=0, pady=40)

        btn = ctk.CTkFrame(tab)
        btn.grid(row=1, column=0, sticky="ew")
        btn.grid_columnconfigure(1, weight=1)  # spacer

        self._refresh_btn = ctk.CTkButton(
            btn, text=self.t("refresh"), width=90, command=self._refresh_installed
        )
        self._refresh_btn.grid(row=0, column=0, padx=(4, 2), pady=6)

        # col 1 = spacer

        self._installed_select_btn = ctk.CTkButton(
            btn,
            text=self.t("select_all"),
            width=105,
            command=self._installed_select_all,
        )
        self._installed_select_btn.grid(row=0, column=2, padx=2, pady=6)

        self._installed_deselect_btn = ctk.CTkButton(
            btn,
            text=self.t("deselect_all"),
            width=105,
            command=self._installed_deselect_all,
        )
        self._installed_deselect_btn.grid(row=0, column=3, padx=2, pady=6)

        self._delete_btn = ctk.CTkButton(
            btn,
            text=self.t("delete_selected"),
            width=150,
            fg_color="#922b21",
            hover_color="#7b241c",
            state="disabled",
            command=self._on_delete,
        )
        self._delete_btn.grid(row=0, column=4, padx=(2, 4), pady=6)

    # ── Settings & localization ───────────────────────────────────────────────

    def _open_settings(self):
        """Open the settings dialog for language selection."""

        win = ctk.CTkToplevel(self)
        win.title(self.t("settings_title"))
        win.geometry("260x170")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.after(50, win.lift)

        ctk.CTkLabel(
            win,
            text=self.t("language"),
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(16, 8), padx=20, anchor="w")

        lang_var = ctk.StringVar(value=self._lang)
        for code, label in [("en", "English"), ("ru", "Русский")]:
            ctk.CTkRadioButton(win, text=label, variable=lang_var, value=code).pack(
                anchor="w", padx=28, pady=3
            )

        def _apply():
            chosen = lang_var.get()
            win.destroy()
            if chosen != self._lang:
                self._switch_language(chosen)

        ctk.CTkButton(win, text="OK", width=80, command=_apply).pack(pady=(14, 0))

    def _switch_language(self, lang: str) -> None:
        """Switch the application's language."""

        self._lang = lang
        cfg = core.load_config()
        cfg["lang"] = lang
        core.save_config(cfg)

        self.title(self.t("window_title"))
        self._title_lbl.configure(text=self.t("window_title"))
        self._dest_lbl.configure(text=self.t("destination"))
        self._browse_btn.configure(text=self.t("browse"))
        self._open_directory_btn.configure(text=self.t("open_directory"))
        self._check_update_btn.configure(text=self.t("check_update"))

        self._rebuild_tabs()

    def _rebuild_tabs(self) -> None:
        """Rebuild the tabview and its contents, preserving the active tab if possible."""

        try:
            current = self._tabs.get()
            self._active_tab_idx = next(
                (i for i, n in enumerate(self._tab_names) if n == current), 0
            )
        except Exception:
            pass

        self._tabs.destroy()
        self._tab_names = [self.t("tab_install"), self.t("tab_installed")]
        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=4, column=0, sticky="nsew", padx=16, pady=(2, 16))
        for name in self._tab_names:
            self._tabs.add(name)

        self._setup_install_tab()
        self._setup_installed_tab()

        if self._groups:
            self._populate_install_list()
            self._install_btn.configure(state="normal")
        self._populate_installed_list()

        self._tabs.set(self._tab_names[self._active_tab_idx])

    # ── Load / update check ───────────────────────────────────────────────────

    def _start_load(self, manual: bool = False) -> None:
        """Kick off the background load; enforces rate limit for manual calls."""

        if self._is_loading:
            return

        if manual:
            cfg = core.load_config()
            elapsed = time.time() - cfg.get("last_check", 0)
            remaining = RATE_LIMIT_SECONDS - elapsed
            if remaining > 0:
                sec = max(1, int(remaining))
                self._set_status(self.t("s_rate_limited", sec), "info")
                return

        self._is_loading = True
        self._check_update_btn.configure(state="disabled")
        threading.Thread(target=self._run_load, daemon=True).start()

    def _run_load(self) -> None:
        """Wraps _load() to guarantee cleanup regardless of how it exits."""

        try:
            self._load()
            cfg = core.load_config()
            cfg["last_check"] = time.time()
            cfg["lang"] = self._lang
            core.save_config(cfg)
        finally:
            self._is_loading = False
            self._ui(self._check_update_btn.configure, state="normal")

    def _load(self) -> None:
        """Load the latest release info, download archive if needed, and list filters."""

        self._ui(self._set_status, self.t("s_connecting"), "progress")
        try:
            self._release = core.get_latest_release()
        except Exception as exc:
            self._ui(self._set_status, self.t("err_github", exc), "error")
            return

        latest = self._release["tag_name"]
        cached = core.get_cached_version()

        if cached != latest or not core.CACHE_ZIP.exists():
            self._ui(self._set_status, self.t("s_downloading", latest), "progress")
            self._ui(self._show_progress)
            try:
                core.download_archive(
                    self._release["zipball_url"],
                    on_progress=lambda p: self._ui(self._progress.set, p),
                )
                core.save_cached_version(latest)
            except Exception as exc:
                self._ui(self._hide_progress)
                self._ui(self._set_status, self.t("err_download", exc), "error")
                return
            self._ui(self._hide_progress)
        else:
            self._ui(self._set_status, self.t("s_using_cache"), "info")

        cached = core.get_cached_version()
        self._ui(self._update_version_label, latest, cached)

        try:
            self._groups = core.list_filters()
        except Exception as exc:
            self._ui(self._set_status, self.t("err_archive", exc), "error")
            return

        # Scan destination for currently installed filters (smart pre-selection)
        dest = Path(self._dest.get())
        self._installed_names = (
            {f.name for f in dest.glob("*.filter")} if dest.exists() else set()
        )

        total = sum(len(v) for v in self._groups.values())
        self._ui(self._populate_install_list)
        self._ui(self._populate_installed_list)
        self._ui(self._set_status, self.t("s_found", total), "info")
        self._ui(self._install_btn.configure, state="normal")

    def _on_check_update(self) -> None:
        """User clicked the Check for Updates button."""

        self._start_load(manual=True)

    def _populate_install_list(self):
        """Populate the Install tab with checkboxes for each filter in the groups."""

        for w in self._scroll.winfo_children():
            w.destroy()
        self._vars.clear()
        self._sections.clear()

        for idx, group in enumerate(
            sorted(self._groups, key=lambda k: ("" != k, k.lower()))
        ):
            title = self.t("main_filters") if group == "" else group
            section = CollapsibleSection(self._scroll, title=title, expanded=True)
            section.grid(row=idx, column=0, sticky="ew", padx=4)
            self._sections.append(section)

            for entry in sorted(self._groups[group], key=lambda p: Path(p).name):
                filename = Path(entry).name
                # Smart pre-selection: tick filters already in PoE2 folder.
                # Fall back to main-filters-only when nothing is installed yet.
                if self._installed_names:
                    pre_checked = filename in self._installed_names
                else:
                    pre_checked = group == ""
                var = ctk.BooleanVar(value=pre_checked)
                self._vars[entry] = var
                ctk.CTkCheckBox(section.body, text=filename, variable=var).pack(
                    anchor="w", padx=4, pady=1
                )

    # ── Install tab actions ───────────────────────────────────────────────────

    def _collapse_all(self):
        for s in self._sections:
            s.set_expanded(False)

    def _expand_all(self):
        for s in self._sections:
            s.set_expanded(True)

    def _select_all(self):
        for v in self._vars.values():
            v.set(True)

    def _deselect_all(self):
        for v in self._vars.values():
            v.set(False)

    def _on_install(self):
        selected = [p for p, v in self._vars.items() if v.get()]
        if not selected:
            self._set_status(self.t("err_no_selection"), "error")
            return
        self._install_btn.configure(state="disabled")
        threading.Thread(target=self._do_install, args=(selected,), daemon=True).start()

    def _do_install(self, selected: list):
        self._ui(self._set_status, self.t("s_installing", len(selected)), "progress")
        try:
            n = core.install_filters(selected, Path(self._dest.get()))
            for entry in selected:
                self._installed_names.add(Path(entry).name)
            self._ui(
                self._set_status,
                self.t("s_done_install", n, self._dest.get()),
                "success",
            )
            self._ui(self._populate_installed_list)
        except Exception as exc:
            self._ui(self._set_status, self.t("err_install", exc), "error")
        finally:
            self._ui(self._install_btn.configure, state="normal")

    # ── Installed tab actions ─────────────────────────────────────────────────

    def _refresh_installed(self):
        self._populate_installed_list()

    def _populate_installed_list(self):
        for w in self._installed_scroll.winfo_children():
            w.destroy()
        self._installed_vars.clear()

        dest = Path(self._dest.get())
        if not dest.exists():
            ctk.CTkLabel(
                self._installed_scroll,
                text=self.t("folder_not_found", dest),
                text_color="gray60",
            ).grid(row=0, column=0, pady=40)
            self._delete_btn.configure(state="disabled")
            return

        filters = sorted(dest.glob("*.filter"), key=lambda p: p.name)
        if not filters:
            ctk.CTkLabel(
                self._installed_scroll,
                text=self.t("no_filter_files"),
                text_color="gray60",
            ).grid(row=0, column=0, pady=40)
            self._delete_btn.configure(state="disabled")
            return

        for i, f in enumerate(filters):
            size_kb = f.stat().st_size // 1024
            var = ctk.BooleanVar(value=False)
            self._installed_vars[str(f)] = var

            row_frame = ctk.CTkFrame(self._installed_scroll, fg_color="transparent")
            row_frame.grid(row=i, column=0, sticky="ew", padx=4, pady=1)
            row_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkCheckBox(row_frame, text=f.name, variable=var).grid(
                row=0, column=0, sticky="w"
            )
            ctk.CTkLabel(
                row_frame,
                text=f"{size_kb} KB",
                text_color="gray55",
                width=64,
                anchor="e",
            ).grid(row=0, column=1, sticky="e", padx=(8, 0))

        self._delete_btn.configure(state="normal")

    def _installed_select_all(self):
        for v in self._installed_vars.values():
            v.set(True)

    def _installed_deselect_all(self):
        for v in self._installed_vars.values():
            v.set(False)

    def _on_delete(self):
        selected = [p for p, v in self._installed_vars.items() if v.get()]
        if not selected:
            self._set_status(self.t("err_no_delete_sel"), "error")
            return
        if not messagebox.askyesno(
            self.t("dlg_del_title"),
            self.t("dlg_del_msg", len(selected), self._dest.get()),
        ):
            return

        errors = []
        for path_str in selected:
            try:
                Path(path_str).unlink()
                self._installed_names.discard(Path(path_str).name)
            except Exception as exc:
                errors.append(f"{Path(path_str).name}: {exc}")

        if errors:
            self._set_status(self.t("s_deleted_errors", "; ".join(errors)), "error")
        else:
            self._set_status(self.t("s_done_delete", len(selected)), "success")
        self._populate_installed_list()

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _update_version_label(self, latest: str, cached: str):
        if not cached:
            text = self.t("ver_new", latest)
        elif cached == latest:
            text = self.t("ver_ok", latest)
        else:
            text = self.t("ver_update", latest, cached)
        self._version_lbl.configure(text=text)

    def _set_status(self, msg: str, kind: str = "info"):
        self._status_lbl.configure(
            text=msg, text_color=STATUS_COLORS.get(kind, "gray60")
        )

    def _show_progress(self):
        self._progress.pack(fill="x", pady=(4, 0))

    def _hide_progress(self):
        self._progress.pack_forget()

    def _browse(self):
        path = filedialog.askdirectory(initialdir=self._dest.get())
        if path:
            self._dest.set(path)

    def _open_directory(self):
        """Open the destination folder in the system file explorer."""
        path = self._dest.get()
        if not Path(path).exists():
            messagebox.showerror(self.title(), self.t("folder_not_found", path))
            return
        try:
            system = platform.system()
            if system == "Windows":
                # explorer always exits with code 1 even on success — don't check
                subprocess.run(
                    ["explorer", path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif system == "Darwin":
                subprocess.run(
                    ["open", path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    ["xdg-open", path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            messagebox.showerror(self.title(), f"Could not open directory:\n{e}")

    def _ui(self, fn, *args, **kwargs):
        """Post a UI call to the main thread from any background thread."""

        self.after(0, lambda: fn(*args, **kwargs))


if __name__ == "__main__":
    app = App()
    app.mainloop()
