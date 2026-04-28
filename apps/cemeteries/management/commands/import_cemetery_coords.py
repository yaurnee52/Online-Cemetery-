from __future__ import annotations

from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from apps.cemeteries.models import Cemetery
from apps.cemeteries.services import normalize_cemetery_name


FORCED_REPLACE_NAMES = {
    "белова один",
    "белова 1",
    "былово",
    "большое свинорье",
    "богородская деревня",
    "богородское",
    "ваварьино",
    "ваварино",
}


class Command(BaseCommand):
    help = "Импортирует координаты кладбищ из Excel и обновляет БД."

    def add_arguments(self, parser):
        parser.add_argument(
            "--xlsx",
            default="data/moscow_cemeteries_full.xlsx",
            help="Путь к Excel-файлу с колонками: название, lat, lon",
        )

    def handle(self, *args, **options):
        xlsx_path = Path(options["xlsx"]).resolve()
        if not xlsx_path.exists():
            raise CommandError(f"Файл не найден: {xlsx_path}")

        frame = pd.read_excel(xlsx_path)
        if frame.shape[1] < 3:
            raise CommandError("Ожидаются минимум 3 колонки: название, lat, lon.")

        name_col, lat_col, lon_col = frame.columns[:3]
        excel_rows = []
        for _, row in frame.iterrows():
            raw_name = str(row.get(name_col, "")).strip()
            if not raw_name:
                continue
            lat = row.get(lat_col)
            lon = row.get(lon_col)
            if pd.isna(lat) or pd.isna(lon):
                continue
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (TypeError, ValueError):
                continue
            excel_rows.append((normalize_cemetery_name(raw_name), lat_f, lon_f, raw_name))

        if not excel_rows:
            raise CommandError("В Excel нет валидных строк с координатами.")

        updated = 0
        skipped = 0
        forced_updated = 0

        cemeteries = list(Cemetery.objects.all().order_by("name"))
        for cemetery in cemeteries:
            db_norm = normalize_cemetery_name(cemetery.name)
            force_replace = any(alias in db_norm for alias in FORCED_REPLACE_NAMES)

            match = self._find_match(db_norm, excel_rows)
            if not match:
                skipped += 1
                continue

            _, lat, lon, source_name = match
            should_update = force_replace or cemetery.latitude is None or cemetery.longitude is None
            if not should_update:
                skipped += 1
                continue

            cemetery.latitude = lat
            cemetery.longitude = lon
            cemetery.save(update_fields=["latitude", "longitude", "updated_at"])
            updated += 1
            if force_replace:
                forced_updated += 1
                self.stdout.write(
                    f"[forced] {cemetery.name} -> {lat}, {lon} (source: {source_name})"
                )

        self.stdout.write(self.style.SUCCESS(f"Готово. Обновлено: {updated}, пропущено: {skipped}"))
        self.stdout.write(f"Принудительно перезаписано: {forced_updated}")

    def _find_match(self, db_norm: str, excel_rows: list[tuple[str, float, float, str]]):
        for row in excel_rows:
            excel_norm = row[0]
            if excel_norm == db_norm:
                return row
        for row in excel_rows:
            excel_norm = row[0]
            if db_norm and excel_norm and (db_norm in excel_norm or excel_norm in db_norm):
                return row
        return None
