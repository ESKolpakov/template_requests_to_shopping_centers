"""Вкладка «Проверка по ЕГРЮЛ» (ТЗ, раздел 6) — полуавтоматический модуль:
приложение только подставляет ИНН в форму поиска и разбирает уже
скачанный пользователем PDF. Никакого автоматического прохождения капчи
или скрапинга страницы поиска здесь нет и быть не должно."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from ..addresses import building_key
from ..egrul_parser import EgrulData, egrul_search_url, find_latest_egrul_pdf, parse_egrul_pdf
from .state import AppState


class EgrulTab(ttk.Frame):
    def __init__(self, parent, state: AppState):
        super().__init__(parent, padding=12)
        self.state = state
        self._current_address_key: str | None = None

        ttk.Label(
            self,
            text=(
                "1) Выберите адрес ТЦ, для которого не хватает данных об УК. "
                "2) Откройте страницу ЕГРЮЛ с подставленным ИНН и пройдите "
                "капчу вручную. 3) Скачайте выписку (PDF) и укажите её "
                "здесь — приложение разберёт нужные поля и покажет их для "
                "проверки перед сохранением."
            ),
            wraplength=620,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))

        top = ttk.Frame(self)
        top.pack(fill="x")

        ttk.Label(top, text="Адрес ТЦ:").grid(row=0, column=0, sticky="w")
        self.address_combo = ttk.Combobox(top, width=50, state="readonly")
        self.address_combo.grid(row=0, column=1, sticky="w", padx=6)
        self.address_combo.bind("<<ComboboxSelected>>", self._on_address_selected)
        ttk.Button(top, text="Обновить список", command=self._refresh_addresses).grid(
            row=0, column=2, padx=6
        )

        ttk.Label(top, text="ИНН:").grid(row=1, column=0, sticky="w", pady=6)
        self.inn_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.inn_var, width=20).grid(
            row=1, column=1, sticky="w", padx=6
        )
        ttk.Button(
            top, text="Открыть egrul.nalog.ru с этим ИНН", command=self._open_browser
        ).grid(row=1, column=2, padx=6)

        file_frame = ttk.Frame(self)
        file_frame.pack(fill="x", pady=8)
        ttk.Button(
            file_frame, text="Указать скачанный PDF выписки...", command=self._pick_pdf
        ).pack(side="left")
        ttk.Button(
            file_frame,
            text="Найти последний PDF в папке загрузок",
            command=self._find_latest,
        ).pack(side="left", padx=6)

        result_frame = ttk.LabelFrame(self, text="Данные из выписки — проверьте перед сохранением")
        result_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.fields = {}
        labels = [
            ("short_name", "Название организации"),
            ("legal_address", "Юридический адрес"),
            ("representative_surname", "Фамилия"),
            ("representative_first_name", "Имя"),
            ("representative_patronymic", "Отчество"),
            ("representative_position", "Должность"),
            ("representative_gender", "Пол (male/female)"),
            ("representative_org_name", "Либо название организации-представителя"),
        ]
        for i, (key, label) in enumerate(labels):
            ttk.Label(result_frame, text=label + ":").grid(
                row=i, column=0, sticky="w", padx=8, pady=3
            )
            var = tk.StringVar()
            ttk.Entry(result_frame, textvariable=var, width=55).grid(
                row=i, column=1, sticky="w", padx=8, pady=3
            )
            self.fields[key] = var

        ttk.Button(
            result_frame,
            text="Подтвердить и сохранить в справочник",
            command=self._confirm,
        ).grid(row=len(labels), column=0, columnspan=2, pady=10)

        self._refresh_addresses()

    def _refresh_addresses(self) -> None:
        addresses = [group.building_address for group in self.state.building_groups]
        self.address_combo["values"] = addresses

    def _on_address_selected(self, _event=None) -> None:
        address = self.address_combo.get()
        self._current_address_key = building_key(address)
        if self.state.contacts_index is not None:
            match = self.state.contacts_index.match(address)
            if match.records:
                inns = match.records[0].inn_tokens
                if inns:
                    self.inn_var.set(inns[0])

    def _open_browser(self) -> None:
        inn = self.inn_var.get().strip()
        if not inn:
            messagebox.showwarning("ИНН не указан", "Введите ИНН перед открытием страницы поиска.")
            return
        webbrowser.open(egrul_search_url(inn))

    def _pick_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Выбрать PDF выписки из ЕГРЮЛ", filetypes=[("PDF файлы", "*.pdf")]
        )
        if not path:
            return
        self._parse_and_fill(path)

    def _find_latest(self) -> None:
        directory = self.state.settings.downloads_dir
        if not directory:
            messagebox.showwarning(
                "Папка загрузок не задана",
                "Укажите папку загрузок браузера в разделе «Настройки» "
                "(поле сохраняется в config.json) или выберите PDF вручную.",
            )
            return
        inn = self.inn_var.get().strip() or None
        path = find_latest_egrul_pdf(directory, inn)
        if not path:
            messagebox.showinfo("Не найдено", "Подходящий PDF в папке загрузок не найден.")
            return
        self._parse_and_fill(path)

    def _parse_and_fill(self, path: str) -> None:
        try:
            data = parse_egrul_pdf(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка разбора PDF", str(exc))
            return
        for key, var in self.fields.items():
            var.set(getattr(data, key) or "")

    def _confirm(self) -> None:
        if not self._current_address_key:
            messagebox.showwarning("Адрес не выбран", "Сначала выберите адрес ТЦ в списке.")
            return
        data = EgrulData(
            inn=self.inn_var.get().strip(),
            full_name=self.fields["short_name"].get().strip(),
            short_name=self.fields["short_name"].get().strip(),
            legal_address=self.fields["legal_address"].get().strip(),
            representative_surname=self.fields["representative_surname"].get().strip() or None,
            representative_first_name=self.fields["representative_first_name"].get().strip() or None,
            representative_patronymic=self.fields["representative_patronymic"].get().strip() or None,
            representative_position=self.fields["representative_position"].get().strip() or None,
            representative_gender=self.fields["representative_gender"].get().strip() or None,
            representative_org_name=self.fields["representative_org_name"].get().strip() or None,
        )
        self.state.confirm_egrul_result(self._current_address_key, data)
        messagebox.showinfo(
            "Сохранено",
            "Данные сохранены и будут использованы при следующей генерации "
            "писем по этому адресу (в этом и последующих запусках "
            "приложения).",
        )
