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
| `03_schema.sql` | The PostgreSQL schema: six tables with keys, CHECK constraints, indexes and the starting policy (10 free, Rs 5 per extra) |

The ER diagram, the queries (`04_queries.sql`) and their analysis will be added here as they are finished.

## Team (Team T0016, Section E)

| Name | GitHub |
| --- | --- |
| Parth Saarthi Chhikara | [parth-access](https://github.com/parth-access) |
| Tanishq Tyagi | [tanishqt25](https://github.com/tanishqt25) |
| Dhruv Maan | [dhruvm25142-eng](https://github.com/dhruvm25142-eng) |
| Aarabdh Sharma | [aarabdh-ICA](https://github.com/aarabdh-ICA) |
