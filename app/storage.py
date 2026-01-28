from dataclasses import dataclass
from typing import List, Optional

from .db import get_conn


@dataclass
class Order:
    id: int
    address: str
    description: str
    price: int
    status: str = "new"
    assignee: Optional[str] = None
    paid: bool = False


def _row_to_order(row) -> Order:
    return Order(
        id=row["id"],
        address=row["address"],
        description=row["description"] or "",
        price=row["price"] or 0,
        status=row["status"] or "new",
        assignee=row["assignee"],
        paid=bool(row["paid"]),
    )


def list_orders() -> List[Order]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, address, description, price, status, assignee, paid FROM orders ORDER BY id"
        ).fetchall()
    return [_row_to_order(row) for row in rows]


def get_order(order_id: int) -> Order:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, address, description, price, status, assignee, paid FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
    if not row:
        raise ValueError("Order not found")
    return _row_to_order(row)


def create_order(address: str, description: str, price: int) -> Order:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO orders (address, description, price, status, assignee, paid)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (address, description, price, "new", None, 0),
        )
        order_id = cur.lastrowid
    return get_order(order_id)


def take_order(order_id: int, assignee: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET assignee = ?, status = ? WHERE id = ?",
            (assignee, "in_progress", order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def complete_order(order_id: int) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            ("done", order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def set_status(order_id: int, status: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def mark_paid(order_id: int) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET paid = ? WHERE id = ?",
            (1, order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")
