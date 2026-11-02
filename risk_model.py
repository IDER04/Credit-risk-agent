import mysql.connector
from config import T_INCIDENT
from database import DatabaseError, get_connection, query


def score_from_incidents(nb_incidents):
    """Methodology: 0 -> 0 | 1-2 -> 5 | 3-5 -> 10 | 6+ -> 20."""
    if nb_incidents == 0:
        return 0
    if nb_incidents <= 2:
        return 5
    if nb_incidents <= 5:
        return 10
    return 20


def get_incident_counts():
    """One dict per client: idclt, nom, nb_incidents, score (worst first)."""
    sql = f"""
        SELECT c.IdClt AS idclt,
               c.Nom AS nom,
               COUNT(i.IdIncident) AS nb_incidents
        FROM Client c
        LEFT JOIN Credit cr ON cr.IdClt = c.IdClt
        LEFT JOIN {T_INCIDENT} i ON i.IdCrdt = cr.IdCrdt
        GROUP BY c.IdClt, c.Nom
        ORDER BY nb_incidents DESC, c.IdClt
    """
    rows = query(sql)
    for row in rows:
        row["score"] = score_from_incidents(row["nb_incidents"])
    return rows


def refresh_risque_table():
    """Rebuild the Risque table. Returns the number of rows written."""
    rows = get_incident_counts()
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Risque (
                    IdRisque INT PRIMARY KEY AUTO_INCREMENT,
                    IdClt INT,
                    Nom VARCHAR(100),
                    ScoreRisque INT
                )
            """)
            cur.execute("DELETE FROM Risque")
            cur.executemany(
                "INSERT INTO Risque (IdClt, Nom, ScoreRisque) VALUES (%s, %s, %s)",
                [(r["idclt"], r["nom"], r["score"]) for r in rows],
            )
            conn.commit()
            return len(rows)
        except mysql.connector.Error as e:
            conn.rollback()
            raise DatabaseError(f"SQL error: {e}") from e
        finally:
            cur.close()
MAX_SCORE = 20


def risk_level(score):
    return {0: "none", 5: "low", 10: "moderate", 20: "high"}[score]


def explain(nb_incidents, nb_credits, score, worst_credit=None):
    """Plain-language explanation of a score, built from the rule (no LLM)."""
    if nb_incidents == 0:
        return (f"No payment incident on {nb_credits} loan(s): "
                f"score 0/{MAX_SCORE} (rule: 0 incidents -> 0).")
    rule = {5: "1-2 incidents -> 5", 10: "3-5 incidents -> 10", 20: "6 or more incidents -> 20"}[score]
    text = (f"{nb_incidents} payment incident(s) across {nb_credits} loan(s): "
            f"score {score}/{MAX_SCORE} (rule: {rule}).")
    if worst_credit:
        text += (f" Most incidents are on loan {worst_credit['idcrdt']} "
                 f"({worst_credit['typecredit']}): {worst_credit['nb_incidents']}.")
    return text