-- LaundryFlow: database schema (PostgreSQL 15+, runs on Supabase)
-- Built from dbms/01_normalization.md: six tables, all in BCNF.
-- Run on an empty database:  psql "$DATABASE_URL" -f dbms/03_schema.sql
-- Re-running is safe: it drops and recreates the six tables (and their data).

BEGIN;

DROP TABLE IF EXISTS order_changes, fines, orders, policies, students, staff CASCADE;

-- ---------------------------------------------------------------------------
-- STAFF: people who work at the laundry counter or manage it.
-- ---------------------------------------------------------------------------
CREATE TABLE staff (
    staff_id    INT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name   TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    email       TEXT NOT NULL UNIQUE CHECK (email = lower(email) AND email LIKE '%_@_%'),
    role        TEXT NOT NULL CHECK (role IN ('COUNTER', 'ADMIN')),
    is_active   BOOLEAN NOT NULL DEFAULT true
);

-- ---------------------------------------------------------------------------
-- STUDENTS: self-registered; the bag tag (B/G + number) is never reassigned.
-- ---------------------------------------------------------------------------
CREATE TABLE students (
    student_id       INT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    enrollment_no    TEXT NOT NULL UNIQUE CHECK (enrollment_no ~ '^[0-9]{10}$'),
    full_name        TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    email            TEXT NOT NULL UNIQUE CHECK (email = lower(email) AND email LIKE '%_@_%'),
    bag_prefix       CHAR(1) NOT NULL CHECK (bag_prefix IN ('B', 'G')),
    bag_number       INT  NOT NULL CHECK (bag_number > 0),
    bag_verified_at  TIMESTAMPTZ,
    bag_verified_by  INT REFERENCES staff (staff_id) ON DELETE RESTRICT,
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_students_bag UNIQUE (bag_prefix, bag_number),
    -- a bag is verified by someone at some time, or not at all
    CONSTRAINT ck_students_bag_verified
        CHECK ((bag_verified_at IS NULL) = (bag_verified_by IS NULL))
);

-- ---------------------------------------------------------------------------
-- POLICIES: never edited; a new rule is a new row with a later date.
-- ---------------------------------------------------------------------------
CREATE TABLE policies (
    policy_id       INT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    effective_from  DATE NOT NULL UNIQUE,
    free_limit      INT  NOT NULL CHECK (free_limit > 0),
    fine_per_extra  NUMERIC(6,2) NOT NULL CHECK (fine_per_extra >= 0)
);

-- ---------------------------------------------------------------------------
-- ORDERS: one bag handed in once.
-- SUBMITTED -> RECEIVED (counted) -> READY -> COLLECTED, or CANCELLED / DISPUTED.
-- order_status is stored on purpose (see 01_normalization.md section 6);
-- the CHECKs below keep it consistent with the timestamps.
-- ---------------------------------------------------------------------------
CREATE TABLE orders (
    order_id        INT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id      INT  NOT NULL REFERENCES students (student_id) ON DELETE RESTRICT,
    policy_id       INT  REFERENCES policies (policy_id) ON DELETE RESTRICT,
    order_status    TEXT NOT NULL DEFAULT 'SUBMITTED'
                    CHECK (order_status IN ('SUBMITTED','RECEIVED','READY','COLLECTED','CANCELLED','DISPUTED')),
    declared_count  INT  NOT NULL CHECK (declared_count > 0 AND declared_count <= 100),
    verified_count  INT  CHECK (verified_count >= 0 AND verified_count <= 100),
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    received_at     TIMESTAMPTZ,
    received_by     INT REFERENCES staff (staff_id) ON DELETE RESTRICT,
    ready_at        TIMESTAMPTZ,
    collected_at    TIMESTAMPTZ,
    collected_by    INT REFERENCES staff (staff_id) ON DELETE RESTRICT,

    -- counting happens all at once: who, when, how many, under which policy
    CONSTRAINT ck_orders_received_together CHECK (
        (received_at IS NULL) = (received_by IS NULL) AND
        (received_at IS NULL) = (verified_count IS NULL) AND
        (received_at IS NULL) = (policy_id IS NULL)),
    CONSTRAINT ck_orders_collected_together CHECK ((collected_at IS NULL) = (collected_by IS NULL)),

    -- milestones happen in order
    CONSTRAINT ck_orders_time_order CHECK (
        (received_at  IS NULL OR received_at  >= submitted_at) AND
        (ready_at     IS NULL OR (received_at IS NOT NULL AND ready_at >= received_at)) AND
        (collected_at IS NULL OR (ready_at    IS NOT NULL AND collected_at >= ready_at))),

    -- the status matches the milestones reached (CANCELLED / DISPUTED are free-standing)
    CONSTRAINT ck_orders_status_matches CHECK (
        order_status IN ('CANCELLED','DISPUTED') OR
        (order_status = 'SUBMITTED' AND received_at IS NULL) OR
        (order_status = 'RECEIVED'  AND received_at IS NOT NULL AND ready_at IS NULL) OR
        (order_status = 'READY'     AND ready_at IS NOT NULL AND collected_at IS NULL) OR
        (order_status = 'COLLECTED' AND collected_at IS NOT NULL))
);

-- ---------------------------------------------------------------------------
-- FINES: at most one per order, only when clothes went over the free limit.
-- fine_amount is stored on purpose (a money record must not move if a policy
-- row is corrected); a check query in 04_queries.sql will verify it.
-- ---------------------------------------------------------------------------
CREATE TABLE fines (
    order_id       INT PRIMARY KEY REFERENCES orders (order_id) ON DELETE CASCADE,
    fine_amount    NUMERIC(8,2) NOT NULL CHECK (fine_amount > 0),
    fine_status    TEXT NOT NULL DEFAULT 'UNPAID' CHECK (fine_status IN ('UNPAID','PAID','WAIVED')),
    fine_paid_at   TIMESTAMPTZ,
    waived_by      INT REFERENCES staff (staff_id) ON DELETE RESTRICT,
    waiver_reason  TEXT,
    CONSTRAINT ck_fines_paid    CHECK ((fine_status = 'PAID') = (fine_paid_at IS NOT NULL)),
    CONSTRAINT ck_fines_waived  CHECK (
        (fine_status = 'WAIVED') = (waived_by IS NOT NULL) AND
        (fine_status = 'WAIVED') = (waiver_reason IS NOT NULL AND length(trim(waiver_reason)) > 0))
);

-- ---------------------------------------------------------------------------
-- ORDER_CHANGES: audit trail. Every correction after counting is recorded,
-- numbered 1, 2, 3... within its order.
-- ---------------------------------------------------------------------------
CREATE TABLE order_changes (
    order_id       INT  NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    change_no      INT  NOT NULL CHECK (change_no > 0),
    changed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    changed_by     INT  NOT NULL REFERENCES staff (staff_id) ON DELETE RESTRICT,
    field_changed  TEXT NOT NULL CHECK (field_changed IN ('verified_count','order_status','fine_status','declared_count')),
    old_value      TEXT,
    new_value      TEXT,
    reason         TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    PRIMARY KEY (order_id, change_no)
);

-- ---------------------------------------------------------------------------
-- Indexes for the screens we know we need
-- ---------------------------------------------------------------------------
-- Counter types "1054" and picks B or G: lookup by number first.
-- (The UNIQUE (bag_prefix, bag_number) index starts with the prefix, so it cannot serve this.)
CREATE INDEX ix_students_bag_number ON students (bag_number, bag_prefix);

-- A student's history, newest first.
CREATE INDEX ix_orders_student ON orders (student_id, submitted_at DESC);

-- Counter queue and "ready to collect" lists: only open orders, oldest first.
CREATE INDEX ix_orders_open ON orders (order_status, submitted_at)
    WHERE order_status IN ('SUBMITTED','RECEIVED','READY');

-- Unpaid fines report.
CREATE INDEX ix_fines_unpaid ON fines (order_id) WHERE fine_status = 'UNPAID';

-- Foreign keys that are searched from the staff side.
CREATE INDEX ix_orders_received_by ON orders (received_by);
CREATE INDEX ix_order_changes_changed_by ON order_changes (changed_by);

-- ---------------------------------------------------------------------------
-- Starting data: the current college rule (10 clothes free, Rs 5 per extra).
-- ---------------------------------------------------------------------------
INSERT INTO policies (effective_from, free_limit, fine_per_extra) VALUES ('2026-01-01', 10, 5.00);

COMMIT;
