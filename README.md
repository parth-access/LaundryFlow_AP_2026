# LaundryFlow (AP and DE submission)

LaundryFlow replaces the paper register at the college laundry. Students submit their laundry from their own account, the staff member at the counter counts the clothes, and the system works out any fine for going over the free limit.

This repository holds the **database design** of LaundryFlow. It is the part of the project that is also marked in the DE course (20 marks: normalization, ER diagram, SQL queries, query analysis).

The application code is in a separate repository: [parth-access/LaundryFlow](https://github.com/parth-access/LaundryFlow).

## Stack

- **Language:** JavaScript (no TypeScript)
- **App:** Next.js 16 (App Router), Tailwind CSS 4
- **Database:** PostgreSQL, plain SQL through the `postgres` driver (no ORM)

## What is in `dbms/`

| File | Content |
| --- | --- |
| `01_normalization.md` | From the paper register (unnormalized) to 1NF, 2NF, 3NF and BCNF, with the final six tables and the deliberate exceptions |
| `03_schema.sql` | The PostgreSQL schema: six tables with keys, CHECK constraints, indexes and the starting policy (10 free, Rs 5 per extra) |

The ER diagram, the schema (`.sql`), the queries and their analysis will be added here as they are finished.

## Team (Team T0016, Section E)

| Name | GitHub |
| --- | --- |
| Parth Saarthi Chhikara | [parth-access](https://github.com/parth-access) |
| Tanishq Tyagi | [tanishqt25](https://github.com/tanishqt25) |
| Dhruv Maan | [dhruvm25142-end](https://github.com/dhruvm25142-end) |
| Aarabdh Sharma | [aarabdh-ICA](https://github.com/aarabdh-ICA) |
