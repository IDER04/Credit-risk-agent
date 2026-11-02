from datetime import datetime
from config import T_INCIDENT
from database import DatabaseError, execute, query
import re
from risk_model import MAX_SCORE, explain, get_incident_counts, risk_level, score_from_incidents
def _to_int(value):
    """Return value as an int, or None if it is not a valid integer."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_client(idclt):
    """Profile of one client, or an error dict."""
    idclt = _to_int(idclt)
    if idclt is None:
        return {"error": "idclt must be an integer."}
    rows = query(
        """SELECT IdClt AS idclt, Nom AS nom, Ville AS ville,
                  DateNaiss AS datenaiss, DateEmbauche AS dateembauche,
                  DateOuvertureCmpt AS dateouverturecmpt
           FROM Client WHERE IdClt = %s""",
        (idclt,),
    )
    if not rows:
        return {"error": f"Client {idclt} not found."}
    return rows[0]

def search_clients(name=None, ville=None, limit=10):
    """Clients whose name and/or city contains the given text."""
    sql = "SELECT IdClt AS idclt, Nom AS nom, Ville AS ville FROM Client WHERE 1=1"
    params = []
    if name:
        sql += " AND Nom LIKE %s"
        params.append(f"%{name}%")
    if ville:
        sql += " AND Ville LIKE %s"
        params.append(f"%{ville}%")
    sql += " ORDER BY IdClt LIMIT %s"
    params.append(_to_int(limit) or 10)
    rows = query(sql, tuple(params))
    return {"count": len(rows), "clients": rows}

def get_client_credits(idclt):
    """All credits of a client."""
    client = get_client(idclt)
    if "error" in client:
        return client
    rows = query(
        """SELECT IdCrdt AS idcrdt, DateDemande AS datedemande, TypeCredit AS typecredit,
                  Montant AS montant, DureeMois AS dureemois, Taux AS taux,
                  StatutCrdt AS statutcrdt
           FROM Credit WHERE IdClt = %s ORDER BY IdCrdt""",
        (client["idclt"],),
    )
    return {"idclt": client["idclt"], "nb_credits": len(rows), "credits": rows}


def get_payment_history(idclt):
    """All payment incidents of a client, across all its credits."""
    client = get_client(idclt)
    if "error" in client:
        return client
    rows = query(
        f"""SELECT i.IdIncident AS idincident, i.IdCrdt AS idcrdt,
                   i.DateIncident AS dateincident, i.MontantIncident AS montantincident,
                   i.TypeIncident AS typeincident
            FROM {T_INCIDENT} i
            JOIN Credit c ON c.IdCrdt = i.IdCrdt
            WHERE c.IdClt = %s
            ORDER BY i.DateIncident, i.IdIncident""",
        (client["idclt"],),
    )
    return {"idclt": client["idclt"], "nb_incidents": len(rows), "incidents": rows}
def calculate_client_risk(idclt):
    """Full deterministic risk analysis of one client."""
    client = get_client(idclt)
    if "error" in client:
        return client
    credits = query(
        f"""SELECT c.IdCrdt AS idcrdt, c.TypeCredit AS typecredit, c.Montant AS montant,
                   c.StatutCrdt AS statutcrdt,
                   COUNT(i.IdIncident) AS nb_incidents,
                   COALESCE(SUM(i.MontantIncident), 0) AS total_incident_amount
            FROM Credit c
            LEFT JOIN {T_INCIDENT} i ON i.IdCrdt = c.IdCrdt
            WHERE c.IdClt = %s
            GROUP BY c.IdCrdt, c.TypeCredit, c.Montant, c.StatutCrdt
            ORDER BY c.IdCrdt""",
        (client["idclt"],),
    )
    nb_incidents = sum(c["nb_incidents"] for c in credits)
    score = score_from_incidents(nb_incidents)
    worst = max(credits, key=lambda c: c["nb_incidents"]) if nb_incidents else None
    return {
        "client": {"idclt": client["idclt"], "nom": client["nom"], "ville": client["ville"]},
        "nb_credits": len(credits),
        "nb_incidents": nb_incidents,
        "total_incident_amount": round(sum(float(c["total_incident_amount"]) for c in credits), 2),
        "risk_score": score,
        "max_score": MAX_SCORE,
        "risk_level": risk_level(score),
        "explanation": explain(nb_incidents, len(credits), score, worst),
        "credits": credits,
    }


def get_highest_risk_clients(limit=5):
    """Clients ranked by number of incidents (worst first)."""
    limit = _to_int(limit) or 5
    return {"clients": get_incident_counts()[:limit]}


def get_portfolio_summary():
    """Portfolio-level summary."""
    clients = get_incident_counts()
    totals = query("SELECT COUNT(*) AS nb_credits, COALESCE(SUM(Montant), 0) AS total FROM Credit")[0]
    per_score = {}
    for c in clients:
        per_score[str(c["score"])] = per_score.get(str(c["score"]), 0) + 1
    return {
        "nb_clients": len(clients),
        "nb_credits": totals["nb_credits"],
        "total_credit_amount": float(totals["total"]),
        "total_incidents": sum(c["nb_incidents"] for c in clients),
        "clients_per_score": per_score,
        "top_risk_clients": [c for c in clients if c["nb_incidents"] > 0][:3],
    }
def compare_clients(idclt_a, idclt_b):
    """Risk analysis of two clients side by side."""
    return {
        "client_a": calculate_client_risk(idclt_a),
        "client_b": calculate_client_risk(idclt_b),
    }
class Pending:
    """A database change that is prepared but NOT executed yet."""

    def __init__(self, description, action):
        self.description = description
        self._action = action

    def run(self):
        try:
            return self._action()
        except DatabaseError as e:
            return {"error": str(e)}


def _date(value, name):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"'{name}' must be a real date in YYYY-MM-DD format, got {value!r}.")


CLIENT_COLUMNS = {  # field the model may set -> real column name
    "nom": "Nom",
    "ville": "Ville",
    "datenaiss": "DateNaiss",
    "dateembauche": "DateEmbauche",
    "dateouverturecmpt": "DateOuvertureCmpt",
}
DATE_FIELDS = {"datenaiss", "dateembauche", "dateouverturecmpt"}


def update_client(idclt, nom=None, ville=None, datenaiss=None,
                  dateembauche=None, dateouverturecmpt=None):
    """Prepare an UPDATE of one client. Nothing is written until a human confirms."""
    current = get_client(idclt)
    if "error" in current:
        return current
    given = {"nom": nom, "ville": ville, "datenaiss": datenaiss,
             "dateembauche": dateembauche, "dateouverturecmpt": dateouverturecmpt}
    changes = {}
    for field, value in given.items():
        if value is None or value == "":
            continue
        changes[field] = _date(value, field) if field in DATE_FIELDS else str(value).strip()
    if not changes:
        return {"error": "No field to update was provided."}

    lines = "\n".join(f"  {f}: {current.get(f)} -> {v}" for f, v in changes.items())
    description = f"UPDATE client {current['idclt']} ({current['nom']}):\n{lines}"

    def action():
        sets = ", ".join(f"{CLIENT_COLUMNS[f]} = %s" for f in changes)
        execute(f"UPDATE Client SET {sets} WHERE IdClt = %s",
                (*changes.values(), current["idclt"]))
        return {"status": "updated", "idclt": current["idclt"],
                "changes": {f: str(v) for f, v in changes.items()}}

    return Pending(description, action)
CREDIT_COLUMNS = {
    "idclt": "IdClt",
    "datedemande": "DateDemande",
    "typecredit": "TypeCredit",
    "montant": "Montant",
    "dureemois": "DureeMois",
    "taux": "Taux",
    "statutcrdt": "StatutCrdt",
}
INCIDENT_COLUMNS = {
    "idcrdt": "IdCrdt",
    "dateincident": "DateIncident",
    "montantincident": "MontantIncident",
    "typeincident": "TypeIncident",
}


def _number(value, name, integer=False, allow_zero=False):
    try:
        number = int(value) if integer else float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a {'whole ' if integer else ''}number, got {value!r}.")
    if number < 0 or (number == 0 and not allow_zero):
        raise ValueError(f"'{name}' must be greater than 0, got {value!r}.")
    return number


def _enum(table, column, value):
    """Check a value against the ENUM list stored in MySQL; return the exact stored spelling."""
    rows = query(f"SHOW COLUMNS FROM {table} LIKE %s", (column,))
    if not rows:
        raise ValueError(f"Column {column} not found in {table}.")
    type_text = rows[0]["Type"]
    if isinstance(type_text, (bytes, bytearray)):
        type_text = type_text.decode()
    allowed = re.findall(r"'([^']*)'", type_text)
    for option in allowed:
        if option.lower() == str(value).strip().lower():
            return option
    raise ValueError(f"Invalid {column} {value!r}. Allowed values: {allowed}")


def _next_id(table, column):
    return query(f"SELECT COALESCE(MAX({column}), 0) + 1 AS n FROM {table}")[0]["n"]


def _prepare_insert(table, id_column, columns, data, label):
    lines = "\n".join(f"  {k}: {v}" for k, v in data.items())
    description = f"CREATE a new {label} (id assigned automatically):\n{lines}"

    def action():
        new_id = _next_id(table, id_column)
        names = [id_column] + [columns[k] for k in data]
        placeholders = ", ".join(["%s"] * len(names))
        execute(f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders})",
                (new_id, *data.values()))
        return {"status": "created", "what": label, "id": new_id}

    return Pending(description, action)


def _prepare_update(table, id_column, columns, current, id_field, changes, label):
    if not changes:
        return {"error": "No field to update was provided."}
    lines = "\n".join(f"  {f}: {current.get(f)} -> {v}" for f, v in changes.items())
    description = f"UPDATE {label} {current[id_field]}:\n{lines}"

    def action():
        sets = ", ".join(f"{columns[f]} = %s" for f in changes)
        execute(f"UPDATE {table} SET {sets} WHERE {id_column} = %s",
                (*changes.values(), current[id_field]))
        return {"status": "updated", "what": label, "id": current[id_field],
                "changes": {f: str(v) for f, v in changes.items()}}

    return Pending(description, action)


def _get_credit(idcrdt):
    idcrdt = _to_int(idcrdt)
    if idcrdt is None:
        return {"error": "idcrdt must be an integer."}
    rows = query(
        """SELECT IdCrdt AS idcrdt, IdClt AS idclt, DateDemande AS datedemande,
                  TypeCredit AS typecredit, Montant AS montant, DureeMois AS dureemois,
                  Taux AS taux, StatutCrdt AS statutcrdt
           FROM Credit WHERE IdCrdt = %s""",
        (idcrdt,),
    )
    if not rows:
        return {"error": f"Loan {idcrdt} not found."}
    return rows[0]


def _given(value):
    return value is not None and value != ""


def create_client(nom, ville=None, datenaiss=None, dateembauche=None, dateouverturecmpt=None):
    nom = str(nom or "").strip()
    if not nom:
        raise ValueError("'nom' is required.")
    data = {"nom": nom}
    for field, value in (("ville", ville), ("datenaiss", datenaiss),
                         ("dateembauche", dateembauche), ("dateouverturecmpt", dateouverturecmpt)):
        if _given(value):
            data[field] = _date(value, field) if field in DATE_FIELDS else str(value).strip()
    return _prepare_insert("Client", "IdClt", CLIENT_COLUMNS, data, "client")


def create_credit(idclt, typecredit, montant, dureemois, taux, statutcrdt=None, datedemande=None):
    client = get_client(idclt)
    if "error" in client:
        return client
    typecredit = str(typecredit or "").strip()
    if not typecredit:
        raise ValueError("'typecredit' is required (e.g. Immobilier, Consommation, Auto).")
    data = {
        "idclt": client["idclt"],
        "typecredit": typecredit,
        "montant": _number(montant, "montant"),
        "dureemois": _number(dureemois, "dureemois", integer=True),
        "taux": _number(taux, "taux", allow_zero=True),
    }
    if _given(statutcrdt):
        data["statutcrdt"] = _enum("Credit", "StatutCrdt", statutcrdt)
    if _given(datedemande):
        data["datedemande"] = _date(datedemande, "datedemande")
    return _prepare_insert("Credit", "IdCrdt", CREDIT_COLUMNS, data, "loan")


def update_credit(idcrdt, typecredit=None, montant=None, dureemois=None,
                  taux=None, statutcrdt=None, datedemande=None):
    current = _get_credit(idcrdt)
    if "error" in current:
        return current
    changes = {}
    if _given(typecredit):
        changes["typecredit"] = str(typecredit).strip()
    if _given(montant) and _to_int(montant) != 0:
        changes["montant"] = _number(montant, "montant")
    if _given(dureemois) and _to_int(dureemois) != 0:
        changes["dureemois"] = _number(dureemois, "dureemois", integer=True)
    if _given(taux) and float(taux) != 0:
        changes["taux"] = _number(taux, "taux", allow_zero=True)
    if _given(statutcrdt):
        changes["statutcrdt"] = _enum("Credit", "StatutCrdt", statutcrdt)
    if _given(datedemande):
        changes["datedemande"] = _date(datedemande, "datedemande")
    return _prepare_update("Credit", "IdCrdt", CREDIT_COLUMNS, current, "idcrdt", changes, "loan")


def create_payment_incident(idcrdt, typeincident, montantincident=None, dateincident=None):
    credit = _get_credit(idcrdt)
    if "error" in credit:
        return credit
    data = {
        "idcrdt": credit["idcrdt"],
        "typeincident": _enum(T_INCIDENT, "TypeIncident", typeincident),
    }
    if _given(montantincident):
        data["montantincident"] = _number(montantincident, "montantincident")
    if _given(dateincident):
        data["dateincident"] = _date(dateincident, "dateincident")
    return _prepare_insert(T_INCIDENT, "IdIncident", INCIDENT_COLUMNS, data, "payment incident")


def delete_credit(idcrdt):
    current = _get_credit(idcrdt)
    if "error" in current:
        return current
    n = query(f"SELECT COUNT(*) AS n FROM {T_INCIDENT} WHERE IdCrdt = %s", (current["idcrdt"],))[0]["n"]
    if n:
        return {"error": f"Loan {current['idcrdt']} has {n} payment incident(s). "
                         "Deletion refused to protect the payment history."}
    description = (f"PERMANENTLY DELETE loan {current['idcrdt']} ({current['typecredit']}, "
                   f"amount {current['montant']}, client {current['idclt']}). This cannot be undone.")

    def action():
        execute("DELETE FROM Credit WHERE IdCrdt = %s", (current["idcrdt"],))
        return {"status": "deleted", "what": "loan", "id": current["idcrdt"]}

    return Pending(description, action)
I = {"type": "integer"}
S = {"type": "string"}
N = {"type": "number"}
D = {"type": "string", "description": "date in YYYY-MM-DD format"}

def _spec(func, description, props=None, required=()):
    """Pair a function with its JSON schema for the model."""
    return func, {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {"type": "object", "properties": props or {}, "required": list(required)},
        },
    }


_REGISTRY = [
    _spec(get_client, "Get the profile (name, city, dates) of one client by numeric client id.",
          {"idclt": I}, ["idclt"]),
    _spec(search_clients, "Find clients by part of their name and/or city. Use this when the user gives a name instead of an id.",
          {"name": S, "ville": S, "limit": I}),
    _spec(get_client_credits, "List all loans (type, amount, duration, rate, status) of one client. Use for any question about a client's loans.",
          {"idclt": I}, ["idclt"]),
    _spec(get_payment_history, "List all payment incidents of one client across all its credits.",
          {"idclt": I}, ["idclt"]),
     _spec(calculate_client_risk,
          "Full risk analysis of one client: number of loans, number of payment incidents, risk score out of 20, risk level and explanation. Use for 'analyze client X' or 'why is X risky'.",
          {"idclt": I}, ["idclt"]),
    _spec(get_highest_risk_clients, "Rank clients by number of payment incidents, worst first.",
          {"limit": I}),
    _spec(compare_clients, "Compare the risk of two clients side by side.",
          {"idclt_a": I, "idclt_b": I}, ["idclt_a", "idclt_b"]),
    _spec(get_portfolio_summary, "Portfolio-level summary: totals, score distribution, top risky clients."),
    _spec(update_client, "Prepare a change to a client's profile (name, city, dates). The user is asked to confirm before anything is written. Dates use YYYY-MM-DD.",
          {"idclt": I, "nom": S, "ville": S, "datenaiss": S, "dateembauche": S, "dateouverturecmpt": S},
          ["idclt"]),
    _spec(create_client, "Prepare the creation of a new client. The user is asked to confirm. Dates use YYYY-MM-DD.",
          {"nom": S, "ville": S, "datenaiss": D, "dateembauche": D, "dateouverturecmpt": D}, ["nom"]),
    _spec(create_credit, "Prepare the creation of a new loan for a client. The user is asked to confirm. Duration is in months, the rate (taux) is a percentage.",
          {"idclt": I, "typecredit": S, "montant": N, "dureemois": I, "taux": N, "statutcrdt": S, "datedemande": D},
          ["idclt", "typecredit", "montant", "dureemois", "taux"]),
    _spec(update_credit, "Prepare a change to an existing loan. Pass ONLY the fields the user wants to change; omit all others. The user is asked to confirm.",
          {"idcrdt": I, "typecredit": S, "montant": N, "dureemois": I, "taux": N, "statutcrdt": S, "datedemande": D},
          ["idcrdt"]),
    _spec(create_payment_incident, "Prepare the recording of a payment incident on a loan. The user is asked to confirm.",
          {"idcrdt": I, "typeincident": S, "montantincident": N, "dateincident": D},
          ["idcrdt", "typeincident"]),
    _spec(delete_credit, "Prepare the permanent deletion of a loan that has no payment incident. The user is asked to confirm.",
          {"idcrdt": I}, ["idcrdt"]),
]

TOOLS = {func.__name__: func for func, _ in _REGISTRY}
TOOL_SPECS = [spec for _, spec in _REGISTRY]


def run_tool(name, args):
    """Execute a tool the model asked for. Never raises: errors become dicts."""
    func = TOOLS.get(name)
    if func is None:
        return {"error": f"Unknown tool {name!r}."}
    try:
        return func(**args)
    except TypeError as e:
        return {"error": f"Invalid arguments: {e}"}
    except DatabaseError as e:
        return {"error": str(e)}
    except ValueError as e:
        return {"error": str(e)}