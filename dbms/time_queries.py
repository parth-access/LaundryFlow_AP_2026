"""
LaundryFlow: time every app query on the large dataset (DE course, CP4).

    python3 dbms/generate_data.py > /tmp/lf.sql
    createdb laundryflow_large
    psql -d laundryflow_large -f dbms/03_schema.sql -f /tmp/lf.sql
    python3 dbms/time_queries.py laundryflow_large

Reads every query from dbms/04_queries.sql, picks realistic parameter values
from the data (PICK below), and runs each one RUNS times with
EXPLAIN (ANALYZE, BUFFERS). Writes are run inside BEGIN ... ROLLBACK, so the
data is the same after the run. Output:
    dbms/plans/<ID>.txt        the plan of every run
    dbms/plans/summary.csv     id, type, avg/median/min/max ms, scan nodes
Only uses the Python standard library and the psql command.

OWNER: Aarabdh.
"""
import csv
import re
import statistics
import subprocess
import sys
from pathlib import Path

RUNS = 5
HERE = Path(__file__).resolve().parent
PLANS = HERE / "plans"

# For each query: SQL that returns its parameter values from the large data,
# chosen so the query does real work (a busy student, a bag in the right state).
BUSY_STUDENT = "(SELECT student_id FROM orders GROUP BY student_id ORDER BY count(*) DESC, student_id LIMIT 1)"
FREE_STUDENT = ("(SELECT s.student_id FROM students s WHERE s.is_active AND NOT EXISTS "
                "(SELECT 1 FROM orders o WHERE o.student_id = s.student_id "
                "AND o.order_status IN ('SUBMITTED','RECEIVED','READY')) ORDER BY s.student_id LIMIT 1)")
OPEN_ORDER = "(SELECT order_id FROM orders WHERE order_status = '{}' ORDER BY order_id LIMIT 1)"
PICK = {
    "R01": "SELECT s.bag_number FROM orders o JOIN students s USING (student_id) WHERE o.order_status = 'READY' LIMIT 1",
    "R03": f"SELECT {BUSY_STUDENT}",
    "R04": f"SELECT email FROM students WHERE student_id = {BUSY_STUDENT}",
    "R05": "SELECT email FROM staff WHERE staff_id = 2",
    "W01": f"SELECT {FREE_STUDENT}, 9",
    "W02": "SELECT '2501099999', 'Timing Test', 'timing.test@nst.rishihood.edu.in', 'G', 3999",
    "R10": f"SELECT {BUSY_STUDENT}",
    "R11": f"SELECT o.order_id, o.student_id FROM orders o JOIN fines f USING (order_id) WHERE o.student_id = {BUSY_STUDENT} LIMIT 1",
    "R12": f"SELECT {BUSY_STUDENT}",
    "R13": f"SELECT {BUSY_STUDENT}",
    "W10": f"SELECT {FREE_STUDENT}, 9",
    "W11": f"SELECT order_id, student_id FROM orders WHERE order_id = {OPEN_ORDER.format('SUBMITTED')}",
    "W12": f"SELECT order_id, student_id, 12 FROM orders WHERE order_id = {OPEN_ORDER.format('SUBMITTED')}",
    "W20": f"SELECT {OPEN_ORDER.format('SUBMITTED')}, 13, 2, 1",
    "W21": f"SELECT (SELECT o.order_id FROM orders o LEFT JOIN fines f USING (order_id) "
           f"WHERE o.order_status = 'RECEIVED' AND f.order_id IS NULL LIMIT 1), 15",
    "W22": "SELECT (SELECT student_id FROM students WHERE bag_verified_at IS NULL LIMIT 1), 2",
    "R23": f"SELECT {OPEN_ORDER.format('SUBMITTED')}",
    "R34": "SELECT s.bag_number, s.bag_prefix FROM orders o JOIN students s USING (student_id) WHERE o.order_status = 'READY' LIMIT 1",
    "W30": f"SELECT {OPEN_ORDER.format('RECEIVED')}",
    "W31": f"SELECT {OPEN_ORDER.format('READY')}, 2",
    "W32": "SELECT (SELECT order_id FROM fines WHERE fine_status = 'UNPAID' LIMIT 1)",
    "W33": "SELECT (SELECT order_id FROM fines WHERE fine_status = 'UNPAID' LIMIT 1), 1, 'Timing test'",
    "W35": "SELECT '{' || string_agg(order_id::text, ',') || '}' FROM (SELECT order_id FROM orders WHERE order_status = 'RECEIVED' LIMIT 20) x",
    "W34": f"SELECT {OPEN_ORDER.format('READY')}, 2, 'Timing test'",
    "W40": "SELECT 'Timing Test', 'timing.test@example.com', 'COUNTER'",
    "W41": "SELECT 3, false, 1",
    "W42": "SELECT (current_date + 30)::text, 10, 5",
}


def psql(db, sql):
    out = subprocess.run(["psql", "-X", "-q", "-A", "-t", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-d", db, "-c", sql],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip())
    return out.stdout


def read_queries():
    text = (HERE / "04_queries.sql").read_text()
    for block in re.split(r"\n(?=-- [RW]\d\d: )", text)[1:]:
        qid, title = re.match(r"-- ([RW]\d\d): (.*)", block).groups()
        sql = "\n".join(l for l in block.splitlines() if not l.startswith("--")).strip().rstrip(";")
        yield qid, title, sql


def literal(value):
    if value in ("t", "f"):
        return "true" if value == "t" else "false"
    if re.fullmatch(r"-?\d+(\.\d+)?", value):
        return value
    return "'" + value.replace("'", "''") + "'"


def bind(sql, values):
    """Put the picked values in place of $1, $2..., highest number first so $1 does not eat $10."""
    for i in sorted(range(len(values)), reverse=True):
        sql = sql.replace(f"${i + 1}", literal(values[i]))
    return sql


def scan_nodes(plan):
    nodes = re.findall(r"((?:Parallel )?(?:Seq|Index|Index Only|Bitmap Heap|Bitmap Index) Scan(?: using \S+)?(?: on \S+)?)", plan)
    return " | ".join(dict.fromkeys(nodes))


def main(db):
    PLANS.mkdir(exist_ok=True)
    rows = []
    for qid, title, sql in read_queries():
        values = psql(db, PICK[qid]).strip().split("\t") if qid in PICK else []
        query = bind(sql, values)
        times, plans = [], []
        for run in range(1, RUNS + 1):
            explain = f"EXPLAIN (ANALYZE, BUFFERS) {query}"
            if qid.startswith("W"):
                explain = f"BEGIN; {explain}; ROLLBACK"
            plan = psql(db, explain)
            ms = float(re.search(r"Execution Time: ([\d.]+) ms", plan).group(1))
            times.append(ms)
            plans.append(f"=== {qid} run {run} ===\n{plan}")
        (PLANS / f"{qid}.txt").write_text(f"-- {qid}: {title}\n-- parameters: {values}\n\n" + "\n".join(plans))
        rows.append([qid, "WRITE" if qid.startswith("W") else "READ",
                     f"{statistics.mean(times):.3f}", f"{statistics.median(times):.3f}",
                     f"{min(times):.3f}", f"{max(times):.3f}", scan_nodes(plans[-1])])
        print(f"{qid}  avg {statistics.mean(times):8.3f} ms  {title}")
    with open(PLANS / "summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "type", "avg_ms", "median_ms", "min_ms", "max_ms", "scan_nodes"])
        w.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 dbms/time_queries.py <database or connection URL>")
    main(sys.argv[1])
