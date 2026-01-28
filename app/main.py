from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlite3 import IntegrityError

from .db import init_db
from .auth import (
    ROLES,
    create_user,
    authenticate,
    get_user_name,
    get_user_role,
    set_user_session,
    clear_user_session,
)
from .storage import (
    list_orders,
    create_order,
    take_order,
    complete_order,
    set_status,
    mark_paid,
)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="dev-secret")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


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


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный логин или пароль"},
            status_code=400,
        )
    set_user_session(request, user["id"], user["username"], user["role"])
    return RedirectResponse(url="/orders", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


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
    except IntegrityError:
        return templates.TemplateResponse(
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
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request):
    redirect = _require_user(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(
        "orders.html",
        {
            "request": request,
            "orders": list_orders(),
            "user_name": get_user_name(request),
            "user_role": get_user_role(request),
        },
    )


@app.get("/orders/new", response_class=HTMLResponse)
def orders_new(request: Request):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"customer", "admin"})
    return templates.TemplateResponse(
        "orders_new.html",
        {"request": request, "user_role": get_user_role(request)},
    )


@app.post("/orders/new")
def orders_create(
    request: Request,
    address: str = Form(...),
    description: str = Form(""),
    price: int = Form(0),
):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"customer", "admin"})
    create_order(address, description, price)
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/take")
def orders_take(request: Request, order_id: int, assignee: str = Form(...)):
    redirect = _require_user(request)
    if redirect:
        return redirect
    _require_role(request, {"worker", "admin"})
    try:
        take_order(order_id, assignee)
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
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)
