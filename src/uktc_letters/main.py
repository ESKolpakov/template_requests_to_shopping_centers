"""Точка входа приложения (см. также scripts/build_exe.spec для сборки в
единый .exe через PyInstaller)."""

from __future__ import annotations


def main() -> None:
    # Абсолютный импорт (не относительный) намеренно: когда приложение
    # запущено как собранный PyInstaller .exe, main.py выполняется как
    # отдельный скрипт без контекста пакета ("no known parent package"),
    # и относительный импорт `.gui.app` в этом случае падает. Абсолютный
    # импорт работает одинаково и в frozen .exe, и при обычном запуске
    # (`python -m uktc_letters.main`), пока папка src/ есть в sys.path.
    from uktc_letters.gui.app import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
