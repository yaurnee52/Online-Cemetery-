# Онлайн-кладбище (Django + DRF)

Информационная система поиска кладбищ и мест захоронений Москвы.
Работает на Django 5 + Django REST Framework, единая база PostgreSQL.

## Стек

- **Backend**: Django 5, Django REST Framework, django-filter
- **Database**: PostgreSQL (одна база на всё)
- **Frontend**: Django templates + Bootstrap 5 + 2GIS Maps
- **Конфиг**: `.env` через `python-dotenv`

## Структура

```
OnlineCemetery/
├── config/                       # Django-проект
│   ├── settings.py               # настройки (БД, DRF, шаблоны)
│   ├── urls.py                   # корневой роутер
│   ├── wsgi.py / asgi.py
├── apps/
│   └── cemeteries/               # бизнес-приложение
│       ├── models.py             # Cemetery / Burial / BurialPerson
│       ├── serializers.py        # DRF сериалайзеры
│       ├── filters.py            # django-filter FilterSet'ы
│       ├── services.py           # бизнес-логика (поиск, парсинг, geocoding)
│       ├── views.py              # ViewSets + APIView + TemplateView
│       ├── urls.py               # API + страницы
│       ├── admin.py              # Django Admin
│       ├── management/commands/
│       │   └── migrate_old_data.py   # миграция legacy данных
│       └── migrations/
├── templates/                    # index.html / map.html / cemetery.html
├── static/                       # статика
├── manage.py
├── requirements.txt
└── .env
```

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
```

Заполни `.env` (см. шаблон в репозитории) — главное `POSTGRES_*` переменные.

## База данных

```bash
python manage.py migrate
python manage.py createsuperuser   # для доступа в /admin/
```

## Перенос старых данных

Если в той же PostgreSQL ещё лежат legacy таблицы `cemeteries`, `burials`,
`burial_persons` (от старого FastAPI), их можно перелить в новые
Django-таблицы (`cemeteries_cemetery`, `cemeteries_burial`, `cemeteries_burialperson`):

```bash
# полная миграция (все три фазы)
python manage.py migrate_old_data

# только кладбища, источник — legacy SQLite
python manage.py migrate_old_data --only cemeteries --sqlite-path cemetery.db

# с очисткой целевых таблиц
python manage.py migrate_old_data --truncate

# проверка без записи
python manage.py migrate_old_data --dry-run
```

Команда:

- сопоставляет `burial.cemetery_name` с моделью `Cemetery` через нормализованное имя;
- разбирает псевдо-JSON `geoData` / `geoDataCenter` в чистый GeoJSON-словарь;
- конвертирует `has_tombstone` (`Да`/`Нет`) в `BooleanField`;
- ничего не теряет: новые таблицы создаются, старые остаются нетронутыми.

После успешной миграции legacy таблицы можно удалить вручную в `psql`.

## Запуск

```bash
python manage.py runserver 0.0.0.0:8000
```

- UI: <http://localhost:8000/>
- Карта: <http://localhost:8000/map/>
- Админка: <http://localhost:8000/admin/>
- DRF Browsable API: <http://localhost:8000/api/cemeteries/>

## REST API

| Метод | URL                                    | Описание                                |
| ----- | -------------------------------------- | --------------------------------------- |
| GET   | `/api/cemeteries/`                     | список кладбищ (`?search=`, `?ordering=`) |
| GET   | `/api/cemeteries/{id}/`                | карточка кладбища                       |
| GET   | `/api/cemeteries/{id}/burials/`        | захоронения внутри кладбища (фильтры `fio`, `sector`, `limit`) |
| GET   | `/api/cemeteries/markers/`             | маркеры для карты                       |
| POST  | `/api/cemeteries/geocode/`             | геокодинг кладбищ без координат         |
| GET   | `/api/burials/`                        | захоронения                             |
| GET   | `/api/burials/{id}/`                   | детальная карточка с людьми             |
| GET   | `/api/burials/search/`                 | плоский поиск по людям (для UI таблицы) |
| GET   | `/api/burials/{id}/point/`             | точка `lat/lon` захоронения             |
| GET   | `/api/persons/`                        | люди (с фильтрами `fio`, `cemetery`, годы) |
| GET   | `/api/2gis/search/`                    | прокси для 2GIS                         |
| GET   | `/api/mosru/64023/`                    | проверка data.mos.ru                    |
