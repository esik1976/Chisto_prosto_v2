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
```

Для Render добавьте те же переменные в `Environment` и выполните redeploy.
