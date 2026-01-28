from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .storage import list_orders, create_order

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


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
