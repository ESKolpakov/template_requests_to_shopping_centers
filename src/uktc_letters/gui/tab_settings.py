"""Вкладка «Настройки» (ТЗ, раздел 7)."""

from __future__ import annotations

import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from .state import AppState


class SettingsTab(ttk.Frame):
    def __init__(self, parent, state: AppState):
        super().__init__(parent, padding=12)
        self.state = state
        s = state.settings

        form = ttk.Frame(self)
        form.pack(fill="x")

        self.executor_name_var = tk.StringVar(value=s.executor_name)
        self.executor_phone_var = tk.StringVar(value=s.executor_phone)
        self.signatory_var = tk.StringVar(value=s.signatory_name)
        self.deadline_days_var = tk.StringVar(value=str(s.deadline_days))
        self.downloads_dir_var = tk.StringVar(value=s.downloads_dir)

        row = 0
        for label, var in [
            ("Исполнитель (ФИО):", self.executor_name_var),
            ("Телефон исполнителя:", self.executor_phone_var),
            ("Подписант:", self.signatory_var),
            ("Длительность срока (календарных дней):", self.deadline_days_var),
            ("Папка загрузок браузера (для поиска PDF ЕГРЮЛ):", self.downloads_dir_var),
        ]:
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=var, width=42).grid(
                row=row, column=1, sticky="w", padx=8, pady=4
            )
            row += 1

        holidays_frame = ttk.LabelFrame(
            self, text="Праздничные/нерабочие дни (ГГГГ-ММ-ДД) — влияют на срок п.4.3"
        )
        holidays_frame.pack(fill="both", expand=True, pady=(12, 0))

        list_frame = ttk.Frame(holidays_frame)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.holidays_listbox = tk.Listbox(list_frame, height=10)
        self.holidays_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, command=self.holidays_listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.holidays_listbox.configure(yscrollcommand=scrollbar.set)
        for d in sorted(s.holidays):
            self.holidays_listbox.insert("end", d)

        add_frame = ttk.Frame(holidays_frame)
        add_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.new_holiday_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_holiday_var, width=14).pack(side="left")
        ttk.Button(add_frame, text="Добавить", command=self._add_holiday).pack(
            side="left", padx=6
        )
        ttk.Button(add_frame, text="Удалить выбранное", command=self._remove_holiday).pack(
            side="left"
        )
        ttk.Button(
            add_frame,
            text="Добавить базовый набор на текущий/следующий год",
            command=self._add_defaults,
        ).pack(side="left", padx=6)

        ttk.Button(self, text="Сохранить настройки", command=self._save).pack(
            anchor="e", pady=12
        )

    def _add_holiday(self) -> None:
        text = self.new_holiday_var.get().strip()
        try:
            datetime.date.fromisoformat(text)
        except ValueError:
            messagebox.showerror("Ошибка", "Дата должна быть в формате ГГГГ-ММ-ДД.")
            return
        existing = set(self.holidays_listbox.get(0, "end"))
        if text not in existing:
            self.holidays_listbox.insert("end", text)
        self.new_holiday_var.set("")

    def _remove_holiday(self) -> None:
        selection = self.holidays_listbox.curselection()
        for index in reversed(selection):
            self.holidays_listbox.delete(index)

    def _add_defaults(self) -> None:
        self.state.settings.holidays = list(self.holidays_listbox.get(0, "end"))
        self.state.settings.ensure_default_holidays()
        self.holidays_listbox.delete(0, "end")
        for d in sorted(self.state.settings.holidays):
            self.holidays_listbox.insert("end", d)

    def _save(self) -> None:
        try:
            deadline_days = int(self.deadline_days_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Длительность срока должна быть числом.")
            return

        s = self.state.settings
        s.executor_name = self.executor_name_var.get().strip()
        s.executor_phone = self.executor_phone_var.get().strip()
        s.signatory_name = self.signatory_var.get().strip()
        s.deadline_days = deadline_days
        s.downloads_dir = self.downloads_dir_var.get().strip()
        s.holidays = sorted(set(self.holidays_listbox.get(0, "end")))
        self.state.save_settings()
        messagebox.showinfo("Настройки", "Сохранено.")
