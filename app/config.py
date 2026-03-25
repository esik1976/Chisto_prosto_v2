from pathlib import Path
import os


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")
APP_CONTACT_EMAIL = os.getenv("APP_CONTACT_EMAIL", EMAIL_FROM or NOTIFY_EMAIL_TO)
