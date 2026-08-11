"""Точка входа приложения (см. также scripts/build_exe.spec для сборки в
единый .exe через PyInstaller)."""

from __future__ import annotations


def main() -> None:
    from .gui.app import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
