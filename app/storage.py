from dataclasses import dataclass
from typing import List


@dataclass
class Order:
    id: int
    address: str
    description: str
    price: int
    status: str = "new"


_orders: List[Order] = []
_next_id = 1


def list_orders():
    return _orders


def create_order(address: str, description: str, price: int) -> Order:
    global _next_id
    order = Order(id=_next_id, address=address, description=description, price=price)
    _orders.append(order)
    _next_id += 1
    return order
