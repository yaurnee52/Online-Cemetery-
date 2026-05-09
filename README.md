# Онлайн-кладбище (Django + DRF)

Веб-платформа для поиска захоронений, работы с картой кладбищ Москвы и заказа услуг по уходу.

## Технологии

- Backend: Django 5, Django REST Framework, django-filter
- Database: PostgreSQL (для продакшена); локально можно **SQLite** через `DJANGO_USE_SQLITE=true` в `.env`
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
- создаст `.env` из `.env.example` (если нет) — в примере по умолчанию **SQLite**, Postgres не обязателен,
- применит миграции,
- запустит сервер.

#### Кодировка файла `.env` (UTF-8)

Кодировка — это не строка внутри файла, а **способ сохранения на диск**. Нужна **UTF-8**, иначе на Windows бывают ошибки при чтении пароля и подключении к БД.

**Cursor или VS Code**

1. Откройте `.env` в редакторе.
2. Внизу **справа** на строке состояния найдите надпись с кодировкой (часто **`UTF-8`**, может быть **`Windows 1251`**, **`CP1251`** и т.п.).
3. **Нажмите на эту надпись**.
4. Выберите пункт **`Save with Encoding...`** («Сохранить с кодировкой…»).
5. В списке выберите **`UTF-8`**. Если есть два варианта, берите обычный **`UTF-8`**, а не *UTF-8 with BOM* (если оба есть — обычно подойдёт любой из UTF-8; при сомнении — без BOM).

Если там уже стоит **UTF-8** и файл вы не сохраняли из другого редактора — менять ничего не обязательно.

**Блокнот (Windows 11)**

Меню **Файл** → **Сохранить как** → внизу поле **Кодировка** → **UTF-8** → сохраните (можно тем же именем `.env`).

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

Скопируйте `.env.example` в `.env` (или дождитесь `run-dev`).

- **`DJANGO_USE_SQLITE=true`** (как в примере) — база в файле `db.sqlite3` в корне проекта, **PostgreSQL не нужен**. Удобно для клона и первого запуска.
- **`DJANGO_USE_SQLITE=false`** — тогда нужен установленный PostgreSQL и корректные `POSTGRES_*`.

Переменные `DJANGO_*` читает именно Django (секрет, отладка, хосты). Пример:

```env
DJANGO_USE_SQLITE=true
DJANGO_SECRET_KEY=change-me-in-production
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

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

- **Точка входа (карта):** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Поиск захоронений: [http://127.0.0.1:8000/search/](http://127.0.0.1:8000/search/)
- Кабинет: [http://127.0.0.1:8000/cabinet/](http://127.0.0.1:8000/cabinet/)
- Админка: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

### Проверить, запущен ли сервер, и остановить

Если в браузере открывается `localhost`, а вы не запускали проект — часто это **старый процесс** на порту 8000 или **кэш страницы**.

```powershell
.\dev-status.ps1   # порт 8000 занят? отвечает ли Django
.\stop-dev.ps1     # остановить процесс на порту 8000
```

Запуск снова: `.\run-dev.ps1` (остановка в том же окне — **Ctrl+C**).

### Напоминания об услугах к праздникам

Раз в день (или по расписанию Celery beat):

```powershell
python manage.py send_holiday_reminders
```

Создаёт уведомления заказчикам за 14 дней до Пасхи, Радоницы, родительских суббот и др. Баннер на всех страницах: `GET /api/marketplace/holiday-reminders/`.

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
