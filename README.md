# LaundryFlow: database work for the DE course

LaundryFlow replaces the paper register at the college laundry. Students submit their laundry from their own account, the staff member at the counter counts the clothes, and the system works out any fine for going over the free limit.

This repository is the **DE course submission** for LaundryFlow's database: 20 marks for normalization, ER diagram, all SQL queries and query analysis. It holds no application code.

The website itself (the AP capstone) is a separate repository, [parth-access/LaundryFlow](https://github.com/parth-access/LaundryFlow). The SQL queries used there are exported into this repository.

## Stack

- **Language:** JavaScript (no TypeScript)
- **App:** Next.js 16 (App Router), Tailwind CSS 4
- **Database:** PostgreSQL, plain SQL through the `postgres` driver (no ORM)

## What is in `dbms/`

| File | Content |
| --- | --- |
| `01_normalization.md` | From the paper register (unnormalized) to 1NF, 2NF, 3NF and BCNF, with the final six tables and the deliberate exceptions |
| `02_er_diagram.png` | ER diagram of the six tables: keys, foreign keys and crow's-foot cardinality (source: `02_er_diagram.mmd`, Mermaid) |
| `03_schema.sql` | The PostgreSQL schema: six tables with keys, CHECK constraints, indexes and the starting policy (10 free, Rs 5 per extra) |
| `04_queries.sql` | Every SQL query the LaundryFlow app runs (R = read, W = write), with its purpose and parameters; exported from the app with `npm run queries:export` |
| `generate_data.py` | Large test dataset for the query timings: 2,000 students, ~48,800 orders as one timeline per student (never two open bags), ~14,200 fines and ~1,400 recount records. Same seed = same rows for everyone. `python3 dbms/generate_data.py > /tmp/lf.sql`, then load it after `03_schema.sql` |
| `time_queries.py` | Times every query in `04_queries.sql` 5 times on the large dataset with `EXPLAIN (ANALYZE, BUFFERS)`; writes are rolled back |
| `05_query_timings.md` | Timings of all 36 queries on the large dataset, how the indexes are used, the slowest queries and a tested fix for R42 |
| `plans/` | The plan of every run, and `summary.csv` |


## Team (Team T0016, Section E)

| Name | GitHub |
| --- | --- |
| Parth Saarthi Chhikara | [parth-access](https://github.com/parth-access) |
| Tanishq Tyagi | [tanishqt25](https://github.com/tanishqt25) |
| Dhruv Maan | [dhruvm25142-eng](https://github.com/dhruvm25142-eng) |
| Aarabdh Sharma | [aarabdh-ICA](https://github.com/aarabdh-ICA) |
