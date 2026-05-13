# Онлайн-кладбище (Django + DRF)

Веб-платформа для поиска захоронений, работы с картой кладбищ Москвы и заказа услуг по уходу.

## Технологии

- Backend: Django 5, Django REST Framework, django-filter
- Database: PostgreSQL
- Frontend: Django templates + Bootstrap 5 + TomSelect (файлы в `static/vendor/`, без CDN) + 2GIS для карты
- Auth: JWT (`/api/auth/login/`, `/api/auth/refresh/`)
- Async: Celery + Redis + django-celery-beat

## Приложения проекта

- `apps/cemeteries` — кладбища, захоронения, поиск, карта
- `apps/users` — регистрация, профиль, роли (`customer`/`executor`)
- `apps/marketplace` — заказы, чат, уведомления, подписки, донаты, доверенности

---

## Быстрый старт (Windows)

### Запуск в 1 клик (рекомендуется)

Самый простой вариант:

```powershell
.\run-dev.bat
```

или

```powershell
powershell -ExecutionPolicy Bypass -File .\run-dev.ps1
```

Скрипт сам:

- создаст `.venv`, если ещё нет рабочего `python` внутри (пустую или битую папку `.venv` пересоздаст),
- установит зависимости через `.\.venv\Scripts\python.exe` (без `Activate.ps1` — так надёжнее после клона и на машинах с политикой PowerShell),
- создаст `.env` из `.env.example` (если нет),
- применит миграции,
- запустит сервер.

### 1) Создать и активировать виртуальное окружение

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Установить зависимости

```powershell
pip install -r requirements.txt
```

### 3) Настроить `.env`

Минимально нужны:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

POSTGRES_DB=online_cemetery
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

DGIS_API_KEY=
DGIS_FALLBACK_KEY=
```

### 4) Применить миграции

```powershell
python manage.py migrate
```

### 5) Создать администратора

```powershell
python manage.py createsuperuser
```

### 6) Запустить проект

```powershell
python manage.py runserver
```

Открыть:

- Главная: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Карта: [http://127.0.0.1:8000/map/](http://127.0.0.1:8000/map/)
- Кабинет: [http://127.0.0.1:8000/cabinet/](http://127.0.0.1:8000/cabinet/)
- Админка: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Полезные команды

### Миграция legacy-данных

```powershell
python manage.py migrate_old_data
python manage.py migrate_old_data --dry-run
python manage.py migrate_old_data --truncate
```

### Импорт координат кладбищ из Excel

```powershell
python manage.py import_cemetery_coords --xlsx "data/moscow_cemeteries_full.xlsx"
```

Команда:

- обновляет координаты для кладбищ без координат;
- умеет принудительно заменить координаты для проблемных названий (встроенный список алиасов).

### Проверка проекта

```powershell
python manage.py check
```

---

## API (основное)

- `GET /api/cemeteries/` — список кладбищ
- `GET /api/cemeteries/{id}/burials/` — захоронения кладбища (`limit`, `offset`, фильтры)
- `GET /api/burials/search/` — общий поиск по людям (`limit`, `offset`, фильтры)
- `POST /api/auth/register/` — регистрация
- `POST /api/auth/login/` — вход (JWT)
- `GET /api/auth/me/` — текущий профиль
- `GET /api/marketplace/orders/` — заказы пользователя
- `POST /api/marketplace/orders/{id}/take|done|confirm/` — действия по заказу

---

## Celery (опционально)

Если используете фоновые задачи:

```powershell
celery -A config worker -l info
celery -A config beat -l info
```

Для Celery нужен работающий Redis (`CELERY_BROKER_URL` в `.env`).
