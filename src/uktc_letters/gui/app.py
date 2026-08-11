"""Главное окно приложения — вкладки согласно ТЗ п.1.1."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .state import AppState
from .tab_egrul import EgrulTab
from .tab_generate import GenerateTab
from .tab_settings import SettingsTab
from .tab_sources import SourcesTab
from .tab_templates import TemplatesTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Письма в УК ТЦ — ГБУ «МКМЦН»")
        self.geometry("900x700")

        self.state_ = AppState()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        notebook.add(TemplatesTab(notebook, self.state_), text="Шаблоны")
        notebook.add(SourcesTab(notebook, self.state_), text="Источники данных")
        notebook.add(SettingsTab(notebook, self.state_), text="Настройки")
        notebook.add(EgrulTab(notebook, self.state_), text="Проверка по ЕГРЮЛ")
        notebook.add(GenerateTab(notebook, self.state_), text="Генерация писем")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        self.state_.registry.close()
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
