# LaundryFlow: normalization (1NF, 2NF, 3NF, BCNF)

LaundryFlow replaces the paper register at the college laundry. Students submit an entry, the laundry staff member
verifies the number of clothes at the counter, the system works out the fine, and the bag is handed back against the entry.

## 0. Rules the data follows (assumptions)

1. Every student has **one bag tag**: a prefix (`B` or `G`) and a number, for example `B 1054`. The student enters it when
   signing up, and it is **never reassigned**. `B 1054` and `G 1054` are different bags, so the number alone is not unique.
2. An order is **submitted** by the student, **received** at the counter by one staff member (who counts the clothes),
   becomes **ready**, and is **collected** with a staff member's confirmation.
3. A **policy** says how many clothes are free (`free_limit`, 10) and the fine for each extra one (`fine_per_extra`, 5 rupees).
   A policy never changes: a new rule is a new policy that applies from a date. An order uses the policy in force when it was received.
4. A **fine** exists only for an order whose verified count is above the free limit, and there is at most one fine per order.
5. The verified count can be corrected after the fact. Every correction is logged.
6. A student's bag number is confirmed by staff on the first drop-off (`bag_verified_*`), because students type it themselves.

## 1. Starting point: the paper register as one sheet (unnormalized)

The paper register has three columns: name, enrollment number, number of clothes. The app needs far more, and keeping it
all in one sheet gives this relation. Attributes inside `{ }` are a repeating group.

```
LAUNDRY_SHEET(
  order_id, submitted_at, order_status,
  student_enrollment_no, student_name, student_email,
  bag_tag, bag_verified_at, bag_verified_by_staff_id, bag_verified_by_name,
  declared_count, verified_count, extra_count,
  policy_effective_from, free_limit, fine_per_extra,
  fine_amount, fine_status, fine_paid_at,
  fine_waived_by_staff_id, fine_waived_by_name, waiver_reason,
  received_at, received_by_staff_id, received_by_name,
  ready_at, collected_at, collected_by_staff_id, collected_by_name,
  { change_no, changed_at, changed_by_staff_id, changed_by_name,
    field_changed, old_value, new_value, reason }
)
```

Example rows. The same student appears on every row, and `B 1054` is one text value holding two facts:

| order_id | student_name | student_enrollment_no | bag_tag | declared | verified | fine_amount |
|---|---|---|---|---:|---:|---:|
| 1 | Parth S. Chhikara | 2501010325 | B 1054 | 10 | 12 | 10 |
| 7 | Parth S. Chhikara | 2501010325 | B 1054 | 10 | 10 | (none) |

Problems: the student's name, email and bag are repeated on every order; a staff member's name is repeated on every order they handle;
the corrections are a list inside one row; the fine can be worked out from other columns.

## 2. First normal form (1NF)

Rule: every value is atomic, there are no repeating groups, and the table has a key.

Changes:
- `bag_tag` (`B 1054`) is split into two atomic columns, `bag_prefix` and `bag_number`.
- The repeating group of corrections becomes **one row per correction**. An order with no correction keeps one row with `change_no = 0` and empty change columns.
- The key becomes `(order_id, change_no)`.

```
LAUNDRY_ROW( order_id, change_no,
  submitted_at, order_status,
  student_enrollment_no, student_name, student_email, bag_prefix, bag_number,
  bag_verified_at, bag_verified_by_staff_id, bag_verified_by_name,
  declared_count, verified_count, extra_count,
  policy_effective_from, free_limit, fine_per_extra,
  fine_amount, fine_status, fine_paid_at,
  fine_waived_by_staff_id, fine_waived_by_name, waiver_reason,
  received_at, received_by_staff_id, received_by_name,
  ready_at, collected_at, collected_by_staff_id, collected_by_name,
  changed_at, changed_by_staff_id, changed_by_name, field_changed, old_value, new_value, reason )
  PRIMARY KEY (order_id, change_no)
```

**Functional dependencies (FD):**

| # | Dependency | Meaning |
|---|---|---|
| F1 | order_id to submitted_at, order_status, student_enrollment_no, declared_count, verified_count, extra_count, policy_effective_from, fine_amount, fine_status, fine_paid_at, fine_waived_by_staff_id, waiver_reason, received_at, received_by_staff_id, ready_at, collected_at, collected_by_staff_id | an order fixes all its own facts (one fine per order) |
| F2 | student_enrollment_no to student_name, student_email, bag_prefix, bag_number, bag_verified_at, bag_verified_by_staff_id | a student fixes their profile |
| F3 | student_email to student_enrollment_no | an email belongs to one student |
| F4 | (bag_prefix, bag_number) to student_enrollment_no | a bag tag belongs to one student, forever |
| F5 | staff id to staff name (for bag_verified_by, fine_waived_by, received_by, collected_by, changed_by) | |
| F6 | policy_effective_from to free_limit, fine_per_extra | a policy fixes its values |
| F7 | (verified_count, free_limit) to extra_count; (extra_count, fine_per_extra) to fine_amount | **derived** values |
| F8 | (order_id, change_no) to changed_at, changed_by_staff_id, field_changed, old_value, new_value, reason | a correction |

## 3. Second normal form (2NF)

Rule: 1NF, and no non-key attribute depends on **part** of a composite key.

The key is `(order_id, change_no)`. F1 and everything chained from it (F2 to F7) depend on `order_id` alone, which is part of the key,
so they are **partial dependencies**. Only F8 needs the whole key. We split on that:

```
ORDER_2NF( order_id PK,
  submitted_at, order_status,
  student_enrollment_no, student_name, student_email, bag_prefix, bag_number,
  bag_verified_at, bag_verified_by_staff_id, bag_verified_by_name,
  declared_count, verified_count, extra_count,
  policy_effective_from, free_limit, fine_per_extra,
  fine_amount, fine_status, fine_paid_at,
  fine_waived_by_staff_id, fine_waived_by_name, waiver_reason,
  received_at, received_by_staff_id, received_by_name,
  ready_at, collected_at, collected_by_staff_id, collected_by_name )

ORDER_CHANGE_2NF( order_id, change_no,  PK (order_id, change_no),
  changed_at, changed_by_staff_id, changed_by_name, field_changed, old_value, new_value, reason )
```

Both tables are in 2NF: `ORDER_2NF` has a single-column key, and in `ORDER_CHANGE_2NF` every attribute needs both parts of the key.
Orders without corrections no longer need the empty `change_no = 0` rows. But `ORDER_2NF` still holds student, staff and policy data that does not belong to the order, which is the next step.

## 4. Third normal form (3NF)

Rule: 2NF, and no non-key attribute depends on another non-key attribute (**transitive dependency**).

| Transitive dependency | Fix |
|---|---|
| order_id to student_enrollment_no to student_name, student_email, bag_prefix, bag_number, bag_verified_* (F2) | new table **STUDENTS**, with a surrogate `student_id` as primary key; `enrollment_no`, `email` and `(bag_prefix, bag_number)` stay unique (F3, F4) |
| order_id to received_by / collected_by / bag_verified_by / fine_waived_by / changed_by to staff name (F5) | new table **STAFF**; every `*_by` column becomes a foreign key to `staff_id` |
| order_id to policy_effective_from to free_limit, fine_per_extra (F6) | new table **POLICIES** with `policy_id`; an order keeps only `policy_id` |
| (verified_count, free_limit) to extra_count (F7) | `extra_count` is **not stored**: it is `max(0, verified_count - free_limit)` |

One more split is a design choice, not a 3NF rule: the fine columns are empty for every order within the limit, so they move to a
table **FINES** keyed by `order_id` (an order has 0 or 1 fine). `fine_amount` stays in it on purpose (see section 6).

**Result (3NF):**

```
STUDENTS( student_id PK, enrollment_no UK, full_name, email UK,
          bag_prefix, bag_number,  UK (bag_prefix, bag_number),
          bag_verified_at, bag_verified_by FK -> STAFF, is_active, created_at )
STAFF( staff_id PK, full_name, email UK, role, is_active )
POLICIES( policy_id PK, effective_from UK, free_limit, fine_per_extra )
ORDERS( order_id PK, student_id FK -> STUDENTS, policy_id FK -> POLICIES,
        order_status, declared_count, verified_count,
        submitted_at, received_at, received_by FK -> STAFF,
        ready_at, collected_at, collected_by FK -> STAFF )
FINES( order_id PK/FK -> ORDERS, fine_amount, fine_status, fine_paid_at,
       waived_by FK -> STAFF, waiver_reason )
ORDER_CHANGES( order_id FK -> ORDERS, change_no, PK (order_id, change_no),
               changed_at, changed_by FK -> STAFF, field_changed, old_value, new_value, reason )
```

## 5. Boyce-Codd normal form (BCNF)

Rule: for every functional dependency X to Y, X must be a candidate key (a superkey).

| Table | Candidate keys | Every determinant is a key? |
|---|---|---|
| STUDENTS | `student_id`; `enrollment_no`; `email`; `(bag_prefix, bag_number)` | yes: each key determines the rest, and nothing else determines anything |
| STAFF | `staff_id`; `email` | yes |
| POLICIES | `policy_id`; `effective_from` | yes |
| ORDERS | `order_id` | yes |
| FINES | `order_id` | yes |
| ORDER_CHANGES | `(order_id, change_no)` | yes |

All six tables are in **BCNF**.

A case we avoided: if STUDENTS also stored `hostel_side` (or gender) next to `bag_prefix`, then `bag_prefix` would determine
`hostel_side` without being a key, which breaks BCNF and 3NF. The prefix already carries that fact, so we do not store it twice.

## 6. Deliberate exceptions (stored values that could be derived)

| Column | Why we store it anyway | The cost, and how we control it |
|---|---|---|
| `FINES.fine_amount` | It is a money record: it must not change if a policy row were ever corrected, and "total unpaid fines" becomes a plain `SUM`. | After a correction of `verified_count` the fine must change in the same transaction. A check query in `dbms/04_queries.sql` finds any order whose fine disagrees with `verified_count` and its policy. |
| `ORDERS.order_status` | It is derivable from the milestone timestamps, except `CANCELLED` and `DISPUTED`, which no timestamp shows. It also allows quick filters such as "all READY bags" or "bags not collected after 3 days". | A `CHECK` in `03_schema.sql` ties the status to the timestamps that must be set for it. |

`declared_count` and `verified_count` are **not** duplicates: they are two different facts (what the student said and what the staff
member counted), and the difference between them is useful data.

## 7. Where the paper register columns ended up

| Register column | Now |
|---|---|
| Name | `STUDENTS.full_name` |
| Enrollment number | `STUDENTS.enrollment_no` (kept for the future Rishiverse link; staff search by bag number instead) |
| Number of clothes | `ORDERS.declared_count` (student) and `ORDERS.verified_count` (staff) |
| (not recorded: fine) | `FINES`, from `verified_count` and `POLICIES` |
| (not recorded: who counted, when it was collected) | `ORDERS.received_by`, `received_at`, `collected_by`, `collected_at` |

## 8. Relationships (input for the ER diagram)

| Relationship | Cardinality |
|---|---|
| STUDENTS to ORDERS | 1 : N |
| POLICIES to ORDERS | 1 : N (the policy applied at receipt) |
| ORDERS to FINES | 1 : 0..1 |
| ORDERS to ORDER_CHANGES | 1 : N |
| STAFF to ORDERS | 1 : N twice (`received_by`, `collected_by`) |
| STAFF to STUDENTS | 1 : N (`bag_verified_by`) |
| STAFF to FINES | 1 : N (`waived_by`) |
| STAFF to ORDER_CHANGES | 1 : N (`changed_by`) |
