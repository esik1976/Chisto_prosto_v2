from dataclasses import dataclass
from typing import List, Optional

from .db import get_conn, is_postgres, sql


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


@dataclass
class Contract:
    id: int
    order_id: int
    customer_id: Optional[int]
    assignee: str
    price: int
    status: str
    created_at: str
    completed_at: Optional[str]
    address: str


@dataclass
class Review:
    id: int
    order_id: int
    customer_id: Optional[int]
    assignee: str
    rating: int
    comment: str
    created_at: str
    address: str


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
        rows = conn.execute(sql(query), params).fetchall()
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


def _row_to_contract(row) -> Contract:
    return Contract(
        id=row["id"],
        order_id=row["order_id"],
        customer_id=row["customer_id"],
        assignee=row["assignee"],
        price=row["price"] or 0,
        status=row["status"] or "active",
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        address=row["address"] or "",
    )


def _row_to_review(row) -> Review:
    return Review(
        id=row["id"],
        order_id=row["order_id"],
        customer_id=row["customer_id"],
        assignee=row["assignee"],
        rating=row["rating"] or 0,
        comment=row["comment"] or "",
        created_at=row["created_at"],
        address=row["address"] or "",
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
            sql("""
            SELECT id, address, description, price, status, assignee, paid, latitude, longitude, customer_id,
                   payment_status, payment_id
            FROM orders
            WHERE id = ?
            """),
            (order_id,),
        ).fetchone()
    if not row:
        raise ValueError("Order not found")
    return _row_to_order(row)


def get_order_by_payment_id(payment_id: str) -> Order:
    with get_conn() as conn:
        row = conn.execute(
            sql("""
            SELECT id, address, description, price, status, assignee, paid, latitude, longitude, customer_id,
                   payment_status, payment_id
            FROM orders
            WHERE payment_id = ?
            """),
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
        if is_postgres():
            cur = conn.execute(
                """
                INSERT INTO orders (
                    address, description, price, status, assignee, paid, latitude, longitude, customer_id,
                    payment_status, payment_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
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
            order_id = cur.fetchone()["id"]
        else:
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
            sql("UPDATE orders SET assignee = ?, status = ? WHERE id = ?"),
            (assignee, "in_progress", order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def complete_order(order_id: int) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            sql("UPDATE orders SET status = ? WHERE id = ?"),
            ("done", order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def set_status(order_id: int, status: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            sql("UPDATE orders SET status = ? WHERE id = ?"),
            (status, order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def mark_paid(order_id: int) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            sql("UPDATE orders SET paid = ?, payment_status = ? WHERE id = ?"),
            (1, "paid", order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def set_payment_pending(order_id: int, payment_id: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            sql("UPDATE orders SET payment_status = ?, payment_id = ? WHERE id = ?"),
            ("pending", payment_id, order_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def mark_paid_by_payment_id(payment_id: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            sql("UPDATE orders SET paid = ?, payment_status = ? WHERE payment_id = ?"),
            (1, "paid", payment_id),
        )
    if cur.rowcount == 0:
        raise ValueError("Order not found")


def mark_payment_failed(payment_id: str) -> None:
    with get_conn() as conn:
        cur = conn.execute(
            sql("UPDATE orders SET payment_status = ? WHERE payment_id = ?"),
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
            sql("""
            INSERT INTO order_events (order_id, event_type, message, actor)
            VALUES (?, ?, ?, ?)
            """),
            (order_id, event_type, message, actor),
        )


def list_order_events(order_id: int) -> List[OrderEvent]:
    with get_conn() as conn:
        rows = conn.execute(
            sql("""
            SELECT id, order_id, event_type, message, actor, created_at
            FROM order_events
            WHERE order_id = ?
            ORDER BY id DESC
            """),
            (order_id,),
        ).fetchall()
    return [_row_to_event(row) for row in rows]


def create_contract_for_order(order: Order, assignee: str) -> None:
    with get_conn() as conn:
        existing = conn.execute(
            sql("SELECT id FROM contracts WHERE order_id = ?"),
            (order.id,),
        ).fetchone()
        if existing:
            return
        conn.execute(
            sql("""
            INSERT INTO contracts (order_id, customer_id, assignee, price, status)
            VALUES (?, ?, ?, ?, ?)
            """),
            (order.id, order.customer_id, assignee, order.price, "active"),
        )


def set_contract_status_for_order(order_id: int, status: str) -> None:
    completed_at = "CURRENT_TIMESTAMP" if status == "completed" else "NULL"
    with get_conn() as conn:
        conn.execute(
            sql(f"""
            UPDATE contracts
            SET status = ?, completed_at = {completed_at}
            WHERE order_id = ?
            """),
            (status, order_id),
        )


def _select_contracts(where: str = "", params: tuple = ()) -> List[Contract]:
    query = """
        SELECT c.id, c.order_id, c.customer_id, c.assignee, c.price, c.status,
               c.created_at, c.completed_at, o.address
        FROM contracts c
        JOIN orders o ON o.id = c.order_id
    """
    if where:
        query += f" WHERE {where}"
    query += " ORDER BY c.id DESC"
    with get_conn() as conn:
        rows = conn.execute(sql(query), params).fetchall()
    return [_row_to_contract(row) for row in rows]


def list_contracts() -> List[Contract]:
    return _select_contracts()


def list_contracts_for_customer(customer_id: int) -> List[Contract]:
    return _select_contracts("c.customer_id = ?", (customer_id,))


def list_contracts_for_worker(worker_name: str) -> List[Contract]:
    return _select_contracts("c.assignee = ?", (worker_name,))


def create_review(
    order: Order,
    rating: int,
    comment: str,
) -> None:
    if not order.assignee:
        raise ValueError("Order has no assignee")
    with get_conn() as conn:
        conn.execute(
            sql("""
            INSERT INTO reviews (order_id, customer_id, assignee, rating, comment)
            VALUES (?, ?, ?, ?, ?)
            """),
            (order.id, order.customer_id, order.assignee, rating, comment),
        )


def get_review_by_order_id(order_id: int) -> Optional[Review]:
    with get_conn() as conn:
        row = conn.execute(
            sql("""
            SELECT r.id, r.order_id, r.customer_id, r.assignee, r.rating, r.comment,
                   r.created_at, o.address
            FROM reviews r
            JOIN orders o ON o.id = r.order_id
            WHERE r.order_id = ?
            """),
            (order_id,),
        ).fetchone()
    return _row_to_review(row) if row else None


def _select_reviews(where: str = "", params: tuple = ()) -> List[Review]:
    query = """
        SELECT r.id, r.order_id, r.customer_id, r.assignee, r.rating, r.comment,
               r.created_at, o.address
        FROM reviews r
        JOIN orders o ON o.id = r.order_id
    """
    if where:
        query += f" WHERE {where}"
    query += " ORDER BY r.id DESC"
    with get_conn() as conn:
        rows = conn.execute(sql(query), params).fetchall()
    return [_row_to_review(row) for row in rows]


def list_reviews() -> List[Review]:
    return _select_reviews()


def list_reviews_for_customer(customer_id: int) -> List[Review]:
    return _select_reviews("r.customer_id = ?", (customer_id,))


def list_reviews_for_worker(worker_name: str) -> List[Review]:
    return _select_reviews("r.assignee = ?", (worker_name,))


def list_reviewed_order_ids(order_ids: list[int]) -> set[int]:
    if not order_ids:
        return set()
    placeholders = ", ".join(["?"] * len(order_ids))
    with get_conn() as conn:
        rows = conn.execute(
            sql(f"SELECT order_id FROM reviews WHERE order_id IN ({placeholders})"),
            tuple(order_ids),
        ).fetchall()
    return {row["order_id"] for row in rows}
