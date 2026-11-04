"""Pure unit tests of the scoring rule. No database needed."""
import pytest

from risk_model import MAX_SCORE, explain, risk_level, score_from_incidents


@pytest.mark.parametrize("incidents, expected", [
    (0, 0), (1, 5), (2, 5), (3, 10), (5, 10), (6, 20), (50, 20),
])
def test_score_thresholds(incidents, expected):
    assert score_from_incidents(incidents) == expected


@pytest.mark.parametrize("score, level", [
    (0, "none"), (5, "low"), (10, "moderate"), (20, "high"),
])
def test_risk_level(score, level):
    assert risk_level(score) == level


def test_explain_without_incidents():
    text = explain(0, 2, 0)
    assert f"score 0/{MAX_SCORE}" in text
    assert "No payment incident" in text


def test_explain_mentions_worst_loan():
    worst = {"idcrdt": 1005, "typecredit": "Auto", "nb_incidents": 3}
    text = explain(6, 2, 20, worst)
    assert "score 20/20" in text
    assert "loan 1005" in text
