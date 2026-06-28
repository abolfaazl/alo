from alo import assessment
from alo.models import AssessmentMode

def test_get_local_assessment_questions():
    questions = assessment.get_local_assessment_questions()
    assert len(questions) == 20
    
    # check IDs are unique
    ids = [q.id for q in questions]
    assert len(set(ids)) == 20
    
    # check difficulty distribution
    diffs = [q.difficulty for q in questions]
    assert diffs.count("foundation") == 5
    assert diffs.count("intermediate") == 7
    assert diffs.count("advanced") == 5
    assert diffs.count("expert") == 3
    
    # Check domain coverage
    domains = set(q.domain for q in questions)
    assert len(domains) == 7

def test_normalize_answer():
    assert assessment.normalize_answer("A") == 0
    assert assessment.normalize_answer(" a ") == 0
    assert assessment.normalize_answer("1") == 0
    assert assessment.normalize_answer("D") == 3
    assert assessment.normalize_answer("4") == 3
    assert assessment.normalize_answer("x") is None
    assert assessment.normalize_answer("") is None

def test_score_assessment():
    questions = assessment.get_local_assessment_questions()
    
    # All correct
    answers = [q.correct_choice_index for q in questions]
    result = assessment.score_assessment(AssessmentMode.local, questions, answers)
    assert result.score_percent == 100
    assert result.level == "professional calibration"
    assert len(result.missed_questions) == 0
    
    # Half correct
    answers_half = [q.correct_choice_index if i % 2 == 0 else None for i, q in enumerate(questions)]
    result_half = assessment.score_assessment(AssessmentMode.local, questions, answers_half)
    assert result_half.score_percent == 50
    assert result_half.level == "early intermediate"
    assert len(result_half.missed_questions) == 10
