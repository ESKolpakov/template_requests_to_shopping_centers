"""Вкладка «Генерация писем» (ТЗ, раздел 8)."""

from __future__ import annotations

import datetime
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..dates import parse_date_ru
from ..docx_template import TemplateError, render_letter
from ..letters import LetterStatus, plan_letter
from ..paths import default_output_dir
from .state import AppState

_STATUS_LABELS = {
    LetterStatus.AUTO_PERSONAL: "автоматически (персонально)",
    LetterStatus.AUTO_IMPERSONAL: "автоматически (обезличенно)",
    LetterStatus.MANUAL_REVIEW: "требует проверки",
}


class GenerateTab(ttk.Frame):
    def __init__(self, parent, state: AppState):
        super().__init__(parent, padding=12)
        self.state = state

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Дата формирования писем (ДД.ММ.ГГГГ):").grid(
            row=0, column=0, sticky="w"
        )
        self.date_var = tk.StringVar(value=datetime.date.today().strftime("%d.%m.%Y"))
        ttk.Entry(top, textvariable=self.date_var, width=14).grid(
            row=0, column=1, sticky="w", padx=6
        )

        ttk.Label(top, text="Папка сохранения:").grid(row=1, column=0, sticky="w", pady=6)
        self.output_dir_var = tk.StringVar(value=str(default_output_dir()))
        ttk.Entry(top, textvariable=self.output_dir_var, width=50).grid(
            row=1, column=1, sticky="w", padx=6
        )
        ttk.Button(top, text="Выбрать...", command=self._choose_output_dir).grid(
            row=1, column=2, padx=6
        )

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, pady=10)

        columns = ("address", "tc_name", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("address", text="Адрес")
        self.tree.heading("tc_name", text="ТЦ")
        self.tree.heading("status", text="Предполагаемый статус")
        self.tree.column("address", width=260)
        self.tree.column("tc_name", width=160)
        self.tree.column("status", width=200)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, command=self.tree.yview)
        scrollbar.pack(side="left", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text="Обновить список / предпросмотр", command=self._refresh).pack(
            side="left"
        )
        ttk.Button(btns, text="Выбрать всё", command=self._select_all).pack(side="left", padx=6)
        ttk.Button(btns, text="Снять выделение", command=self._select_none).pack(side="left")
        ttk.Button(btns, text="Сгенерировать выбранные письма", command=self._generate).pack(
            side="right"
        )

        self.summary_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.summary_var, wraplength=700, justify="left").pack(
            anchor="w", pady=(10, 0)
        )

        self._plans_by_address = {}
        if self.state.building_groups:
            self._refresh()

    def _choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Папка для сохранения писем")
        if path:
            self.output_dir_var.set(path)

    def _formation_date(self) -> datetime.date | None:
        try:
            return parse_date_ru(self.date_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректная дата формирования писем.")
            return None

    def _refresh(self) -> None:
        if not self.state.building_groups:
            messagebox.showwarning(
                "Нет данных", "Сначала загрузите выгрузку объектов торговли на вкладке «Источники данных»."
            )
            return
        if self.state.contacts_index is None:
            messagebox.showwarning(
                "Нет справочника", "Сначала загрузите справочник УК/ТЦ на вкладке «Источники данных»."
            )
            return
        formation_date = self._formation_date()
        if formation_date is None:
            return

        self.tree.delete(*self.tree.get_children())
        self._plans_by_address = {}
        for group in self.state.building_groups:
            plan = plan_letter(
                group, self.state.contacts_index, self.state.settings, formation_date,
                self.state.egrul_overrides,
            )
            self._plans_by_address[plan.address_display] = plan
            self.tree.insert(
                "", "end", iid=plan.address_display,
                values=(plan.address_display, plan.tc_name, _STATUS_LABELS[plan.status]),
            )
        self._select_all()

    def _select_all(self) -> None:
        self.tree.selection_set(self.tree.get_children())

    def _select_none(self) -> None:
        self.tree.selection_remove(self.tree.get_children())

    def _generate(self) -> None:
        if not self.state.template_path:
            messagebox.showwarning("Нет шаблона", "Сначала загрузите шаблон письма на вкладке «Шаблоны».")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ничего не выбрано", "Выберите хотя бы один адрес для генерации.")
            return
        formation_date = self._formation_date()
        if formation_date is None:
            return

        output_dir = Path(self.output_dir_var.get())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось создать папку сохранения: {exc}")
            return

        plans = []
        output_paths: dict[str, str] = {}
        errors = []
        for address in selected:
            plan = self._plans_by_address.get(address)
            if plan is None:
                continue
            plans.append(plan)
            out_path = output_dir / plan.filename
            try:
                render_letter(self.state.template_path, plan.context, plan.row_specs, str(out_path))
                output_paths[plan.address_display] = str(out_path)
            except TemplateError as exc:
                errors.append(f"{plan.address_display}: {exc}")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{plan.address_display}: {exc}")

        summary = self.state.registry.record_run(
            plans,
            formation_date,
            objects_source_path=self.state.settings.objects_source_path,
            contacts_source_path=self.state.settings.contacts_source_path,
            template_path=self.state.template_path,
            output_paths=output_paths,
        )

        review_addresses = [p.address_display for p in plans if p.status == LetterStatus.MANUAL_REVIEW]
        lines = [
            f"Готово. Всего: {summary.total_addresses}, "
            f"автоматически (персонально): {summary.auto_personal}, "
            f"автоматически (обезличенно): {summary.auto_impersonal}, "
            f"требуют проверки: {summary.manual_review}.",
        ]
        if review_addresses:
            lines.append("Требуют ручной проверки: " + "; ".join(review_addresses))
        if errors:
            lines.append("Ошибки генерации: " + "; ".join(errors))
        self.summary_var.set("\n".join(lines))

        try:
            os.startfile(output_dir)  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            pass
