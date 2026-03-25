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

## Email уведомления

1. Скопируйте `.env.example` в `.env`
2. Заполните Gmail SMTP настройки
3. Для `SMTP_PASSWORD` используйте Google App Password

Переменные:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_google_app_password
SMTP_FROM=your_email@gmail.com
NOTIFY_EMAIL_TO=your_email@gmail.com
```
