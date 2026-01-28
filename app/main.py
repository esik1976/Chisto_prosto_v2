from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .storage import (
    list_orders,
    create_order,
    take_order,
    complete_order,
    set_status,
    mark_paid,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request):
    return templates.TemplateResponse(
        "orders.html",
        {"request": request, "orders": list_orders()},
    )


@app.get("/orders/new", response_class=HTMLResponse)
def orders_new(request: Request):
    return templates.TemplateResponse("orders_new.html", {"request": request})


@app.post("/orders/new")
def orders_create(
    address: str = Form(...),
    description: str = Form(""),
    price: int = Form(0),
):
    create_order(address, description, price)
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/take")
def orders_take(order_id: int, assignee: str = Form(...)):
    try:
        take_order(order_id, assignee)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/complete")
def orders_complete(order_id: int):
    try:
        complete_order(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/status")
def orders_status(order_id: int, status: str = Form(...)):
    try:
        set_status(order_id, status)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)


@app.post("/orders/{order_id}/pay")
def orders_pay(order_id: int):
    try:
        mark_paid(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")
    return RedirectResponse(url="/orders", status_code=303)
