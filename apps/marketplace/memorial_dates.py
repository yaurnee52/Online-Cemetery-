"""Даты поминовения (годовщина смерти) для избранных захоронений."""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

MONTHS_GENITIVE = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_DATE_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")


def format_ru_date(d: date, *, with_weekday: bool = False) -> str:
    label = f"{d.day} {MONTHS_GENITIVE[d.month]} {d.year}"
    if not with_weekday:
        return label
    weekdays = (
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    )
    return f"{label} ({weekdays[d.weekday()]})"


def parse_death_date(raw: str | None, death_year: int | None = None) -> Optional[date]:
    text = (raw or "").strip()
    match = _DATE_RE.match(text)
    if match:
        day, month, year = (int(match.group(i)) for i in range(1, 4))
        try:
            return date(year, month, day)
        except ValueError:
            return None
    if death_year:
        try:
            return date(int(death_year), 1, 1)
        except ValueError:
            return None
    return None


def next_memorial_anniversary(death: date, today: date | None = None) -> tuple[date, int]:
    """Ближайший день памяти (годовщина) и число дней до него."""
    today = today or date.today()
    try:
        candidate = death.replace(year=today.year)
    except ValueError:
        candidate = date(today.year, 3, 1)
    if candidate < today:
        try:
            candidate = death.replace(year=today.year + 1)
        except ValueError:
            candidate = date(today.year + 1, 3, 1)
    return candidate, (candidate - today).days


def memorial_info_for_person(
    death_date_raw: str | None,
    death_year: int | None,
    *,
    today: date | None = None,
    days_before: int = 15,
) -> Optional[dict]:
    """День памяти (годовщина смерти): дата и флаг напоминания за days_before дней."""
    today = today or date.today()
    death = parse_death_date(death_date_raw, death_year)
    if not death:
        return None
    next_date, days_until = next_memorial_anniversary(death, today)
    year_only = not (death_date_raw or "").strip() and bool(death_year)
    when = "сегодня" if days_until == 0 else f"через {days_until} дн."
    return {
        "label": "День памяти (годовщина)",
        "note": (
            f"Указан только год смерти ({death_year}); точная дата может отличаться."
            if year_only
            else None
        ),
        "next_date": next_date.isoformat(),
        "next_date_display": format_ru_date(next_date, with_weekday=True),
        "days_until": days_until,
        "when_short": when,
        "is_reminder_active": days_until <= days_before,
    }


def memorial_reminder_for_person(
    death_date_raw: str | None,
    death_year: int | None,
    *,
    today: date | None = None,
    days_before: int = 15,
) -> Optional[dict]:
    """Напоминание только в окне за days_before дней до годовщины."""
    info = memorial_info_for_person(
        death_date_raw, death_year, today=today, days_before=days_before
    )
    if not info or not info["is_reminder_active"]:
        return None
    return info
