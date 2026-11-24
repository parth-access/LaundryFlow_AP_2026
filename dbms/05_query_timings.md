# 05 · Query timings on a large dataset

Team T0016 · Section E · CP4

Every SQL query the LaundryFlow app runs (all **36** in `04_queries.sql`: 19 reads, 17 writes), timed on a large generated dataset, with the plan of every run in `plans/`.

## 1. The dataset

Made by `generate_data.py` (seed 2026, so everyone gets identical rows), loaded on top of `03_schema.sql`:

| Table | Rows |
|---|---:|
| students | 2,000 |
| staff | 12 |
| orders | 48,762 |
| fines | 14,172 |
| order_changes | 1,437 |
| policies | 1 |

That is about 25 bags per student from January to November 2026, roughly a full year of a real hostel. Total database size: **18 MB**. Orders are one timeline per student: a bag is collected before the next is handed in, so the "one open order per student" index is never broken, and only the most recent bags are still open (15 waiting at the counter, 130 in the wash, 192 ready for pickup).

## 2. How it was measured

```bash
python3 dbms/generate_data.py > /tmp/lf.sql
createdb laundryflow_large
psql -d laundryflow_large -f dbms/03_schema.sql -f /tmp/lf.sql
python3 dbms/time_queries.py laundryflow_large
```

`time_queries.py` reads each query from `04_queries.sql`, picks realistic parameter values from the data, and runs `EXPLAIN (ANALYZE, BUFFERS)` **5 times**. Some examples of the values it picks:
- the student with the most orders (for history pages)
- a bag that is ready (for the pickup search)
- a bag still waiting (for the receive step)

**Writes run inside `BEGIN … ROLLBACK`**, so they are timed for real but the data is unchanged afterwards.

Environment: PostgreSQL 16.15, Linux x86-64, data fully in memory after the first run. Times are **Execution Time** from the plan, in milliseconds.

## 3. Results

| Query | What it does | Avg (ms) | Median (ms) | Max (ms) | How it reads the data (run 5) |
|---|---|---:|---:|---:|---|
| R01 | Find bags by number | 0.088 | 0.084 | 0.113 | Index Scan using ix_students_bag_number, Index Scan using uq_orders_one_open_per_student |
| R02 | Counter queue: orders waiting to be received | 1.189 | 1.107 | 1.526 | Index Scan using uq_orders_one_open_per_student, Seq Scan |
| R03 | A student's orders with fines | 0.072 | 0.068 | 0.091 | Index Scan using ix_orders_student, Index Scan using fines_pkey |
| R04 | Find a student by email | 0.061 | 0.060 | 0.071 | Index Scan using students_email_key |
| R05 | Find an active staff member by email | 0.039 | 0.037 | 0.046 | Seq Scan |
| W01 | Submit an order | 1.025 | 0.993 | 1.151 | no table scan (insert / constant) |
| W02 | Register a student profile | 0.460 | 0.483 | 0.520 | no table scan (insert / constant) |
| R10 | Check student's active laundry order | 0.025 | 0.020 | 0.041 | Index Scan using uq_orders_one_open_per_student |
| R11 | One of a student's orders, with its fine | 0.064 | 0.065 | 0.068 | Index Scan using orders_pkey, Index Scan using fines_pkey, Seq Scan |
| R12 | A student's fines | 0.112 | 0.103 | 0.151 | Seq Scan, Index Scan using ix_orders_student, Index Scan using fines_pkey |
| R13 | A student's laundry in numbers | 0.108 | 0.106 | 0.115 | Index Scan using ix_orders_student, Index Scan using fines_pkey |
| W10 | Submit order if no active order exists | 0.601 | 0.550 | 0.769 | Index Only Scan using students_pkey, Index Scan using uq_orders_one_open_per_student |
| W11 | Cancel a hand-in | 0.313 | 0.272 | 0.477 | Index Scan using uq_orders_one_open_per_student |
| W12 | Change the clothes count on a hand-in | 0.312 | 0.326 | 0.343 | Index Scan using uq_orders_one_open_per_student |
| R20 | Current fine policy | 0.057 | 0.047 | 0.084 | Seq Scan |
| W20 | Receive a submitted order | 0.765 | 0.781 | 0.882 | Index Scan using orders_pkey |
| W21 | Create an unpaid fine | 0.871 | 0.869 | 0.900 | no table scan (insert / constant) |
| W22 | Verify a bag tag | 0.672 | 0.696 | 0.737 | Index Scan using students_pkey |
| R23 | One order with its student, for the receive page | 0.055 | 0.052 | 0.075 | Index Scan using orders_pkey, Index Scan using students_pkey |
| R30 | Unpaid fines | 8.575 | 8.191 | 10.256 | Seq Scan, Index Scan using ix_fines_unpaid |
| R31 | Orders ready to wash | 1.129 | 1.106 | 1.241 | Index Scan using uq_orders_one_open_per_student, Seq Scan |
| R32 | Orders waiting for pickup | 1.209 | 1.204 | 1.345 | Index Scan using uq_orders_one_open_per_student, Seq Scan |
| R33 | Settled fines (history) | 20.689 | 19.895 | 25.606 | Seq Scan |
| R34 | Find a bag waiting for pickup | 0.145 | 0.147 | 0.162 | Index Scan using ix_students_bag_number, Index Scan using uq_orders_one_open_per_student |
| W30 | Mark order ready | 0.308 | 0.309 | 0.335 | Index Scan using orders_pkey |
| W31 | Mark order collected | 0.551 | 0.547 | 0.601 | Index Scan using orders_pkey |
| W32 | Mark fine paid | 0.236 | 0.248 | 0.260 | Index Scan using ix_fines_unpaid |
| W33 | Waive unpaid fine | 0.481 | 0.481 | 0.521 | Index Scan using ix_fines_unpaid |
| W35 | Mark several orders ready | 1.025 | 0.980 | 1.127 | Index Scan using uq_orders_one_open_per_student |
| W34 | Undo mark ready | 1.116 | 1.181 | 1.712 | Index Scan using orders_pkey, Index Only Scan using order_changes_pkey |
| R40 | All staff | 0.050 | 0.050 | 0.056 | Seq Scan |
| R41 | Fine policy history | 0.059 | 0.058 | 0.064 | Seq Scan |
| R42 | Numbers at a glance | 21.557 | 19.399 | 29.538 | Seq Scan, Index Only Scan using ix_orders_open, Index Scan using ix_fines_unpaid |
| W40 | Add staff | 0.206 | 0.204 | 0.236 | no table scan (insert / constant) |
| W41 | Deactivate or reactivate staff | 0.258 | 0.231 | 0.380 | Seq Scan |
| W42 | New fine policy | 0.237 | 0.233 | 0.267 | no table scan (insert / constant) |

Full plans: `plans/<ID>.txt`; raw numbers: `plans/summary.csv`.

## 4. What the numbers show

**27 of 36 queries take under 1 ms.** Every query a student or the counter waits on is an index lookup:
- finding a bag (R01, R34)
- the student's home and order pages (R03, R10–R13)
- sign-in lookups (R04, R05)
- every button press (all W queries)

Their cost depends on the few rows they return, not on the size of the tables, so they stay this fast as the data grows (a B-tree lookup grows with log n).

**The indexes from `03_schema.sql` are doing their job:**
- `uq_orders_one_open_per_student` serves the counter queue, wash and pickup lists (R02, R31, R32): it only holds the ~340 open orders out of 48,762, so these lists never read the closed history.
- `ix_fines_unpaid` (partial) serves the unpaid fines (R30, R42), reading 954 rows out of 14,172.
- `ix_students_bag_number` serves the bag search (R01).

**The three slowest queries are staff reports**, and each one reads a whole table:

### Rewritten with JOINs (CP3 feedback)

Three queries used subqueries where a JOIN fits. They were rewritten and timed again (same results, checked against the old versions):

| Query | Before | After | Time before → after (median) |
|---|---|---|---|
| W10 | `WHERE NOT EXISTS (SELECT … FROM orders …)` | `LEFT JOIN orders … WHERE o.order_id IS NULL` (anti-join) | 0.741 → 0.550 ms |
| W34 | `coalesce((SELECT max(change_no) …), 0) + 1` | `LEFT JOIN order_changes … GROUP BY`, `coalesce(max(c.change_no), 0) + 1` | 0.744 → 1.181 ms |
| R42 | four scalar subqueries | three one-row aggregates `CROSS JOIN`ed | 19.075 → 19.399 ms |

All three stay in the same range. W34's time is mostly the UPDATE and the foreign-key checks; the join adds a one-row sort. For R42 we also tried counting both order numbers in one pass with `FILTER`: it was no faster and lost the `ix_orders_open` index, so each count keeps its own subquery.

### R33: settled fines history (20.7 ms)
It reads all 13,218 paid or waived fines and joins every order, only to show the newest 50 (`Sort Method: top-N heapsort`). The sort key `coalesce(fine_paid_at, received_at)` mixes two tables, so no index can give the rows already in order. It grows **linearly with the fine history**: about 10× slower after 10 years of data. Fixes, if it ever matters:
- store a `settled_at` column on `fines` (set on Paid or Waive) with an index on it, so the newest 50 come straight from the index
- or only show the last 3 months

### R42: numbers at a glance, "orders today" (19.4 ms) → **0.026 ms with a fix**
The plan shows `Seq Scan on orders … Rows Removed by Filter: 48762` to count **0** rows. The filter is
`(submitted_at AT TIME ZONE 'Asia/Kolkata')::date = (now() AT TIME ZONE 'Asia/Kolkata')::date`, and converting the column to a date hides it from any index. We tested the fix: compare the raw column to the start and end of today in India time, plus an index on `orders (submitted_at)`:

```sql
WHERE submitted_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata'
  AND submitted_at <  (date_trunc('day', now() AT TIME ZONE 'Asia/Kolkata') + interval '1 day') AT TIME ZONE 'Asia/Kolkata'
```
```
before: Seq Scan on orders (actual rows=0)  Rows Removed by Filter: 48762   Execution Time: 18.095 ms
after:  Index Only Scan using ix_orders_submitted_at on orders (actual rows=0)  Execution Time: 0.026 ms
```
Same answer, about **700× faster**, and it stays flat as orders grow. This is the one change we recommend making in the app.

### R30: unpaid fines list (8.6 ms)
It starts from the 954 unpaid fines (using `ix_fines_unpaid`), but the planner then hashes them against a **Seq Scan of all 48,762 orders** instead of looking each order up by its primary key. With only 954 rows that is still the cheaper plan today. As orders grow, the planner switches to index lookups by itself once the full scan costs more, so we leave it.

**Writes:** every W query is 0.2–1.1 ms, including the transaction-style ones:
- W10, submit only if there is no open order
- W34, undo plus an audit row in one statement
- W35, marking 20 bags ready in one UPDATE

The partial unique index makes W10's "only one open order" check cost almost nothing.

## 5. Summary

| | Count |
|---|---:|
| Queries timed | 36 |
| Under 1 ms | 27 |
| 1–10 ms | 7 |
| 10–25 ms | 2 |
| Slowest | R33, 20.7 ms |

Nothing a student waits on is slow. The only queries that grow with the size of the history are two staff reports (R33, R42), and R42 has a tested 700× fix.
