"""Вкладка «Источники данных» (ТЗ, раздел 3): загрузка выгрузки объектов
торговли и справочника УК/ТЦ — независимо друг от друга, с возможностью
перезагрузки в любой момент."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..contacts_source import ContactsIndex, load_contacts
from ..objects_source import group_by_building, load_trade_objects
from .state import AppState


class SourcesTab(ttk.Frame):
    def __init__(self, parent, state: AppState):
        super().__init__(parent, padding=12)
        self.state = state

        objects_frame = ttk.LabelFrame(self, text="Выгрузка объектов торговли (Реестр ТО)")
        objects_frame.pack(fill="x", pady=6)
        self.objects_path_var = tk.StringVar(value=state.settings.objects_source_path or "(не загружено)")
        ttk.Label(objects_frame, textvariable=self.objects_path_var, wraplength=560).pack(
            anchor="w", padx=8, pady=4
        )
        ttk.Button(
            objects_frame, text="Загрузить / перезагрузить...", command=self._load_objects
        ).pack(anchor="w", padx=8, pady=(0, 8))
        self.objects_summary_var = tk.StringVar(value="")
        ttk.Label(objects_frame, textvariable=self.objects_summary_var).pack(
            anchor="w", padx=8, pady=(0, 8)
        )

        contacts_frame = ttk.LabelFrame(self, text="Справочник контактов УК/ТЦ")
        contacts_frame.pack(fill="x", pady=6)
        self.contacts_path_var = tk.StringVar(value=state.settings.contacts_source_path or "(не загружено)")
        ttk.Label(contacts_frame, textvariable=self.contacts_path_var, wraplength=560).pack(
            anchor="w", padx=8, pady=4
        )
        ttk.Button(
            contacts_frame, text="Загрузить / перезагрузить...", command=self._load_contacts
        ).pack(anchor="w", padx=8, pady=(0, 8))
        self.contacts_summary_var = tk.StringVar(value="")
        ttk.Label(contacts_frame, textvariable=self.contacts_summary_var).pack(
            anchor="w", padx=8, pady=(0, 8)
        )

        if state.objects_rows:
            self._update_objects_summary()
        if state.contact_records:
            self._update_contacts_summary()

    def _load_objects(self) -> None:
        path = filedialog.askopenfilename(
            title="Выбрать выгрузку объектов торговли",
            filetypes=[("Excel файлы", "*.xlsx *.xls")],
        )
        if not path:
            return
        try:
            rows = load_trade_objects(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка загрузки", str(exc))
            return
        self.state.objects_rows = rows
        self.state.building_groups = group_by_building(rows)
        self.state.settings.objects_source_path = path
        self.state.save_settings()
        self.objects_path_var.set(path)
        self._update_objects_summary()

    def _update_objects_summary(self) -> None:
        self.objects_summary_var.set(
            f"Строк: {len(self.state.objects_rows)}, зданий (писем): "
            f"{len(self.state.building_groups)}"
        )

    def _load_contacts(self) -> None:
        path = filedialog.askopenfilename(
            title="Выбрать справочник УК/ТЦ", filetypes=[("Excel файлы", "*.xlsx *.xls")]
        )
        if not path:
            return
        try:
            records = load_contacts(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка загрузки", str(exc))
            return
        self.state.contact_records = records
        self.state.contacts_index = ContactsIndex(records)
        self.state.settings.contacts_source_path = path
        self.state.save_settings()
        self.contacts_path_var.set(path)
        self._update_contacts_summary()

    def _update_contacts_summary(self) -> None:
        self.contacts_summary_var.set(f"Строк в справочнике: {len(self.state.contact_records)}")
