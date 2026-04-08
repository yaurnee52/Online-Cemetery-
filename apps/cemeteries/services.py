"""Слой бизнес-логики (изолирован от views/serializers).

Здесь живут: парсинг inscription/имён, нормализация имени кладбища,
геокодинг через 2GIS/Nominatim, проксирование внешних API.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Optional

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q

from .models import Burial, BurialPerson, Cemetery


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------
_DATE_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_INSCRIPTION_TOKEN_RE = re.compile(r"(?i)\binscription\s*:\s*")


# ---------------------------------------------------------------------------
# Парсинг inscription и имён
# ---------------------------------------------------------------------------
def split_people_entries(inscription: str | None) -> list[str]:
    """Делит сырой inscription на отдельные записи людей."""
    if not inscription:
        return []
    text = str(inscription).replace("\r", "\n")
    parts = _INSCRIPTION_TOKEN_RE.split(text)
    if len(parts) > 1:
        return [chunk.strip(" \n\t,;") for chunk in parts[1:] if chunk.strip(" \n\t,;")]
    return [
        _INSCRIPTION_TOKEN_RE.sub("", line, count=1).strip(" ,;")
        for line in (raw.strip() for raw in text.splitlines())
        if line
    ]


def extract_life_dates(text: str | None) -> tuple[Optional[str], Optional[str]]:
    """ДД.ММ.ГГГГ → (birth_date, death_date)."""
    if not text:
        return (None, None)
    dates = _DATE_RE.findall(text)
    if dates:
        return (dates[0], dates[1] if len(dates) > 1 else None)
    years = _YEAR_RE.findall(text)
    if not years:
        return (None, None)
    return (years[0], years[1] if len(years) > 1 else None)


def extract_years(text: str | None) -> tuple[Optional[int], Optional[int]]:
    if not text:
        return (None, None)
    years = [int(y) for y in _YEAR_RE.findall(text)]
    if not years:
        return (None, None)
    if len(years) == 1:
        return (years[0], None)
    return (years[0], years[1])


def normalize_inscription_preview(text: str | None, max_len: int = 160) -> str:
    """Однострочное превью inscription для UI."""
    compact = " ".join((text or "").replace("\n", " ").split())
    compact = _INSCRIPTION_TOKEN_RE.sub("", compact, count=1)
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


# ---------------------------------------------------------------------------
# Нормализация имени кладбища (для матчинга legacy-данных)
# ---------------------------------------------------------------------------
def normalize_cemetery_name(name: str | None) -> str:
    value = (name or "").lower().strip().replace("ё", "е")
    value = re.sub(r"[\(\)\.,\-_/]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


# ---------------------------------------------------------------------------
# Сериализация результата поиска (для UI-таблиц)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PersonHit:
    burial: Burial
    person: BurialPerson
    people_count: int

    def to_dict(self) -> dict:
        text = self.burial.inscription or ""
        birth_date = self.person.birth_date or None
        death_date = self.person.death_date or None
        birth_year = self.person.birth_year
        death_year = self.person.death_year
        if not (birth_date or death_date):
            birth_date, death_date = extract_life_dates(self.person.person_name)
        if not (birth_year or death_year):
            birth_year, death_year = extract_years(self.person.person_name)
        return {
            "id": self.burial.id,
            "grave_number": self.burial.grave_number,
            "has_tombstone": _bool_to_legacy(self.burial.has_tombstone),
            "has_tombstone_bool": self.burial.has_tombstone,
            "inscription": text,
            "inscription_preview": normalize_inscription_preview(text),
            "display_person": self.person.person_name,
            "people_count": max(1, self.people_count),
            "cemetery_name": self.burial.cemetery.name if self.burial.cemetery_id else "",
            "global_id": self.burial.global_id,
            "birth_date": birth_date,
            "death_date": death_date,
            "birth_year": birth_year,
            "death_year": death_year,
        }


def _bool_to_legacy(value: Optional[bool]) -> Optional[str]:
    if value is True:
        return "Да"
    if value is False:
        return "Нет"
    return None


# ---------------------------------------------------------------------------
# Поиск захоронений (по людям)
# ---------------------------------------------------------------------------
def search_person_hits(
    *,
    fio: str | None = None,
    cemetery_id: int | None = None,
    cemetery_name: str | None = None,
    sector: str | None = None,
    limit: int = 100,
    min_limit: int = 1,
    max_limit: int = 1000,
) -> list[dict]:
    """Возвращает плоский список «попаданий» person+burial для UI."""
    safe_limit = max(min_limit, min(int(limit or 0), max_limit))

    qs = (
        BurialPerson.objects
        .select_related("burial", "burial__cemetery")
        .order_by("-burial_id", "id")
    )

    fio_query = (fio or "").strip()
    if fio_query:
        qs = qs.filter(person_name__icontains=fio_query)

    if cemetery_id:
        qs = qs.filter(burial__cemetery_id=cemetery_id)
    elif cemetery_name and cemetery_name.strip():
        qs = qs.filter(burial__cemetery__name__icontains=cemetery_name.strip())

    if sector and sector.strip():
        qs = qs.filter(burial__grave_number__icontains=sector.strip())

    rows = list(qs[:safe_limit])
    counts = _people_counts_per_burial([row.burial_id for row in rows])

    return [
        PersonHit(burial=row.burial, person=row, people_count=counts.get(row.burial_id, 1)).to_dict()
        for row in rows
    ]


def count_person_hits(*, cemetery_id: int, fio: str | None, sector: str | None) -> int:
    qs = BurialPerson.objects.filter(burial__cemetery_id=cemetery_id)
    if fio and fio.strip():
        qs = qs.filter(person_name__icontains=fio.strip())
    if sector and sector.strip():
        qs = qs.filter(burial__grave_number__icontains=sector.strip())
    return qs.count()


def _people_counts_per_burial(burial_ids: Iterable[int]) -> dict[int, int]:
    unique = sorted({int(b) for b in burial_ids if b is not None})
    if not unique:
        return {}
    rows = (
        BurialPerson.objects.filter(burial_id__in=unique)
        .values("burial_id")
        .annotate(cnt=Count("id"))
    )
    return {row["burial_id"]: row["cnt"] for row in rows}


# ---------------------------------------------------------------------------
# Геокодинг кладбищ (2GIS → Nominatim)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GeocodeReport:
    processed: int
    updated: int
    failed: int

    def to_dict(self) -> dict:
        return {"processed": self.processed, "updated": self.updated, "failed": self.failed}


def geocode_missing_cemeteries(limit: int | None = None) -> GeocodeReport:
    qs = Cemetery.objects.filter(latitude__isnull=True, longitude__isnull=True).order_by("name")
    if limit:
        qs = qs[: int(limit)]

    updated = failed = 0
    rows = list(qs)
    with transaction.atomic():
        for row in rows:
            point = _geocode_with_2gis(row.name) or _geocode_with_nominatim(row.name)
            if point is None:
                failed += 1
                continue
            row.latitude, row.longitude = point
            row.save(update_fields=["latitude", "longitude", "updated_at"])
            updated += 1

    return GeocodeReport(processed=len(rows), updated=updated, failed=failed)


def _http_get_json(url: str, *, timeout: int = 10) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "OnlineCemetery/2.0", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def _geocode_with_2gis(name: str) -> tuple[float, float] | None:
    api_key = settings.DGIS_API_KEY or settings.DGIS_FALLBACK_KEY
    if not api_key:
        return None
    base = "https://catalog.api.2gis.com/3.0/items"
    for query in (f"{name} кладбище Москва", f"{name} Москва"):
        params = urllib.parse.urlencode(
            {"q": query, "fields": "items.point,items.name", "key": api_key}
        )
        data = _http_get_json(f"{base}?{params}")
        if not data:
            continue
        for item in (data.get("result") or {}).get("items") or []:
            point = item.get("point") or {}
            lat, lon = point.get("lat"), point.get("lon")
            if lat is not None and lon is not None:
                return (float(lat), float(lon))
    return None


def _geocode_with_nominatim(name: str) -> tuple[float, float] | None:
    base = "https://nominatim.openstreetmap.org/search"
    for query in (f"{name} кладбище, Москва", f"{name}, Москва"):
        params = urllib.parse.urlencode(
            {"q": query, "format": "json", "limit": "1", "addressdetails": "0"}
        )
        data = _http_get_json(f"{base}?{params}")
        if isinstance(data, list) and data:
            try:
                return (float(data[0]["lat"]), float(data[0]["lon"]))
            except (KeyError, TypeError, ValueError):
                continue
    return None


# ---------------------------------------------------------------------------
# Внешние API (для UI кнопок проверки)
# ---------------------------------------------------------------------------
def call_2gis_search(query: str) -> tuple[int, dict]:
    api_key = settings.DGIS_API_KEY or settings.DGIS_FALLBACK_KEY
    query = (query or "").strip()
    if not query:
        return 200, {"ok": True, "items": []}
    params = urllib.parse.urlencode(
        {
            "q": query,
            "fields": "items.id,items.name,items.full_name,items.point",
            "key": api_key,
        }
    )
    url = f"https://catalog.api.2gis.com/3.0/items?{params}"
    payload = _http_get_json(url)
    if payload is None:
        return 502, {"ok": False, "error": "2GIS unreachable", "items": []}
    return 200, payload


def call_mosru_dataset() -> tuple[int, dict]:
    url = settings.MOSRU_DATASET_URL
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "OnlineCemetery/2.0",
            "Accept": "text/html,application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return 200, {"source": url, "ok": True, "preview": body[:2000]}
    except (urllib.error.URLError, TimeoutError) as exc:
        return 502, {"source": url, "ok": False, "error": str(exc)}
