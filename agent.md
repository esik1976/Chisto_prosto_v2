# Agent Instructions

Инструкция для code-ассистента, который продолжает разработку проекта `Chisto Prosto`.

## Контекст проекта
- Проект: веб-приложение для агрегатора уборки городских улиц.
- Цель MVP: быстро проверять сценарии заказа уборки, выбора исполнителя, оплаты, истории и аналитики.
- Главный принцип: KISS. Минимально необходимое решение, без оверинжиниринга.
- Базовые документы: `vision.md`, `conventions.md`, `doc/workflow.md`, `doc/tasklist.md`.

## Текущий стек
- Backend: Python, FastAPI.
- UI: Jinja2, HTML, CSS, минимальный JavaScript.
- Карта: Leaflet + OpenStreetMap.
- Геокодинг: Nominatim через backend endpoint.
- Email: Resend API.
- Данные: SQLite локально, PostgreSQL на Render через `DATABASE_URL`.
- Деплой: Render.
- Репозиторий: GitHub.

## Текущая структура
- `app/main.py` — маршруты, роли, сценарии приложения.
- `app/auth.py` — регистрация, логин, роли, пароли.
- `app/db.py` — подключение SQLite/PostgreSQL и инициализация схемы.
- `app/storage.py` — работа с заказами, историей, контрактами.
- `app/payments.py` — mock-платежи.
- `app/notifications.py` — email через Resend.
- `app/config.py` — переменные окружения и `.env`.
- `templates/` — HTML-шаблоны.
- `static/` — стили, изображения, Leaflet.
- `doc/tasklist.md` — план разработки и прогресс.

## Реализованные сценарии
- Регистрация и вход пользователей.
- Роли: `customer`, `worker`, `admin`.
- Создание заказа с адресом, описанием, ценой и точкой на карте.
- Автоподстановка адреса по координатам с кешем и защитой от частых запросов.
- Список заказов с фильтрами и статусами.
- Исполнитель берет заказ и завершает его.
- Администратор меняет статусы и фиксирует оплату.
- Mock-оплата.
- Email-уведомление после создания заказа.
- История событий заказа.
- Дашборд аналитики.
- Контракты между заказчиком и исполнителем.
- Поддержка PostgreSQL на Render.

## Правила разработки
- Следовать `doc/tasklist.md` и не перескакивать без согласования.
- Перед новой итерацией кратко предложить решение и дождаться согласования.
- Делать маленькие итерации, каждая должна давать проверяемый результат.
- Не добавлять новые зависимости без необходимости.
- Не вводить ORM, микросервисы, очереди и сложную инфраструктуру без явного решения.
- Секреты не коммитить. `.env` должен оставаться локальным.
- После реализации обновлять `doc/tasklist.md`.
- После проверки делать git commit и push.

## Проверка перед коммитом
Минимальная проверка:

```bash
.venv\Scripts\python.exe -c "from app.db import init_db; init_db(); from app.main import app; print('app ok')"
.venv\Scripts\python.exe -m compileall app
```

При изменении шаблонов:

```bash
.venv\Scripts\python.exe -c "from jinja2 import Environment, FileSystemLoader; Environment(loader=FileSystemLoader('templates')).get_template('имя_шаблона.html'); print('template ok')"
```

## Локальный запуск
```bash
.venv\Scripts\activate
uvicorn app.main:app --reload
```

Открыть:

```text
http://127.0.0.1:8000
```

## Render
- Build command: `pip install -r requirements.txt`.
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Для постоянной БД задать `DATABASE_URL`.
- После push выполнять `Manual Deploy` → `Deploy latest commit`.

## Конфигурация
Основные переменные:

```env
RESEND_API_KEY=
EMAIL_FROM=
NOTIFY_EMAIL_TO=
APP_CONTACT_EMAIL=
DATABASE_URL=
```

Если `DATABASE_URL` пустой, используется SQLite `data/app.db`.
Если `DATABASE_URL` задан, используется PostgreSQL.

## Важные ограничения
- Nominatim имеет rate limit; не увеличивать частоту запросов геокодинга.
- Mock-оплата не является реальной оплатой.
- Старые данные SQLite не мигрируют в PostgreSQL автоматически.
- Роли и права доступа простые, достаточные для MVP.

## Ближайший план
Следующие пункты из `doc/tasklist.md`:
- Реальный платежный провайдер.
- Рейтинги и отзывы.
- API и интеграции.

Приоритет выбирать по практической ценности для MVP.
