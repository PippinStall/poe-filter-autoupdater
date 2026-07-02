import time
import core
import lang
import settings
import platform
import threading
import subprocess
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

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

        self.minsize(600, 520)
        core.center(self, 720, 720)

        self._release = None
        self._groups: dict = {}
        self._vars: dict = {}
        self._sections: list = []
        self._installed_vars: dict = {}
        self._installed_names: set = set()  # filenames currently in dest folder
        self._tab_names: list = []
        self._active_tab_idx: int = 0
        self._is_loading: bool = False
        self._dest = ctk.StringVar(value=cfg.get("dest", str(settings.POE2_DIR)))

        self._setup_ui()
        self.after(200, self._start_load)

    # ── Translation helper ────────────────────────────────────────────────────

    def t(self, key: str, *args) -> str:
        """Return the translated string for the current language, or fallback to English."""

        text = lang.get_localized(lang.LocalizationEnum(self._lang), key)

        return text.format(*args) if args else text

    # ── Layout ────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        """Create the main window layout."""

        self.title(self.t("window_title"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # tabview expands

        # Header row: title + version label (left) | ↻ update | ⚙ settings (right)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        header.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew")
        left.grid_columnconfigure(0, weight=1)

        self._version_lbl = ctk.CTkLabel(
            left,
            text=self.t("ver_unknown"),
            font=ctk.CTkFont(size=12),
            text_color="gray55",
            anchor="w",
        )
        self._version_lbl.grid(row=1, column=0, sticky="w")

        self._check_update_btn = ctk.CTkButton(
            header,
            text="↻",
            width=40,
            height=40,
            state="disabled",
            command=self._on_check_update,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=22),
        )
        self._check_update_btn.grid(row=0, column=1, padx=(4, 2), sticky="e")

        self._settings_btn = ctk.CTkButton(
            header,
            text="⚙",
            width=40,
            height=40,
            command=self._open_settings,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=18),
        )
        self._settings_btn.grid(row=0, column=2, sticky="e")

        # Status + progress
        status_area = ctk.CTkFrame(self, fg_color="transparent")
        status_area.grid(row=1, column=0, sticky="ew", padx=16, pady=2)
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

        # Tabview
        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=(2, 16))
        self._tab_names = [self.t("tab_install"), self.t("tab_installed")]
        for name in self._tab_names:
            self._tabs.add(name)

        self._setup_install_tab()
        self._setup_installed_tab()

        # App version footer
        ctk.CTkLabel(
            self,
            text=f"v{settings.APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color="gray45",
            anchor="e",
        ).grid(row=3, column=0, sticky="e", padx=18, pady=(0, 6))

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
        """Create the Installed tab with scrollable list of installed filters and buttons."""

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
        win.resizable(False, False)
        core.center(win, 420, 300)
        win.transient(self)
        win.grab_set()
        win.after(50, win.lift)

        # Language section
        ctk.CTkLabel(
            win,
            text=self.t("language"),
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(pady=(16, 6), padx=20, anchor="w", fill="x")

        lang_var = ctk.StringVar(value=self._lang)
        for code, label in [
            (
                lang.LocalizationEnum.EN,
                lang.get_language_type(lang.LocalizationEnum.EN),
            ),
            (
                lang.LocalizationEnum.RU,
                lang.get_language_type(lang.LocalizationEnum.RU),
            ),
        ]:
            ctk.CTkRadioButton(win, text=label, variable=lang_var, value=code).pack(
                anchor="w", padx=28, pady=3
            )

        # Destination section
        ctk.CTkLabel(
            win,
            text=self.t("destination"),
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(pady=(16, 6), padx=20, anchor="w", fill="x")

        dest_var = ctk.StringVar(value=self._dest.get())

        dest_row = ctk.CTkFrame(win, fg_color="transparent")
        dest_row.pack(fill="x", padx=20, pady=(0, 4))
        dest_row.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(dest_row, textvariable=dest_var).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )

        self._browse_btn = ctk.CTkButton(
            dest_row,
            text="⁝",
            width=40,
            height=40,
            command=lambda: self._browse(dest_var),
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=22),
        )
        self._browse_btn.grid(row=0, column=1, padx=(0, 4))

        self._open_directory_btn = ctk.CTkButton(
            dest_row,
            text="⇢",
            width=40,
            height=40,
            command=lambda: self._open_directory(dest_var.get()),
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray70"),
            font=ctk.CTkFont(size=22),
        )
        self._open_directory_btn.grid(row=0, column=2, padx=(0, 4))

        def _apply():
            chosen_lang = lang_var.get()
            chosen_dest = dest_var.get()
            win.destroy()
            self._dest.set(chosen_dest)
            cfg = core.load_config()
            cfg["dest"] = chosen_dest
            core.save_config(cfg)
            if chosen_lang != self._lang:
                self._switch_language(chosen_lang)

        ctk.CTkButton(win, text="OK", width=80, command=_apply).pack(pady=(16, 0))

    def _switch_language(self, lang: str) -> None:
        """Switch the application's language."""

        self._lang = lang
        cfg = core.load_config()
        cfg["lang"] = lang
        core.save_config(cfg)

        self.title(self.t("window_title"))

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
        self._tabs.grid(row=2, column=0, sticky="nsew", padx=16, pady=(2, 16))
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
            remaining = settings.RATE_LIMIT_SECONDS - elapsed
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

        if cached != latest or not settings.CACHE_ZIP.exists():
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
        """Install the selected filters in the destination folder."""

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
        """Refresh the Installed tab by repopulating the list of installed filters."""

        self._populate_installed_list()

    def _populate_installed_list(self):
        """Populate the Installed tab with checkboxes for each filter in the destination folder."""

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
            text=msg, text_color=settings.STATUS_COLORS.get(kind, "gray60")
        )

    def _show_progress(self):
        self._progress.pack(fill="x", pady=(4, 0))

    def _hide_progress(self):
        self._progress.pack_forget()

    def _browse(self, dest_var=None):
        var = dest_var if dest_var is not None else self._dest
        path = filedialog.askdirectory(initialdir=var.get())
        if path:
            var.set(path)

    def _open_directory(self, path=None):
        """Open the destination folder in the system file explorer."""
        if path is None:
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
