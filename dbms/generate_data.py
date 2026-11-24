"""
LaundryFlow: large test dataset for query timings (DE course, dbms/05_query_timings.md).

Writes plain SQL INSERTs that load on top of dbms/03_schema.sql:

    python3 dbms/generate_data.py > /tmp/laundryflow_data.sql
    psql "$DATABASE_URL" -f dbms/03_schema.sql
    psql "$DATABASE_URL" -f /tmp/laundryflow_data.sql

Same seed = same data every run, so everyone's timings use identical rows.
Only uses the Python standard library.

OWNER: Parth (staff, students), Dhruv (orders, fines, order changes).
"""
import random
from datetime import datetime, timedelta, timezone

SEED = 2026
N_STAFF = 12
N_STUDENTS = 2000
N_ORDERS = 50_000            # about 25 bags per student over the term
IST = timezone(timedelta(hours=5, minutes=30))
START = datetime(2026, 1, 5, tzinfo=IST)
NOW = datetime(2026, 11, 23, 20, 0, tzinfo=IST)   # "today" in the data: open orders are the recent ones
FREE_LIMIT, FINE_PER_EXTRA = 10, 5                  # policy 1 in 03_schema.sql

rng = random.Random(SEED)
FIRST = ["Aman", "Riya", "Kabir", "Meera", "Arjun", "Isha", "Rohan", "Ananya", "Vikram", "Sneha", "Dev", "Pooja", "Karan", "Nisha", "Aditya", "Tanvi"]
LAST = ["Sharma", "Verma", "Singh", "Iyer", "Gupta", "Mehta", "Reddy", "Nair", "Chopra", "Joshi", "Kapoor", "Das"]
SUBDOMAINS = ["nst", "nst", "nst", "cse", "design", "psy"]   # mostly NST, as in the real college


def q(value):
    """SQL literal: NULL, number, or quoted text."""
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def insert(table, cols, rows, batch=1000, overriding=False):
    over = " OVERRIDING SYSTEM VALUE" if overriding else ""
    for i in range(0, len(rows), batch):
        values = ",\n".join("(" + ", ".join(q(v) for v in r) + ")" for r in rows[i:i + batch])
        print(f"INSERT INTO {table} ({', '.join(cols)}){over} VALUES\n{values};")


def ts(moment):
    return None if moment is None else moment.isoformat()


def make_staff():
    rows = [("Admin One", "admin1@laundry.example", "ADMIN")]
    for i in range(2, N_STAFF + 1):
        rows.append((f"Counter Staff {i}", f"staff{i}@laundry.example", "COUNTER"))
    insert("staff", ["full_name", "email", "role"], rows)
    return len(rows)


def make_students():
    rows, used_bags = [], set()
    for i in range(1, N_STUDENTS + 1):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        prefix = "B" if rng.random() < 0.55 else "G"
        while True:                                   # bag tags are unique and never reused
            number = rng.randint(1, 3500)
            if (prefix, number) not in used_bags:
                used_bags.add((prefix, number)); break
        enrollment = f"25010{i:05d}"                  # 10 digits, unique
        email = f"{name.split()[0].lower()}.{i}@{rng.choice(SUBDOMAINS)}.rishihood.edu.in"
        verified = rng.random() < 0.9                 # most bags already checked by staff
        at = (START + timedelta(days=rng.randint(0, 20))).isoformat() if verified else None
        by = rng.randint(1, N_STAFF) if verified else None
        active = rng.random() > 0.02
        rows.append((enrollment, name, email, prefix, number, at, by, active))
    insert("students", ["enrollment_no", "full_name", "email", "bag_prefix", "bag_number",
                        "bag_verified_at", "bag_verified_by", "is_active"], rows)


def hand_in_time(day):
    """A hand-in time on `day`: weekends get more bags, and people come between 8:00 and 21:00."""
    if day.weekday() < 5 and rng.random() < 0.45:     # many weekday bags wait for the weekend
        day += timedelta(days=5 - day.weekday() + rng.randint(0, 1))
    return day.replace(hour=rng.randint(8, 20), minute=rng.randint(0, 59), second=rng.randint(0, 59))


def make_orders():
    """
    Every student gets a timeline of bags. A bag is collected before the next one is
    handed in, so a student never has two open orders (uq_orders_one_open_per_student).
    Only a student's LAST bag can still be open, and only if its steps are after NOW.

    Every row passes the CHECKs in 03_schema.sql:
      * received_at, received_by, verified_count and policy_id are all set together
      * submitted <= received <= ready <= collected
      * order_status matches the steps reached (CANCELLED / DISPUTED stand alone)
    Returns the counted orders, for make_fines() and make_changes().
    """
    per_student = N_ORDERS // N_STUDENTS
    rows, counted = [], []
    order_id = 0
    for student_id in range(1, N_STUDENTS + 1):
        day = START + timedelta(days=rng.randint(0, 10))
        for _ in range(per_student):
            submitted = hand_in_time(day)
            if submitted >= NOW:
                break
            order_id += 1
            declared = max(1, min(100, int(rng.gauss(9, 3))))
            roll = rng.random()

            if roll < 0.02:                            # handed in by mistake, cancelled before counting
                rows.append((order_id, student_id, None, "CANCELLED", declared, None,
                             ts(submitted), None, None, None, None, None))
                day = submitted + timedelta(days=rng.randint(1, 4))
                continue

            received = submitted + timedelta(minutes=rng.randint(20, 6 * 60))
            ready = received + timedelta(hours=rng.randint(12, 48))
            collected = ready + timedelta(hours=rng.randint(2, 72))
            if roll < 0.85:
                verified = declared                    # most students count right
            elif roll < 0.97:
                verified = min(100, declared + rng.randint(1, 5))   # under-declared: a fine if over 10
            else:
                verified = max(1, declared - rng.randint(1, 2))
            staff_in, staff_out = rng.randint(2, N_STAFF), rng.randint(2, N_STAFF)

            if roll >= 0.99:                           # student disputes the count
                status, ready, collected = "DISPUTED", None, None
            elif received > NOW:                       # the steps that have not happened yet stay empty
                status, received, ready, collected = "SUBMITTED", None, None, None
            elif ready > NOW:
                status, ready, collected = "RECEIVED", None, None
            elif collected > NOW:
                status, collected = "READY", None
            else:
                status = "COLLECTED"
            if collected is None:
                staff_out = None

            if received is None:
                rows.append((order_id, student_id, None, status, declared, None,
                             ts(submitted), None, None, None, None, None))
            else:
                rows.append((order_id, student_id, 1, status, declared, verified,
                             ts(submitted), ts(received), staff_in, ts(ready), ts(collected), staff_out))
                counted.append({"order_id": order_id, "status": status, "verified": verified,
                                "received": received, "collected": collected})
            if status in ("SUBMITTED", "RECEIVED", "READY"):
                break                                  # still open: no next bag for this student yet
            day = (collected or received) + timedelta(days=rng.randint(4, 14))

    insert("orders", ["order_id", "student_id", "policy_id", "order_status", "declared_count",
                      "verified_count", "submitted_at", "received_at", "received_by", "ready_at",
                      "collected_at", "collected_by"], rows, overriding=True)
    print("SELECT setval(pg_get_serial_sequence('orders', 'order_id'), (SELECT max(order_id) FROM orders));")
    return counted


def make_fines(counted):
    """
    One fine per counted order over the free limit: (verified - 10) * Rs 5.
    Collected bags: mostly PAID when collected, some still UNPAID, a few WAIVED.
    Bags not collected yet: UNPAID.
    """
    reasons = ["Counting error at the counter", "First time over the limit", "Machine damaged clothes",
               "Hostel warden approved", "Medical laundry"]
    rows = []
    for o in counted:
        extra = o["verified"] - FREE_LIMIT
        if extra <= 0:
            continue
        amount = extra * FINE_PER_EXTRA
        status, paid_at, waived_by, reason = "UNPAID", None, None, None
        if o["status"] == "COLLECTED":
            r = rng.random()
            if r < 0.88:
                status, paid_at = "PAID", ts(o["collected"])
            elif r < 0.94:
                status, waived_by, reason = "WAIVED", 1, rng.choice(reasons)
        rows.append((o["order_id"], amount, status, paid_at, waived_by, reason))
    insert("fines", ["order_id", "fine_amount", "fine_status", "fine_paid_at", "waived_by", "waiver_reason"], rows)


def make_changes(counted):
    """
    Audit trail: about 3% of counted bags were recounted after the first count.
    The change records the old count and the count now stored on the order.
    """
    rows = []
    for o in counted:
        if rng.random() >= 0.03:
            continue
        old = max(1, o["verified"] + rng.choice([-2, -1, 1, 2]))
        at = o["received"] + timedelta(minutes=rng.randint(5, 120))
        rows.append((o["order_id"], 1, ts(at), rng.randint(2, N_STAFF), "verified_count",
                     str(old), str(o["verified"]), "Recounted when the student checked the bag"))
    insert("order_changes", ["order_id", "change_no", "changed_at", "changed_by", "field_changed",
                             "old_value", "new_value", "reason"], rows)


if __name__ == "__main__":
    print("-- Generated by dbms/generate_data.py (seed %d). Load after 03_schema.sql." % SEED)
    print("BEGIN;")
    print("TRUNCATE order_changes, fines, orders, students, staff RESTART IDENTITY CASCADE;")
    make_staff()
    make_students()
    counted = make_orders()
    make_fines(counted)
    make_changes(counted)
    print("COMMIT;")
    print("ANALYZE;")
