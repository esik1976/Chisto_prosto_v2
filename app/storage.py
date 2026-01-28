from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Order:
    id: int
    address: str
    description: str
    price: int
    status: str = "new"
    assignee: Optional[str] = None
    paid: bool = False


_orders: List[Order] = []
_next_id = 1


def list_orders():
    return _orders


def get_order(order_id: int) -> Order:
    for order in _orders:
        if order.id == order_id:
            return order
    raise ValueError("Order not found")


def create_order(address: str, description: str, price: int) -> Order:
    global _next_id
    order = Order(id=_next_id, address=address, description=description, price=price)
    _orders.append(order)
    _next_id += 1
    return order


def take_order(order_id: int, assignee: str) -> None:
    order = get_order(order_id)
    order.assignee = assignee
    order.status = "in_progress"


def complete_order(order_id: int) -> None:
    order = get_order(order_id)
    order.status = "done"


def set_status(order_id: int, status: str) -> None:
    order = get_order(order_id)
    order.status = status


def mark_paid(order_id: int) -> None:
    order = get_order(order_id)
    order.paid = True
