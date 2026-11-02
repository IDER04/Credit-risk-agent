from database import query
from risk_model import score_from_incidents
from tools import run_tool, Pending, create_client

passed = failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS  {label}")
    else:
        failed += 1
        print(f"FAIL  {label}")


# 1. Score boundaries (the business rule)
cases = {0: 0, 1: 5, 2: 5, 3: 10, 5: 10, 6: 20, 50: 20}
for n, expected in cases.items():
    check(f"score({n}) == {expected}", score_from_incidents(n) == expected)

# 2. Unknown tool
r = run_tool("drop_all_tables", {})
check("unknown tool is refused", "error" in r)

# 3. Missing / wrong arguments don't crash
r = run_tool("get_client", {})
check("missing argument returns error", "error" in r)
r = run_tool("get_client", {"idclt": "abc"})
check("non-numeric id returns error", "error" in r)

# 4. Nonexistent client
r = run_tool("get_client", {"idclt": 99999})
check("get_client on missing id returns error", "error" in r)
r = run_tool("calculate_client_risk", {"idclt": 99999})
check("risk on missing id returns error", "error" in r)

# 5. A write tool only PREPARES the change
before = query("SELECT COUNT(*) AS n FROM Client")[0]["n"]
p = create_client("Phase9 Dummy")
after = query("SELECT COUNT(*) AS n FROM Client")[0]["n"]
check("create_client returns a Pending object", isinstance(p, Pending))
check("nothing written before confirmation", before == after)

print(f"\n{passed} passed, {failed} failed")