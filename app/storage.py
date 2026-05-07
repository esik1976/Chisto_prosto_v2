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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    customer_id: Optional[int] = None
    payment_status: str = "not_started"
    payment_id: Optional[str] = None


@dataclass
class OrderEvent:
    id: int
    order_id: int
    event_type: str
    message: str
    actor: Optional[str]
    created_at: str


def _row_to_order(row) -> Order:
    return Order(
        id=row["id"],
        address=row["address"],
        description=row["description"] or "",
        price=row["price"] or 0,
        status=row["status"] or "new",
        assignee=row["assignee"],
        paid=bool(row["paid"]),
        latitude=row["latitude"],
        longitude=row["longitude"],
        customer_id=row["customer_id"],
        payment_status=row["payment_status"] or "not_started",
        payment_id=row["payment_id"],
    )


def _select_orders(where: str = "", params: tuple = ()) -> List[Order]:
    query = """
        SELECT id, address, description, price, status, assignee, paid, latitude, longitude, customer_id,
               payment_status, payment_id
        FROM orders
    """
    if where:
        query += f" WHERE {where}"
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_order(row) for row in rows]


def _row_to_event(row) -> OrderEvent:
    return OrderEvent(
        id=row["id"],
        order_id=row["order_id"],
        event_type=row["event_type"],
        message=row["message"],
        actor=row["actor"],
        created_at=row["created_at"],
    )


def list_orders() -> List[Order]:
    return _select_orders()


def list_orders_for_customer(customer_id: int) -> List[Order]:
    return _select_orders("customer_id = ?", (customer_id,))


def list_orders_for_worker(worker_name: str) -> List[Order]:
    return _select_orders(
        "status = ? OR assignee = ?",
        ("new", worker_name),
    )


def get_order(order_id: int) -> Order:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, address, description, price, status, assignee, paid, latitude, longitude, customer_id,
                   payment_status, payment_id
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
    if not row:
        raise ValueError("Order not found")
    return _row_to_order(row)


def get_order_by_payment_id(payment_id: str) -> Order:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, address, description, price, status, assignee, paid, latitude, longitude, customer_id,
                   payment_status, payment_id
            FROM orders
            WHERE payment_id = ?
            """,
            (payment_id,),
        ).fetchone()
    if not row:
        raise ValueError("Order not found")
    return _row_to_order(row)


def create_order(
    address: str,
    description: str,
    price: int,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    customer_id: Optional[int] = None,
) -> Order:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO orders (
                address, description, price, status, assignee, paid, latitude, longitude, customer_id,
                payment_status, payment_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                address,
                description,
                price,
                "new",
                None,
                0,
                latitude,
                longitude,
                customer_id,
                "not_started",
                None,
            ),
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
            "UPDATE orders SET paid = ?, payment_status = ? WHERE id = ?",
            (1, "paid", order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def set_payment_pending(order_id: int, payment_id: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET payment_status = ?, payment_id = ? WHERE id = ?",
            ("pending", payment_id, order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def mark_paid_by_payment_id(payment_id: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET paid = ?, payment_status = ? WHERE payment_id = ?",
            (1, "paid", payment_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def mark_payment_failed(payment_id: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET payment_status = ? WHERE payment_id = ?",
            ("failed", payment_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def add_order_event(
    order_id: int,
    event_type: str,
    message: str,
    actor: Optional[str] = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO order_events (order_id, event_type, message, actor)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, event_type, message, actor),
        )


def list_order_events(order_id: int) -> List[OrderEvent]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, order_id, event_type, message, actor, created_at
            FROM order_events
            WHERE order_id = ?
            ORDER BY id DESC
            """,
            (order_id,),
        ).fetchall()
    return [_row_to_event(row) for row in rows]
