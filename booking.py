from db import db_cursor


DEFAULT_SERVICE = "standard_cleaning"


def upsert_customer(phone: str) -> int:
    with db_cursor() as (_, cur):
        cur.execute("INSERT OR IGNORE INTO customers(phone) VALUES (?)", (phone,))
        cur.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
        return int(cur.fetchone()["id"])


def save_state(phone: str, intent: str, requested_date: str | None, requested_time_window: str | None, service_type: str | None) -> None:
    with db_cursor() as (_, cur):
        cur.execute(
            """
            INSERT INTO conversation_state(phone, last_intent, pending_date, pending_time_window, pending_service, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone) DO UPDATE SET
                last_intent = excluded.last_intent,
                pending_date = excluded.pending_date,
                pending_time_window = excluded.pending_time_window,
                pending_service = excluded.pending_service,
                updated_at = CURRENT_TIMESTAMP
            """,
            (phone, intent, requested_date, requested_time_window, service_type),
        )


def check_availability(requested_date: str | None = None):
    query = """
        SELECT appointment_date, time_window
        FROM appointments
        WHERE status = 'available'
    """
    params: list[str] = []
    if requested_date:
        query += " AND appointment_date = ?"
        params.append(requested_date)
    query += " ORDER BY appointment_date, time_window LIMIT 3"

    with db_cursor() as (_, cur):
        cur.execute(query, params)
        return cur.fetchall()


def make_reservation(phone: str, requested_date: str | None, requested_time_window: str | None, service_type: str | None):
    customer_id = upsert_customer(phone)
    service = service_type or DEFAULT_SERVICE

    query = """
        SELECT id, appointment_date, time_window
        FROM appointments
        WHERE status = 'available'
    """
    params: list[str] = []
    if requested_date:
        query += " AND appointment_date = ?"
        params.append(requested_date)
    if requested_time_window:
        query += " AND time_window = ?"
        params.append(requested_time_window)
    query += " ORDER BY appointment_date, time_window LIMIT 1"

    with db_cursor() as (_, cur):
        cur.execute(query, params)
        slot = cur.fetchone()
        if not slot:
            return None
        cur.execute(
            """
            UPDATE appointments
            SET status='booked', customer_id=?, service_type=?
            WHERE id=?
            """,
            (customer_id, service, slot["id"]),
        )
        return slot


def latest_customer_appointment(phone: str):
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT a.id, a.appointment_date, a.time_window
            FROM appointments a
            JOIN customers c ON c.id = a.customer_id
            WHERE c.phone = ? AND a.status = 'booked'
            ORDER BY a.created_at DESC
            LIMIT 1
            """,
            (phone,),
        )
        return cur.fetchone()


def cancel_reservation(phone: str):
    appointment = latest_customer_appointment(phone)
    if not appointment:
        return None

    with db_cursor() as (_, cur):
        cur.execute(
            """
            UPDATE appointments
            SET status='available', customer_id=NULL
            WHERE id=?
            """,
            (appointment["id"],),
        )
    return appointment


def reschedule_reservation(phone: str, requested_date: str | None, requested_time_window: str | None):
    current = latest_customer_appointment(phone)
    if not current:
        return None, None

    new_slot = make_reservation(phone, requested_date, requested_time_window, DEFAULT_SERVICE)
    if not new_slot:
        return current, None

    with db_cursor() as (_, cur):
        cur.execute(
            """
            UPDATE appointments
            SET status='available', customer_id=NULL
            WHERE id=?
            """,
            (current["id"],),
        )
    return current, new_slot
