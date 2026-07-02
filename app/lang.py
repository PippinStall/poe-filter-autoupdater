from enum import StrEnum


class LocalizationEnum(StrEnum):
    EN = "en"
    RU = "ru"


# ── Translations ──────────────────────────────────────────────────────────────

LOCALIZATION_STRINGS: dict = {
    LocalizationEnum.EN: {
        "window_title": "PoE 2 NeverSink Filter Updater",
        "settings_title": "Settings",
        "language": "Language",
        "destination": "Destination:",
        "check_update": "Check for Updates",
        "tab_install": "Install",
        "tab_installed": "Installed",
        "collapse_all": "Collapse All",
        "expand_all": "Expand All",
        "select_all": "Select All",
        "deselect_all": "Deselect All",
        "install_selected": "Install Selected",
        "refresh": "Refresh",
        "delete_selected": "Delete Selected",
        "install_list_label": "Select filters to install",
        "installed_list_label": "Filters in destination folder",
        "main_filters": "Main Filters",
        "loading": "Loading…",
        "click_refresh": "Click Refresh to load installed filters.",
        "folder_not_found": "Folder not found:\n{}",
        "no_filter_files": "No .filter files found in destination folder.",
        # status — progress (blue)
        "s_connecting": "Fetching release info from GitHub…",
        "s_downloading": "Downloading {}…",
        "s_installing": "Installing {} filter(s)…",
        # status — info (gray)
        "s_using_cache": "Using cached archive.",
        "s_found": "Found {} filters. Select what to install.",
        "s_rate_limited": "Too soon — next check available in {} seconds.",
        # status — success (green)
        "s_done_install": "Done! {} filter(s) copied to: {}",
        "s_done_delete": "Deleted {} filter(s).",
        # status — error (red)
        "s_deleted_errors": "Deleted with errors: {}",
        "err_github": "GitHub error: {}",
        "err_download": "Download error: {}",
        "err_archive": "Archive error: {}",
        "err_install": "Install error: {}",
        "err_no_selection": "No filters selected.",
        "err_no_delete_sel": "No filters selected for deletion.",
        # version card
        "ver_unknown": "Connecting to GitHub…",
        "ver_new": "Latest: {}   (not yet installed)",
        "ver_ok": "Version: {}   ✓  Up to date",
        "ver_update": "Latest: {}   |   Installed: {}   — update available",
        # confirm dialog
        "dlg_del_title": "Confirm deletion",
        "dlg_del_msg": "Delete {} filter file(s) from:\n{}\n\nThis cannot be undone.",
        "lang_type": "English",
    },
    LocalizationEnum.RU: {
        "window_title": "Обновление фильтров NeverSink для PoE 2",
        "settings_title": "Настройки",
        "language": "Язык",
        "destination": "Папка:",
        "check_update": "Проверить обновления",
        "tab_install": "Установка",
        "tab_installed": "Установлено",
        "collapse_all": "Свернуть всё",
        "expand_all": "Развернуть всё",
        "select_all": "Выбрать все",
        "deselect_all": "Снять выбор",
        "install_selected": "Установить",
        "refresh": "Обновить",
        "delete_selected": "Удалить выбранные",
        "install_list_label": "Выберите фильтры для установки",
        "installed_list_label": "Фильтры в папке назначения",
        "main_filters": "Основные фильтры",
        "loading": "Загрузка…",
        "click_refresh": "Нажмите «Обновить» для загрузки списка.",
        "folder_not_found": "Папка не найдена:\n{}",
        "no_filter_files": "В папке назначения нет файлов .filter.",
        # status — progress (blue)
        "s_connecting": "Получение информации о релизе…",
        "s_downloading": "Загрузка {}…",
        "s_installing": "Установка {} фильтр(ов)…",
        # status — info (gray)
        "s_using_cache": "Используется кэшированный архив.",
        "s_found": "Найдено {} фильтров. Выберите нужные.",
        "s_rate_limited": "Слишком рано — следующая проверка через {} секунд.",
        # status — success (green)
        "s_done_install": "Готово! {} фильтр(ов) скопировано в: {}",
        "s_done_delete": "Удалено {} фильтр(ов).",
        # status — error (red)
        "s_deleted_errors": "Удалено с ошибками: {}",
        "err_github": "Ошибка GitHub: {}",
        "err_download": "Ошибка загрузки: {}",
        "err_archive": "Ошибка архива: {}",
        "err_install": "Ошибка установки: {}",
        "err_no_selection": "Не выбрано ни одного фильтра.",
        "err_no_delete_sel": "Не выбрано ни одного фильтра для удаления.",
        # version card
        "ver_unknown": "Подключение к GitHub…",
        "ver_new": "Последняя: {}   (не установлена)",
        "ver_ok": "Версия: {}   ✓  Актуальная",
        "ver_update": "Последняя: {}   |   Установлена: {}   — доступно обновление",
        # confirm dialog
        "dlg_del_title": "Подтверждение удаления",
        "dlg_del_msg": "Удалить {} файл(ов) из:\n{}\n\nОтменить нельзя.",
        "lang_type": "Русский",
    },
}


def get_localized(lang: LocalizationEnum, key: str) -> str:
    """Return the translated string for the given language and key."""

    return LOCALIZATION_STRINGS.get(
        lang, LOCALIZATION_STRINGS[LocalizationEnum.EN]
    ).get(key, key)


def get_language_type(lang: LocalizationEnum) -> str:
    """Return the display name of the language for the given language code."""

    return LOCALIZATION_STRINGS.get(
        lang, LOCALIZATION_STRINGS[LocalizationEnum.EN]
    ).get("lang_type", "Unknown")
