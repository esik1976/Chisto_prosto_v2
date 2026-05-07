from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen
import json
import logging
import time

from .config import APP_CONTACT_EMAIL
from .db import init_db, is_unique_error
from .auth import (
    ROLES,
    create_user,
    authenticate,
    get_user_id,
    get_user_name,
    get_user_role,
    set_user_session,
    clear_user_session,
)
from .notifications import send_order_created_email
from .payments import create_mock_payment
from .storage import (
    list_orders,
    list_orders_for_customer,
    list_orders_for_worker,
    get_order,
    get_order_by_payment_id,
    list_order_events,
    create_order,
    add_order_event,
    take_order,
    complete_order,
    set_status,
    mark_paid,
    set_payment_pending,
    mark_paid_by_payment_id,
    mark_payment_failed,
)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="dev-secret")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)
reverse_geocode_cache = {}
last_reverse_geocode_request_at = 0.0


@app.on_event("startup")
def startup() -> None:
    init_db()


def _require_user(request: Request):
    if not get_user_role(request):
        return RedirectResponse(url="/login", status_code=303)
    return None


def _require_role(request: Request, allowed: set[str]):
    role = get_user_role(request)
    if role not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden")


def _orders_for_user(request: Request, status_filter: str = "all"):
    role = get_user_role(request)
    user_id = get_user_id(request)
    user_name = get_user_name(request)

    if role == "admin":
        orders = list_orders()
    elif role == "customer" and user_id is not None:
        orders = list_orders_for_customer(user_id)
    elif role == "worker" and user_name:
        orders = list_orders_for_worker(user_name)
    else:
        orders = []

    if status_filter == "all":
        return orders
    return [order for order in orders if order.status == status_filter]


def _ensure_can_pay(request: Request, order) -> None:
    role = get_user_role(request)
    if role == "admin":
        return
    if role == "customer" and order.customer_id == get_user_id(request):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _ensure_can_view_order(request: Request, order) -> None:
    role = get_user_role(request)
    if role == "admin":
        return
    if role == "customer" and order.customer_id == get_user_id(request):
        return
    if role == "worker" and (order.status == "new" or order.assignee == get_user_name(request)):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _actor(request: Request) -> str:
    return get_user_name(request) or "system"


def _dashboard_data(orders):
    total = len(orders)
    status_labels = {
        "new": "Новые",
        "in_progress": "В работе",
        "done": "Готово",
        "cancelled": "Отменены",
    }
    status_counts = {status: 0 for status in status_labels}
    paid_count = 0
    unpaid_count = 0
    total_amount = 0
    paid_amount = 0
    with_location = 0

    for order in orders:
        if order.status in status_counts:
            status_counts[order.status] += 1
        total_amount += order.price
        if order.paid:
            paid_count += 1
            paid_amount += order.price
        else:
            unpaid_count += 1
        if order.latitude is not None and order.longitude is not None:
            with_location += 1

    status_stats = []
    for status, label in status_labels.items():
        count = status_counts[status]
        percent = round((count / total) * 100) if total else 0
        status_stats.append(
            {"status": status, "label": label, "count": count, "percent": percent}
        )

    return {
        "total": total,
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "unpaid_amount": total_amount - paid_amount,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "with_location": with_location,
        "status_stats": status_stats,
    }


@app.get("/api/reverse-geocode")
def reverse_geocode(lat: float, lon: float):
    global last_reverse_geocode_request_at

    cache_key = (round(lat, 4), round(lon, 4))
    cached = reverse_geocode_cache.get(cache_key)
    if cached:
        return {"address": cached, "error": "", "cached": True}

    now = time.time()
    if now - last_reverse_geocode_request_at < 1.2:
        return {"address": "", "error": "local_rate_limit"}
    last_reverse_geocode_request_at = now

    params = {
        "format": "jsonv2",
        "lat": lat,
        "lon": lon,
        "accept-language": "ru",
        "addressdetails": 1,
    }
    if APP_CONTACT_EMAIL:
        params["email"] = APP_CONTACT_EMAIL

    request = UrlRequest(
        f"https://nominatim.openstreetmap.org/reverse?{urlencode(params)}",
        headers={
            "User-Agent": f"ChistoProsto/1.0 ({APP_CONTACT_EMAIL or 'no-contact'})",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.warning("Reverse geocode HTTP error for lat=%s lon=%s: %s", lat, lon, exc)
        return {"address": "", "error": f"http_{exc.code}"}
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Reverse geocode failed for lat=%s lon=%s: %s", lat, lon, exc)
        return {"address": "", "error": "request_failed"}
    address = payload.get("display_name", "")
    if address:
        reverse_geocode_cache[cache_key] = address
    return {"address": address, "error": "", "cached": False}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate(username, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=400,
        )
    set_user_session(request, user["id"], user["username"], user["role"])
    return RedirectResponse(url="/orders", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"request": request})


@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
):
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    try:
        user_id = create_user(username, role, password)
    except Exception as exc:
        if not is_unique_error(exc):
            raise
        return templates.TemplateResponse(
            request,
            "register.html",
            {"request": request, "error": "Пользователь уже существует"},
            status_code=400,
        )
    set_user_session(request, user_id, username, role)
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/logout")
def logout(request: Request):
    clear_user_session(request)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/camera", response_class=HTMLResponse)
def camera(request: Request):
    return templates.TemplateResponse(request, "camera.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    redirect = _require_user(request)
    if redirect:
        return redirect
    orders = _orders_for_user(request, "all")
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "user_name": get_user_name(request),
            "user_role": get_user_role(request),
            "stats": _dashboard_data(orders),
        },
    )


@app.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request, status: str = "all"):
    redirect = _require_user(request)
    if redirect:
        return redirect
    allowed_statuses = {"all", "new", "in_progress", "done", "cancelled"}
    status_filter = status if status in allowed_statuses else "all"
    return templates.TemplateResponse(
        request,
        "orders.html",
        {
            "request": request,
            "orders": _orders_for_user(request, status_filter),
            "user_name": get_user_name(request),
            "user_role": get_user_role(request),
            "status_filter": status_filter,
        },
    )


@app.get("/orders/new", response_class=HTMLResponse)
def orders_new(request: Request):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"customer", "admin"})
    return templates.TemplateResponse(
        request,
        "orders_new.html",
        {"request": request, "user_role": get_user_role(request)},
    )


@app.post("/orders/new")
def orders_create(
    request: Request,
    address: str = Form(...),
    description: str = Form(""),
    price: int = Form(0),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"customer", "admin"})
    order = create_order(
        address,
        description,
        price,
        latitude,
        longitude,
        get_user_id(request),
    )
    try:
        send_order_created_email(order)
    except Exception as exc:
        logger.exception("Failed to send order created email: %s", exc)
    add_order_event(order.id, "created", "Заказ создан", _actor(request))
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/take")
def orders_take(request: Request, order_id: int, assignee: str = Form("")):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"worker", "admin"})
    assignee_name = assignee.strip() or get_user_name(request)
    if not assignee_name:
        raise HTTPException(status_code=400, detail="Assignee is required")
    try:
        take_order(order_id, assignee_name)
        add_order_event(
            order_id,
            "assignee",
            f"Заказ взят в работу исполнителем: {assignee_name}",
            _actor(request),
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/complete")
def orders_complete(request: Request, order_id: int):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"worker", "admin"})
    try:
        complete_order(order_id)
        add_order_event(order_id, "status", "Статус изменен на done", _actor(request))
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/status")
def orders_status(request: Request, order_id: int, status: str = Form(...)):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"admin"})
    try:
        set_status(order_id, status)
        add_order_event(order_id, "status", f"Статус изменен на {status}", _actor(request))
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/pay")
def orders_pay(request: Request, order_id: int):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"admin"})
    try:
        mark_paid(order_id)
        add_order_event(order_id, "payment", "Оплата отмечена вручную", _actor(request))
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/pay/start")
def orders_pay_start(request: Request, order_id: int):
    redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        order = get_order(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    _ensure_can_pay(request, order)
    if order.paid:
        return RedirectResponse(url="/orders", status_code=303)

    payment = create_mock_payment(order)
    set_payment_pending(order.id, payment.payment_id)
    add_order_event(order.id, "payment", "Запущена тестовая оплата", _actor(request))
    return RedirectResponse(url=payment.payment_url, status_code=303)


@app.get("/payments/mock/{payment_id}", response_class=HTMLResponse)
def payment_mock_page(request: Request, payment_id: str):
    redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        order = get_order_by_payment_id(payment_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Payment not found")
    _ensure_can_pay(request, order)
    return templates.TemplateResponse(
        request,
        "payment_mock.html",
        {"request": request, "order": order, "payment_id": payment_id},
    )


@app.post("/payments/mock/{payment_id}/success")
def payment_mock_success(request: Request, payment_id: str):
    redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        order = get_order_by_payment_id(payment_id)
        _ensure_can_pay(request, order)
        mark_paid_by_payment_id(payment_id)
        add_order_event(order.id, "payment", "Тестовая оплата выполнена", _actor(request))
    except ValueError:
        raise HTTPException(status_code=404, detail="Payment not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/payments/mock/{payment_id}/fail")
def payment_mock_fail(request: Request, payment_id: str):
    redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        order = get_order_by_payment_id(payment_id)
        _ensure_can_pay(request, order)
        mark_payment_failed(payment_id)
        add_order_event(order.id, "payment", "Тестовая оплата отменена", _actor(request))
    except ValueError:
        raise HTTPException(status_code=404, detail="Payment not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.get("/orders/{order_id}/history", response_class=HTMLResponse)
def order_history(request: Request, order_id: int):
    redirect = _require_user(request)
    if redirect:
        return redirect
    try:
        order = get_order(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    _ensure_can_view_order(request, order)
    return templates.TemplateResponse(
        request,
        "order_history.html",
        {
            "request": request,
            "order": order,
            "events": list_order_events(order.id),
            "user_name": get_user_name(request),
            "user_role": get_user_role(request),
        },
    )
