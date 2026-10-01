from app.modules.matching.routes import _sort_matches_by_score


def test_match_score_sort_orders_highest_score_first_with_recent_tiebreaker():
    matches = [
        {"job_id": "older-high", "overall_score": 92, "posted_days_ago": 8},
        {"job_id": "low", "overall_score": 71, "posted_days_ago": 1},
        {"job_id": "newer-high", "overall_score": 92, "posted_days_ago": 2},
    ]

    assert [match["job_id"] for match in _sort_matches_by_score(matches)] == [
        "newer-high",
        "older-high",
        "low",
    ]
