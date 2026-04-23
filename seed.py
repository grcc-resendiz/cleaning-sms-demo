from datetime import date, timedelta

from db import db_cursor, init_db

DEFAULT_SERVICE = "standard_cleaning"
TIME_WINDOWS = ["9am-11am", "12pm-2pm", "3pm-5pm"]
DEMO_PHONE = "+15550001111"


def seed_next_7_days() -> None:
    init_db()

    with db_cursor() as (_, cur):
        cur.execute("DELETE FROM appointments")
        cur.execute("DELETE FROM customers")

        for offset in range(7):
            day = (date.today() + timedelta(days=offset)).isoformat()
            for window in TIME_WINDOWS:
                cur.execute(
                    """
                    INSERT INTO appointments (service_type, appointment_date, time_window, status)
                    VALUES (?, ?, ?, 'available')
                    """,
                    (DEFAULT_SERVICE, day, window),
                )

        cur.execute("INSERT INTO customers (phone, name) VALUES (?, ?)", (DEMO_PHONE, "Demo Customer"))
        customer_id = cur.lastrowid

        sample_date = (date.today() + timedelta(days=1)).isoformat()
        cur.execute(
            """
            UPDATE appointments
            SET status='booked', customer_id=?
            WHERE id = (
                SELECT id FROM appointments
                WHERE appointment_date=? AND time_window='12pm-2pm' AND status='available'
                LIMIT 1
            )
            """,
            (customer_id, sample_date),
        )


if __name__ == "__main__":
    seed_next_7_days()
    print(f"Seeded appointments for next 7 days with demo booking for {DEMO_PHONE}.")
