"""Календарь памятных дат и напоминания об услугах к праздникам (РПЦ)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .models import NotificationType, ServiceCode


@dataclass(frozen=True)
class HolidayReminder:
    key: str
    title: str
    body: str
    holiday_date: date
    days_until: int
    service_codes: tuple[str, ...]
    notification_type: str
    primary_service_code: str
    holiday_date_display: str
    date_context: str
    marketplace_url: str = "/marketplace/"


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


def format_holiday_date(d: date) -> str:
    weekdays = (
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    )
    return f"{d.day} {MONTHS_GENITIVE[d.month]} {d.year} ({weekdays[d.weekday()]})"


def orthodox_easter(year: int) -> date:
    """Дата Пасхи по юлианскому пасхалию в григорианском календаре (РПЦ)."""
    a = year % 19
    b = year % 4
    c = year % 7
    d = (19 * a + 15) % 30
    e = (2 * b + 4 * c + 6 * d + 6) % 7
    day = 22 + d + e
    month = 3
    if day > 31:
        day -= 31
        month = 4
    julian = date(year, month, day)
    return julian + timedelta(days=13)


def _saturday_before(target: date) -> date:
    """Ближайшая суббота на или перед указанной датой."""
    return target - timedelta(days=(target.weekday() - 5) % 7)


def _clean_monday(easter: date) -> date:
    return easter - timedelta(days=48)


def _holiday_events_for_year(
    year: int,
) -> list[tuple[str, str, str, date, tuple[str, ...], str, str, str]]:
    """key, title, body, date, service_codes, notification_type, primary_service_code, date_context."""
    easter = orthodox_easter(year)
    radonitsa = easter + timedelta(days=9)
    clean_monday = _clean_monday(easter)

    meatfare_saturday = clean_monday - timedelta(days=2)
    lent_week2 = clean_monday + timedelta(days=12)
    lent_week3 = clean_monday + timedelta(days=19)
    lent_week4 = clean_monday + timedelta(days=26)
    before_radonitsa = radonitsa - timedelta(days=3)
    dmitrievskaya = _saturday_before(date(year, 11, 8))
    pokrovskaya = _saturday_before(date(year, 10, 14))

    easter_label = easter.strftime("%d.%m.%Y")
    radonitsa_label = radonitsa.strftime("%d.%m.%Y")
    clean_label = clean_monday.strftime("%d.%m.%Y")

    body_parents = (
        "Закажите поминальные работы на захоронении: уборка, свеча и фотоотчёт для родных, "
        "если не сможете приехать сами."
    )

    return [
        (
            "pascha",
            "Пасха",
            "К Светлому Христову Воскресению можно заказать поминальные работы: уборка участка и фотоотчёт.",
            easter,
            (ServiceCode.PASCHA_CARE, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.PASCHA_CARE,
            f"Православная Пасха · дата по календарю: {easter_label}",
        ),
        (
            "radonitsa",
            "Радоница",
            "Скоро Радоница — закажите «Дистанционную Радоницу»: уборка, свеча и фотоотчёт на могилу.",
            radonitsa,
            (ServiceCode.RADONITSA_REMOTE, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.RADONITSA_REMOTE,
            f"9-й день после Пасхи ({easter_label}) · Радоница {radonitsa_label}",
        ),
        (
            "parents_before_radonitsa",
            "Родительская суббота",
            f"Родительская суббота перед Радоницей. {body_parents}",
            before_radonitsa,
            (ServiceCode.PARENTS_SATURDAY, ServiceCode.RADONITSA_REMOTE),
            NotificationType.PASCHA,
            ServiceCode.PARENTS_SATURDAY,
            f"За 3 дня до Радоницы ({radonitsa_label})",
        ),
        (
            "meatfare_parents",
            "Мясопустная родительская суббота",
            body_parents,
            meatfare_saturday,
            (ServiceCode.PARENTS_SATURDAY, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.PARENTS_SATURDAY,
            f"За 2 дня до Начала Великого поста ({clean_label})",
        ),
        (
            "lent_week2",
            "Родительская суббота (2-я седмица Великого поста)",
            body_parents,
            lent_week2,
            (ServiceCode.PARENTS_SATURDAY, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.PARENTS_SATURDAY,
            f"Суббота 2-й седмицы Великого поста (от {clean_label})",
        ),
        (
            "lent_week3",
            "Родительская суббота (3-я седмица Великого поста)",
            body_parents,
            lent_week3,
            (ServiceCode.PARENTS_SATURDAY, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.PARENTS_SATURDAY,
            f"Суббота 3-й седмицы Великого поста (от {clean_label})",
        ),
        (
            "lent_week4",
            "Родительская суббота (4-я седмица Великого поста)",
            body_parents,
            lent_week4,
            (ServiceCode.PARENTS_SATURDAY, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.PARENTS_SATURDAY,
            f"Суббота 4-й седмицы Великого поста (от {clean_label})",
        ),
        (
            "warriors_memorial",
            "Поминовение усопших воинов",
            body_parents,
            lent_week2,
            (ServiceCode.MEMORIAL_WARRIORS, ServiceCode.PARENTS_SATURDAY),
            NotificationType.ANNIVERSARY,
            ServiceCode.MEMORIAL_WARRIORS,
            f"Суббота 2-й седмицы Великого поста · поминовение воинов (от {clean_label})",
        ),
        (
            "dmitrievskaya",
            "Дмитриевская родительская суббота",
            body_parents,
            dmitrievskaya,
            (ServiceCode.PARENTS_SATURDAY, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.PARENTS_SATURDAY,
            "Суббота перед днём св. Димитрия Солунского (8 ноября)",
        ),
        (
            "pokrovskaya",
            "Покровская родительская суббота",
            body_parents,
            pokrovskaya,
            (ServiceCode.PARENTS_SATURDAY, ServiceCode.CLEANING),
            NotificationType.PASCHA,
            ServiceCode.PARENTS_SATURDAY,
            "Суббота перед Покровом Пресвятой Богородицы (14 октября)",
        ),
    ]


def get_active_holiday_reminders(
    today: date | None = None,
    *,
    days_before: int = 15,
) -> list[HolidayReminder]:
    """Праздники, до которых осталось от 0 до days_before дней включительно."""
    today = today or date.today()
    reminders: list[HolidayReminder] = []

    for year in (today.year - 1, today.year, today.year + 1):
        for (
            key,
            title,
            body,
            holiday_date,
            service_codes,
            ntype,
            primary_code,
            date_context,
        ) in _holiday_events_for_year(year):
            delta = (holiday_date - today).days
            if 0 <= delta <= days_before:
                reminders.append(
                    HolidayReminder(
                        key=f"{key}_{holiday_date.isoformat()}",
                        title=title,
                        body=body,
                        holiday_date=holiday_date,
                        days_until=delta,
                        service_codes=service_codes,
                        notification_type=ntype,
                        primary_service_code=primary_code,
                        holiday_date_display=format_holiday_date(holiday_date),
                        date_context=date_context,
                    )
                )

    reminders.sort(key=lambda r: (r.holiday_date, r.title))
    return reminders


def get_next_holiday_for_service(
    service_code: str,
    today: date | None = None,
) -> dict | None:
    """Ближайшая памятная дата, к которой привязана услуга (для карточки в маркетплейсе)."""
    today = today or date.today()
    candidates: list[tuple[date, int, str, str, bool]] = []

    for year in (today.year - 1, today.year, today.year + 1):
        for (
            _key,
            title,
            _body,
            holiday_date,
            service_codes,
            _ntype,
            primary_code,
            date_context,
        ) in _holiday_events_for_year(year):
            if service_code not in service_codes and primary_code != service_code:
                continue
            delta = (holiday_date - today).days
            if delta < 0:
                continue
            candidates.append(
                (holiday_date, delta, title, date_context, primary_code == service_code)
            )

    if not candidates:
        return None

    holiday_date, delta, title, date_context, is_primary = min(candidates, key=lambda c: c[0])
    when = "сегодня" if delta == 0 else f"через {delta} дн."
    return {
        "holiday_title": title,
        "holiday_date": holiday_date.isoformat(),
        "holiday_date_display": format_holiday_date(holiday_date),
        "date_context": date_context,
        "days_until": delta,
        "when_short": when,
        "is_primary": is_primary,
    }
