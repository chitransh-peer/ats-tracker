"""Model output is shaped by applicant-written résumé text, so it is bounded
before it is stored."""

from app.services.ai.evaluation import _clamped_score, _string_list


def test_scores_are_clamped_to_0_100():
    assert _clamped_score(1_000_000) == 100.0
    assert _clamped_score(-5) == 0.0
    assert _clamped_score(72.5) == 72.5


def test_non_numbers_are_not_scores():
    assert _clamped_score("95") is None
    assert _clamped_score(None) is None
    assert _clamped_score(True) is None


def test_string_lists_are_trimmed_to_something_storable():
    assert _string_list("not a list") == []
    assert _string_list(["a", None, " ", 3]) == ["a", "3"]
    assert len(_string_list(["x"] * 100)) == 20
    assert len(_string_list(["y" * 5000])[0]) == 500
