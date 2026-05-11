# Chisto Prosto

MVP цифрового агрегатора уборки городских улиц.

## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Откройте: http://127.0.0.1:8000

## Хранилище данных

Локально приложение использует SQLite: `data/app.db`.

На Render используйте PostgreSQL:

1. Создайте PostgreSQL database в Render.
2. Скопируйте Internal Database URL.
3. Добавьте переменную `DATABASE_URL` в Environment Variables веб-сервиса.
4. Сделайте redeploy.

Если `DATABASE_URL` не задан, приложение автоматически работает на SQLite.

## Email уведомления через Resend

1. Создайте аккаунт в Resend
2. Получите API key
3. Скопируйте `.env.example` в `.env`
4. Заполните переменные

Переменные:

```env
RESEND_API_KEY=re_xxxxx
EMAIL_FROM=onboarding@resend.dev
NOTIFY_EMAIL_TO=your_email@gmail.com
APP_CONTACT_EMAIL=your_email@gmail.com
DATABASE_URL=
```

Для Render добавьте те же переменные в `Environment` и выполните redeploy.

## API

API работает через текущую сессию пользователя. Сначала войдите через `/login`.

- `GET /api/me` — текущий пользователь.
- `GET /api/orders` — список доступных заказов.
- `POST /api/orders` — создать заказ.
- `GET /api/orders/{id}` — детали заказа, события и отзыв.
- `GET /api/dashboard` — аналитика по доступным заказам.
- `GET /api/contracts` — доступные контракты.
- `GET /api/reviews` — доступные отзывы.

OpenAPI доступен по адресу `/docs`.
