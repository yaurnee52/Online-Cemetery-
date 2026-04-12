"""Миграция данных из старых таблиц (legacy SQLite + legacy PostgreSQL) в новые Django-таблицы.

Логика
------
1. Источник кладбищ:
   * `--sqlite-path PATH` — старый SQLite файл (поле legacy `cemeteries`),
   * иначе по умолчанию читаем legacy таблицу `cemeteries` из текущей PostgreSQL,
     которая лежит рядом с новыми Django-таблицами (`cemeteries_cemetery`, ...).
2. Источник захоронений и людей — всегда legacy таблицы PostgreSQL
   `burials` и `burial_persons` (если присутствуют).
3. По имени кладбища (`burial.cemetery_name`) ищется существующий `Cemetery`
   из новой таблицы `cemeteries_cemetery`. Соответствие — по нормализованному
   имени; если кладбище не найдено, оно создаётся автоматически.

Безопасность
-----------
* Каждая фаза идёт в своей транзакции и обрабатывается батчами (`--batch-size`).
* Поддерживается `--dry-run` (никаких записей).
* Можно пропускать фазы (`--only cemeteries|burials|persons|all`) и обнулять
  целевые таблицы (`--truncate`).

Примеры
-------
    python manage.py migrate_old_data
    python manage.py migrate_old_data --only cemeteries --sqlite-path cemetery.db
    python manage.py migrate_old_data --truncate --batch-size 5000
    python manage.py migrate_old_data --dry-run
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections, transaction

from apps.cemeteries.models import Burial, BurialPerson, Cemetery
from apps.cemeteries.services import (
    extract_life_dates,
    extract_years,
    normalize_cemetery_name,
    split_people_entries,
)


PHASES = ("cemeteries", "burials", "persons", "all")


# ===========================================================================
# Resolver: имя кладбища -> Cemetery
# ===========================================================================
class CemeteryResolver:
    """Сопоставляет произвольную строку имени кладбища с моделью Cemetery."""

    def __init__(self) -> None:
        self._cache: dict[str, int] = {}
        self._refresh()

    def _refresh(self) -> None:
        self._cache = {
            normalize_cemetery_name(name): cid
            for cid, name in Cemetery.objects.values_list("id", "name")
        }

    def resolve(self, name: str | None, *, create_missing: bool = True) -> Optional[int]:
        normalized = normalize_cemetery_name(name)
        if not normalized:
            return None
        if normalized in self._cache:
            return self._cache[normalized]
        if not create_missing:
            return None
        cemetery = Cemetery.objects.create(name=(name or "").strip() or normalized)
        self._cache[normalized] = cemetery.id
        return cemetery.id


# ===========================================================================
# Stats
# ===========================================================================
@dataclass
class PhaseStats:
    name: str
    total_source: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed: float = 0.0

    def render(self) -> str:
        head = f"[{self.name}] source={self.total_source} inserted={self.inserted} updated={self.updated} skipped={self.skipped} elapsed={self.elapsed:.1f}s"
        if self.errors:
            head += f" errors={len(self.errors)} (first: {self.errors[0]})"
        return head


# ===========================================================================
# Geo data parser
# ===========================================================================
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
_TYPE_RE = re.compile(r"type\s*[:=]\s*([A-Za-z]+)")


def parse_geo_raw(raw: Any) -> Optional[dict]:
    """Парсит сырое значение geoData / geoDataCenter в GeoJSON-подобный dict.

    Источник часто содержит псевдо-JSON ``{coordinates:[37.6, 55.7], type:Point}``,
    где ключи без кавычек — `json.loads` тут падает. Используем регулярки.
    """
    if raw in (None, ""):
        return None
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass

    type_match = _TYPE_RE.search(text)
    geometry_type = type_match.group(1) if type_match else "Point"

    numbers = [float(n) for n in _NUMBER_RE.findall(text)]
    if len(numbers) < 2:
        return None
    if geometry_type.lower() == "point" or len(numbers) == 2:
        return {"type": "Point", "coordinates": [numbers[0], numbers[1]]}
    pairs = list(zip(numbers[0::2], numbers[1::2]))
    return {"type": geometry_type or "Polygon", "coordinates": [pairs]}


# ===========================================================================
# Tombstone -> bool
# ===========================================================================
_TRUE_TOKENS = {"да", "true", "1", "y", "yes", "t"}
_FALSE_TOKENS = {"нет", "false", "0", "n", "no", "f"}


def parse_tombstone(value: Any) -> Optional[bool]:
    if value is None:
        return None
    token = str(value).strip().lower()
    if not token:
        return None
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    return None


# ===========================================================================
# Source readers
# ===========================================================================
def _read_legacy_cemeteries_postgres() -> list[dict]:
    """Читает legacy таблицу `cemeteries` из текущей Postgres-БД (если существует)."""
    if not _legacy_table_exists("cemeteries"):
        return []
    sql = """
        SELECT name,
               burials_signed, burials_unsigned, burials_total,
               people_signed, people_unsigned, people_total,
               latitude, longitude
        FROM cemeteries
        ORDER BY name
    """
    rows: list[dict] = []
    with connection.cursor() as cur:
        cur.execute(sql)
        for r in cur.fetchall():
            rows.append(
                {
                    "name": r[0],
                    "burials_signed": r[1],
                    "burials_unsigned": r[2],
                    "burials_total": r[3],
                    "people_signed": r[4],
                    "people_unsigned": r[5],
                    "people_total": r[6],
                    "latitude": r[7],
                    "longitude": r[8],
                }
            )
    return rows


def _read_legacy_cemeteries_sqlite(path: str) -> list[dict]:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(
            """
            SELECT name,
                   burials_signed, burials_unsigned, burials_total,
                   people_signed, people_unsigned, people_total,
                   latitude, longitude
            FROM cemeteries
            ORDER BY name
            """
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        con.close()


def _iter_legacy_burials(batch_size: int = 5000) -> Iterator[list[tuple]]:
    """Потоково читает legacy.burials через keyset-пагинацию (по id)."""
    if not _legacy_table_exists("burials"):
        return
    last_id = 0
    while True:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, grave_number, has_tombstone, inscription, cemetery_name,
                       global_id, geo_data_raw, geo_data_center_raw
                FROM burials
                WHERE id > %s
                ORDER BY id
                LIMIT %s
                """,
                [last_id, batch_size],
            )
            chunk = cur.fetchall()
        if not chunk:
            break
        last_id = int(chunk[-1][0])
        yield chunk


def _iter_legacy_persons(batch_size: int = 5000) -> Iterator[list[tuple]]:
    """Потоково читает legacy.burial_persons через keyset-пагинацию (по id)."""
    if not _legacy_table_exists("burial_persons"):
        return
    last_id = 0
    while True:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, burial_id, person_name, birth_date, death_date, birth_year, death_year
                FROM burial_persons
                WHERE id > %s
                ORDER BY id
                LIMIT %s
                """,
                [last_id, batch_size],
            )
            chunk = cur.fetchall()
        if not chunk:
            break
        last_id = int(chunk[-1][0])
        yield [row[1:] for row in chunk]


def _legacy_table_exists(table_name: str) -> bool:
    """Проверяет наличие legacy таблицы в текущей Postgres-БД."""
    new_tables = {"cemeteries_cemetery", "cemeteries_burial", "cemeteries_burialperson"}
    if table_name in new_tables:
        return False
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            LIMIT 1
            """,
            [table_name],
        )
        return cur.fetchone() is not None


def _legacy_count(table_name: str) -> int:
    if not _legacy_table_exists(table_name):
        return 0
    with connection.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0])


# ===========================================================================
# Phases
# ===========================================================================
def migrate_cemeteries(
    *,
    sqlite_path: str | None,
    truncate: bool,
    dry_run: bool,
    stdout,
) -> PhaseStats:
    stats = PhaseStats(name="cemeteries")
    started = time.time()

    if sqlite_path:
        stdout.write(f"  - source: SQLite {sqlite_path}")
        rows = _read_legacy_cemeteries_sqlite(sqlite_path)
    else:
        stdout.write("  - source: legacy PostgreSQL (table `cemeteries`)")
        rows = _read_legacy_cemeteries_postgres()

    stats.total_source = len(rows)
    if stats.total_source == 0:
        stdout.write("    нет данных в источнике — фаза пропущена")
        stats.elapsed = time.time() - started
        return stats

    if dry_run:
        stdout.write(f"    [dry-run] было бы загружено: {stats.total_source}")
        stats.elapsed = time.time() - started
        return stats

    with transaction.atomic():
        if truncate:
            BurialPerson.objects.all().delete()
            Burial.objects.all().delete()
            Cemetery.objects.all().delete()

        existing = {c.name: c for c in Cemetery.objects.all()}
        to_create: list[Cemetery] = []
        to_update: list[Cemetery] = []

        for row in rows:
            name = (row.get("name") or "").strip()
            if not name:
                stats.skipped += 1
                continue
            payload = {
                "burials_signed": row.get("burials_signed"),
                "burials_unsigned": row.get("burials_unsigned"),
                "burials_total": row.get("burials_total"),
                "people_signed": row.get("people_signed"),
                "people_unsigned": row.get("people_unsigned"),
                "people_total": row.get("people_total"),
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
            }
            if name in existing:
                row_obj = existing[name]
                changed = False
                for field_name, value in payload.items():
                    if getattr(row_obj, field_name) != value:
                        setattr(row_obj, field_name, value)
                        changed = True
                if changed:
                    to_update.append(row_obj)
                else:
                    stats.skipped += 1
            else:
                to_create.append(Cemetery(name=name, **payload))

        if to_create:
            Cemetery.objects.bulk_create(to_create, batch_size=500)
            stats.inserted = len(to_create)
        if to_update:
            Cemetery.objects.bulk_update(
                to_update,
                fields=[
                    "burials_signed",
                    "burials_unsigned",
                    "burials_total",
                    "people_signed",
                    "people_unsigned",
                    "people_total",
                    "latitude",
                    "longitude",
                ],
                batch_size=500,
            )
            stats.updated = len(to_update)

    stats.elapsed = time.time() - started
    return stats


def migrate_burials(
    *,
    truncate: bool,
    batch_size: int,
    dry_run: bool,
    stdout,
) -> PhaseStats:
    stats = PhaseStats(name="burials")
    started = time.time()

    total = _legacy_count("burials")
    stats.total_source = total
    if total == 0:
        stdout.write("    legacy таблица `burials` пуста или отсутствует — пропуск")
        stats.elapsed = time.time() - started
        return stats

    if dry_run:
        stdout.write(f"    [dry-run] было бы загружено: {total}")
        stats.elapsed = time.time() - started
        return stats

    if truncate:
        with transaction.atomic():
            BurialPerson.objects.all().delete()
            Burial.objects.all().delete()

    resolver = CemeteryResolver()

    existing_global_ids: set[int] = set(
        Burial.objects.exclude(global_id__isnull=True).values_list("global_id", flat=True)
    )

    processed = 0
    for chunk in _iter_legacy_burials(batch_size=batch_size):
        objs: list[Burial] = []
        for (
            _legacy_id,
            grave_number,
            has_tombstone,
            inscription,
            cemetery_name,
            global_id,
            geo_data_raw,
            geo_data_center_raw,
        ) in chunk:
            if global_id is not None and int(global_id) in existing_global_ids:
                stats.skipped += 1
                continue

            cemetery_id = resolver.resolve(cemetery_name)
            if cemetery_id is None:
                stats.skipped += 1
                stats.errors.append(f"no cemetery for: {cemetery_name!r}")
                continue

            objs.append(
                Burial(
                    cemetery_id=cemetery_id,
                    grave_number=(grave_number or "")[:128],
                    has_tombstone=parse_tombstone(has_tombstone),
                    inscription=inscription or "",
                    global_id=int(global_id) if global_id is not None else None,
                    geo_data=parse_geo_raw(geo_data_raw),
                    geo_data_center=parse_geo_raw(geo_data_center_raw),
                )
            )

        if objs:
            Burial.objects.bulk_create(objs, batch_size=batch_size, ignore_conflicts=True)
            stats.inserted += len(objs)
            for obj in objs:
                if obj.global_id is not None:
                    existing_global_ids.add(obj.global_id)

        processed += len(chunk)
        stdout.write(f"    burials: processed={processed}/{total} inserted={stats.inserted}")

    stats.elapsed = time.time() - started
    return stats


def migrate_persons(
    *,
    truncate: bool,
    batch_size: int,
    dry_run: bool,
    stdout,
) -> PhaseStats:
    stats = PhaseStats(name="persons")
    started = time.time()

    total = _legacy_count("burial_persons")
    stats.total_source = total
    if total == 0:
        stdout.write("    legacy таблица `burial_persons` пуста или отсутствует — пропуск")
        stats.elapsed = time.time() - started
        return stats

    if dry_run:
        stdout.write(f"    [dry-run] было бы загружено: {total}")
        stats.elapsed = time.time() - started
        return stats

    if truncate:
        BurialPerson.objects.all().delete()

    legacy_to_new = _build_legacy_burial_id_map(stdout)
    if not legacy_to_new:
        msg = "не удалось сопоставить ни одного legacy.burial_id с новым Burial — фаза прервана"
        stats.errors.append(msg)
        stdout.write(f"    {msg}")
        stats.elapsed = time.time() - started
        return stats

    processed = 0
    for chunk in _iter_legacy_persons(batch_size=batch_size):
        objs: list[BurialPerson] = []
        for legacy_burial_id, person_name, birth_date, death_date, birth_year, death_year in chunk:
            new_burial_id = legacy_to_new.get(int(legacy_burial_id))
            if new_burial_id is None:
                stats.skipped += 1
                continue
            person_text = (person_name or "").strip()
            if not person_text:
                stats.skipped += 1
                continue

            if not (birth_date or death_date):
                bd, dd = extract_life_dates(person_text)
                birth_date = birth_date or bd
                death_date = death_date or dd
            if not (birth_year or death_year):
                by, dy = extract_years(person_text)
                birth_year = birth_year or by
                death_year = death_year or dy

            objs.append(
                BurialPerson(
                    burial_id=new_burial_id,
                    person_name=person_text,
                    birth_date=(birth_date or "")[:32],
                    death_date=(death_date or "")[:32],
                    birth_year=int(birth_year) if birth_year else None,
                    death_year=int(death_year) if death_year else None,
                )
            )
        if objs:
            BurialPerson.objects.bulk_create(objs, batch_size=batch_size)
            stats.inserted += len(objs)

        processed += len(chunk)
        stdout.write(f"    persons: processed={processed}/{total} inserted={stats.inserted}")

    stats.elapsed = time.time() - started
    return stats


def _build_legacy_burial_id_map(stdout) -> dict[int, int]:
    """Соответствие legacy.burials.id -> cemeteries_burial.id (через global_id)."""
    if not _legacy_table_exists("burials"):
        return {}

    with connection.cursor() as cur:
        cur.execute("SELECT id, global_id FROM burials WHERE global_id IS NOT NULL")
        legacy = cur.fetchall()
    if not legacy:
        stdout.write("    у legacy.burials нет global_id — соответствие невозможно")
        return {}

    legacy_global_to_id = {int(g): int(i) for i, g in legacy if g is not None}

    new_global_to_id = {
        int(g): int(i)
        for i, g in Burial.objects.exclude(global_id__isnull=True).values_list("id", "global_id")
    }

    mapping: dict[int, int] = {}
    for global_id, legacy_id in legacy_global_to_id.items():
        new_id = new_global_to_id.get(global_id)
        if new_id is not None:
            mapping[legacy_id] = new_id
    stdout.write(f"    map ready: {len(mapping)} legacy burial ids resolved")
    return mapping


# ===========================================================================
# Command
# ===========================================================================
class Command(BaseCommand):
    help = "Переливает данные из legacy SQLite + legacy PostgreSQL таблиц в новые Django-модели."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--only",
            choices=PHASES,
            default="all",
            help="Какую фазу выполнить (по умолчанию все).",
        )
        parser.add_argument(
            "--sqlite-path",
            default=None,
            help="Путь к legacy SQLite файлу с таблицей `cemeteries` (необязательно).",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Очистить целевые Django-таблицы перед загрузкой.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Размер батча для bulk_create.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Не записывать в БД, только посчитать объёмы.",
        )

    def handle(self, *args, **opts) -> None:
        only = opts["only"]
        sqlite_path = opts["sqlite_path"]
        truncate = opts["truncate"]
        batch_size = opts["batch_size"]
        dry_run = opts["dry_run"]

        if "default" not in connections.databases:
            raise CommandError("DATABASES['default'] не настроен.")

        self.stdout.write(self.style.NOTICE("Migrate legacy data into Django"))
        self.stdout.write(f"  settings: only={only} truncate={truncate} dry-run={dry_run} batch={batch_size}")
        self.stdout.write(f"  target db: {settings.DATABASES['default']['NAME']}")

        results: list[PhaseStats] = []

        if only in ("cemeteries", "all"):
            self.stdout.write(self.style.MIGRATE_HEADING("\n[1/3] cemeteries"))
            results.append(
                migrate_cemeteries(
                    sqlite_path=sqlite_path,
                    truncate=truncate,
                    dry_run=dry_run,
                    stdout=self.stdout,
                )
            )

        if only in ("burials", "all"):
            self.stdout.write(self.style.MIGRATE_HEADING("\n[2/3] burials"))
            results.append(
                migrate_burials(
                    truncate=truncate,
                    batch_size=batch_size,
                    dry_run=dry_run,
                    stdout=self.stdout,
                )
            )

        if only in ("persons", "all"):
            self.stdout.write(self.style.MIGRATE_HEADING("\n[3/3] burial_persons"))
            results.append(
                migrate_persons(
                    truncate=truncate,
                    batch_size=batch_size,
                    dry_run=dry_run,
                    stdout=self.stdout,
                )
            )

        self.stdout.write(self.style.SUCCESS("\nDone"))
        for stat in results:
            self.stdout.write("  " + stat.render())
