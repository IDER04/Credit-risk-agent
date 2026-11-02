import json
from tools import calculate_client_risk, get_highest_risk_clients, get_portfolio_summary


def show(title, result):
    print(f"\n--- {title}")
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))


show("calculate_client_risk(102)", calculate_client_risk(102))
show("calculate_client_risk(101)  [no incidents]", calculate_client_risk(101))
show("calculate_client_risk(999)  [unknown]", calculate_client_risk(999))
show("get_highest_risk_clients(3)", get_highest_risk_clients(3))
show("get_portfolio_summary()", get_portfolio_summary())