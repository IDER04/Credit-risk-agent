"""Prints raw tool output against the real database. Run: python tests/manual/tools_smoke.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import (calculate_client_risk, get_client, get_client_credits,
                   get_highest_risk_clients, get_payment_history,
                   get_portfolio_summary, search_clients)


def show(title, result):
    print(f"\n--- {title}")
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))


show("get_client(102)", get_client(102))
show("get_client(999)  [unknown]", get_client(999))
show("search_clients('cur')", search_clients(name="cur"))
show("get_client_credits(102)", get_client_credits(102))
show("get_payment_history(102)", get_payment_history(102))
show("calculate_client_risk(102)", calculate_client_risk(102))
show("calculate_client_risk(101)  [no incidents]", calculate_client_risk(101))
show("get_highest_risk_clients(3)", get_highest_risk_clients(3))
show("get_portfolio_summary()", get_portfolio_summary())
