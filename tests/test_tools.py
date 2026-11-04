"""Tool safety tests.

Tests without the `db` fixture run anywhere. Tests with it are skipped when MySQL is
unreachable and expect the fictional sample data from schema.sql.
"""
import pytest

from database import DatabaseError, query
from tools import Pending, create_client, run_tool


@pytest.fixture
def db():
    try:
        query("SELECT 1 AS ok")
    except DatabaseError as e:
        pytest.skip(f"MySQL not available: {e}")


# ---- no database needed -------------------------------------------------

def test_unknown_tool_is_refused():
    assert "error" in run_tool("drop_all_tables", {})


def test_missing_argument_returns_error():
    assert "error" in run_tool("get_client", {})


def test_non_numeric_id_returns_error():
    assert "error" in run_tool("get_client", {"idclt": "abc"})


def test_invalid_date_returns_error():
    result = run_tool("create_client", {"nom": "X", "datenaiss": "31/12/2000"})
    assert "error" in result


def test_empty_name_returns_error():
    assert "error" in run_tool("create_client", {"nom": "   "})


# ---- database needed ----------------------------------------------------

def test_unknown_client_returns_error(db):
    assert "error" in run_tool("get_client", {"idclt": 99999})
    assert "error" in run_tool("calculate_client_risk", {"idclt": 99999})


def test_sql_injection_attempt_is_harmless(db):
    result = run_tool("search_clients", {"name": "'; DROP TABLE Client; --"})
    assert result["count"] == 0
    assert query("SELECT COUNT(*) AS n FROM Client")[0]["n"] > 0


def test_create_client_only_prepares_the_change(db):
    before = query("SELECT COUNT(*) AS n FROM Client")[0]["n"]
    pending = create_client("Test Dummy")
    after = query("SELECT COUNT(*) AS n FROM Client")[0]["n"]
    assert isinstance(pending, Pending)
    assert before == after


def test_risk_levels_on_sample_data(db):
    assert run_tool("calculate_client_risk", {"idclt": 101})["risk_score"] == 0
    assert run_tool("calculate_client_risk", {"idclt": 102})["risk_score"] == 10
    assert run_tool("calculate_client_risk", {"idclt": 104})["risk_score"] == 20


def test_loan_with_incidents_cannot_be_deleted(db):
    result = run_tool("delete_credit", {"idcrdt": 1002})
    assert "error" in result
    assert not isinstance(result, Pending)
