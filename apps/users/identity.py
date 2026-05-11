"""ФИО и паспорт для доверенности и профиля."""
from __future__ import annotations

import re
from typing import Any

PASSPORT_SERIES_RE = re.compile(r"^\d{2}\s\d{2}$")
PASSPORT_NUMBER_RE = re.compile(r"^\d{6}$")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "on", "yes")


def normalize_passport_series(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 4:
        raise ValueError("Серия паспорта: 4 цифры (например 12 13).")
    return f"{digits[:2]} {digits[2:]}"


def normalize_passport_number(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 6:
        raise ValueError("Номер паспорта: 6 цифр.")
    return digits


def build_full_name(
    *,
    last_name: str,
    first_name: str,
    patronymic: str = "",
    no_patronymic: bool = False,
) -> str:
    parts = [last_name.strip(), first_name.strip()]
    if not no_patronymic and patronymic.strip():
        parts.append(patronymic.strip())
    return " ".join(parts)


def passport_display(series: str, number: str) -> str:
    return f"паспорт серии {series}, № {number}"
