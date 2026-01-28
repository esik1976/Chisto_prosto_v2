from typing import Optional

ROLES = {"customer", "worker", "admin"}


def get_user_name(request) -> Optional[str]:
    return request.session.get("user_name")


def get_user_role(request) -> Optional[str]:
    return request.session.get("user_role")


def set_user_session(request, name: str, role: str) -> None:
    request.session["user_name"] = name
    request.session["user_role"] = role


def clear_user_session(request) -> None:
    request.session.clear()
