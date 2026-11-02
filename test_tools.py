import json
from tools import get_client, search_clients, get_client_credits, get_payment_history


def show(title, result):
    print(f"\n--- {title}")
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))


show("get_client(102)", get_client(102))
show("get_client(999)  [unknown]", get_client(999))
show("get_client('abc')  [bad input]", get_client("abc"))
show("search_clients('cur')", search_clients(name="cur"))
show("search_clients(injection attempt)", search_clients(name="'; DROP TABLE Client; --"))
show("get_client_credits(102)", get_client_credits(102))
show("get_payment_history(102)", get_payment_history(102))
show("get_payment_history(101)  [no incidents]", get_payment_history(101))