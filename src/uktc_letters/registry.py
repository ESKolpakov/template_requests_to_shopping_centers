"""Реестр (лог) генераций писем (ТЗ, раздел 8) — сохраняется в локальной
SQLite-базе в пользовательском каталоге данных (см. paths.py), чтобы
накапливать историю между запусками приложения, а не сбрасываться каждый
раз.
"""

from __future__ import annotations

import datetime
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .letters import LetterPlan, LetterStatus
from .paths import registry_db_path

__all__ = ["RunSummary", "LetterRecord", "Registry"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    formation_date TEXT NOT NULL,
    total_addresses INTEGER NOT NULL,
    auto_personal INTEGER NOT NULL,
    auto_impersonal INTEGER NOT NULL,
    manual_review INTEGER NOT NULL,
    objects_source_path TEXT,
    contacts_source_path TEXT,
    template_path TEXT
);

CREATE TABLE IF NOT EXISTS letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    address TEXT NOT NULL,
    tc_name TEXT,
    status TEXT NOT NULL,
    reason TEXT,
    filename TEXT,
    output_path TEXT
);
"""


@dataclass
class RunSummary:
    id: int
    started_at: str
    formation_date: str
    total_addresses: int
    auto_personal: int
    auto_impersonal: int
    manual_review: int
    objects_source_path: str = ""
    contacts_source_path: str = ""
    template_path: str = ""


@dataclass
class LetterRecord:
    id: int
    run_id: int
    address: str
    tc_name: str
    status: str
    reason: str
    filename: str
    output_path: str


class Registry:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or registry_db_path())
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def record_run(
        self,
        plans: list[LetterPlan],
        formation_date: datetime.date,
        objects_source_path: str = "",
        contacts_source_path: str = "",
        template_path: str = "",
        output_paths: dict[str, str] | None = None,
    ) -> RunSummary:
        """Сохранить в реестре результаты одного запуска генерации."""
        output_paths = output_paths or {}
        counts = {status: 0 for status in LetterStatus}
        for plan in plans:
            counts[plan.status] += 1

        cur = self._conn.execute(
            "INSERT INTO runs (started_at, formation_date, total_addresses, "
            "auto_personal, auto_impersonal, manual_review, "
            "objects_source_path, contacts_source_path, template_path) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                datetime.datetime.now().isoformat(timespec="seconds"),
                formation_date.isoformat(),
                len(plans),
                counts[LetterStatus.AUTO_PERSONAL],
                counts[LetterStatus.AUTO_IMPERSONAL],
                counts[LetterStatus.MANUAL_REVIEW],
                objects_source_path,
                contacts_source_path,
                template_path,
            ),
        )
        run_id = cur.lastrowid

        for plan in plans:
            self._conn.execute(
                "INSERT INTO letters (run_id, address, tc_name, status, "
                "reason, filename, output_path) VALUES (?,?,?,?,?,?,?)",
                (
                    run_id,
                    plan.address_display,
                    plan.tc_name,
                    plan.status.value,
                    plan.status_reason,
                    plan.filename,
                    output_paths.get(plan.address_display, ""),
                ),
            )
        self._conn.commit()

        return RunSummary(
            id=run_id,
            started_at=datetime.datetime.now().isoformat(timespec="seconds"),
            formation_date=formation_date.isoformat(),
            total_addresses=len(plans),
            auto_personal=counts[LetterStatus.AUTO_PERSONAL],
            auto_impersonal=counts[LetterStatus.AUTO_IMPERSONAL],
            manual_review=counts[LetterStatus.MANUAL_REVIEW],
            objects_source_path=objects_source_path,
            contacts_source_path=contacts_source_path,
            template_path=template_path,
        )

    def list_runs(self, limit: int = 50) -> list[RunSummary]:
        rows = self._conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            RunSummary(
                id=r["id"],
                started_at=r["started_at"],
                formation_date=r["formation_date"],
                total_addresses=r["total_addresses"],
                auto_personal=r["auto_personal"],
                auto_impersonal=r["auto_impersonal"],
                manual_review=r["manual_review"],
                objects_source_path=r["objects_source_path"] or "",
                contacts_source_path=r["contacts_source_path"] or "",
                template_path=r["template_path"] or "",
            )
            for r in rows
        ]

    def list_letters(self, run_id: int, status: str | None = None) -> list[LetterRecord]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM letters WHERE run_id=? AND status=? ORDER BY id",
                (run_id, status),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM letters WHERE run_id=? ORDER BY id", (run_id,)
            ).fetchall()
        return [
            LetterRecord(
                id=r["id"],
                run_id=r["run_id"],
                address=r["address"],
                tc_name=r["tc_name"] or "",
                status=r["status"],
                reason=r["reason"] or "",
                filename=r["filename"] or "",
                output_path=r["output_path"] or "",
            )
            for r in rows
        ]
