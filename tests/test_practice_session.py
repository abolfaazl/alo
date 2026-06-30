from alo.services.practice_session_service import PracticeItemResult, summarize_practice_results

def test_summarize_practice_results_correct_counts():
    results = [
        PracticeItemResult(index=1, result="pass", score=100),
        PracticeItemResult(index=2, result="partial", score=60),
        PracticeItemResult(index=3, result="fail", score=20),
        PracticeItemResult(index=4, result="partial", score=80),
    ]
    
    summary = summarize_practice_results(results)
    assert summary.total_items == 4
    assert summary.passed == 1
    assert summary.partial == 2
    assert summary.failed == 1
    assert summary.average_score == 65  # (100+60+20+80) / 4 = 260 / 4 = 65
    assert not summary.warnings

def test_summarize_practice_results_empty():
    summary = summarize_practice_results([])
    assert summary.total_items == 0
    assert summary.passed == 0
    assert summary.partial == 0
    assert summary.failed == 0
    assert summary.average_score == 0

def test_summarize_practice_results_unknown_result():
    results = [
        PracticeItemResult(index=1, result="unknown", score=50)
    ]
    summary = summarize_practice_results(results)
    assert summary.total_items == 1
    assert summary.passed == 0
    assert summary.partial == 0
    assert summary.failed == 1
    assert summary.average_score == 50
    assert len(summary.warnings) == 1
    assert "counted as fail" in summary.warnings[0]
