import datetime
from alo.models import (
    AssessmentQuestion, 
    AssessmentResult, 
    AssessmentDomainScore, 
    AssessmentDifficultyScore, 
    AssessmentMode
)

def get_local_assessment_questions() -> list[AssessmentQuestion]:
    return [
        AssessmentQuestion(id="ALO-AS-001", domain="Python", difficulty="foundation", question="What is PEP 8?", choices=["A database", "A web framework", "A style guide for Python code", "A packaging tool"], correct_choice_index=2, explanation="PEP 8 is the style guide for Python.", weakness_topic="Python basics"),
        AssessmentQuestion(id="ALO-AS-002", domain="Git and GitHub", difficulty="foundation", question="What command is used to stage changes?", choices=["git commit", "git push", "git add", "git clone"], correct_choice_index=2, explanation="git add stages changes.", weakness_topic="Git basics"),
        AssessmentQuestion(id="ALO-AS-003", domain="Testing", difficulty="foundation", question="What is unit testing?", choices=["Testing the entire application", "Testing individual components", "Testing deployment", "Testing user interface manually"], correct_choice_index=1, explanation="Unit testing focuses on individual components.", weakness_topic="Testing concepts"),
        AssessmentQuestion(id="ALO-AS-004", domain="Architecture", difficulty="foundation", question="What does API stand for?", choices=["Application Programming Interface", "Advanced Python Interpreter", "Automated Process Integration", "Application Protocol Interface"], correct_choice_index=0, explanation="API stands for Application Programming Interface.", weakness_topic="Architecture basics"),
        AssessmentQuestion(id="ALO-AS-005", domain="Technical Writing", difficulty="foundation", question="What is the primary purpose of a README file?", choices=["To store secrets", "To provide project overview and instructions", "To list dependencies", "To run tests"], correct_choice_index=1, explanation="A README introduces the project.", weakness_topic="Documentation"),

        AssessmentQuestion(id="ALO-AS-006", domain="Python", difficulty="intermediate", question="What is the purpose of a virtual environment?", choices=["To run Python faster", "To isolate project dependencies", "To compile Python to C", "To write better tests"], correct_choice_index=1, explanation="Virtual environments isolate dependencies.", weakness_topic="Python packaging"),
        AssessmentQuestion(id="ALO-AS-007", domain="Git and GitHub", difficulty="intermediate", question="What does 'git rebase' do?", choices=["Deletes a branch", "Combines branches by moving the base of the current branch", "Uploads changes to a remote server", "Creates a new repository"], correct_choice_index=1, explanation="git rebase rewrites the commit history by moving the base.", weakness_topic="Git branching"),
        AssessmentQuestion(id="ALO-AS-008", domain="Testing", difficulty="intermediate", question="Why do we use mocking in tests?", choices=["To make tests slower", "To isolate code by simulating dependencies", "To test the real database", "To write less code"], correct_choice_index=1, explanation="Mocking simulates dependencies.", weakness_topic="mocking"),
        AssessmentQuestion(id="ALO-AS-009", domain="Architecture", difficulty="intermediate", question="What is a microservice?", choices=["A small Python script", "A small, independent deployable service", "A front-end component", "A database table"], correct_choice_index=1, explanation="Microservices are small, independent services.", weakness_topic="System Architecture"),
        AssessmentQuestion(id="ALO-AS-010", domain="AI-Native Development", difficulty="intermediate", question="What is a 'prompt' in the context of LLMs?", choices=["A command line interface", "The input text given to the model", "A database query", "A Python function"], correct_choice_index=1, explanation="The prompt is the instruction given to the model.", weakness_topic="LLM basics"),
        AssessmentQuestion(id="ALO-AS-011", domain="Product Engineering", difficulty="intermediate", question="What is an MVP?", choices=["Most Valuable Player", "Minimum Viable Product", "Maximum Visual Polish", "Model View Presenter"], correct_choice_index=1, explanation="MVP is Minimum Viable Product.", weakness_topic="product thinking"),
        AssessmentQuestion(id="ALO-AS-012", domain="Python", difficulty="intermediate", question="How do you handle exceptions in Python?", choices=["if/else", "try/except", "switch/case", "for/while"], correct_choice_index=1, explanation="Exceptions are handled using try/except blocks.", weakness_topic="exceptions"),

        AssessmentQuestion(id="ALO-AS-013", domain="Python", difficulty="advanced", question="What is the purpose of asyncio in Python?", choices=["For writing synchronous code", "For concurrent code using the async/await syntax", "For mathematical computations", "For database migrations"], correct_choice_index=1, explanation="asyncio is used for concurrent programming.", weakness_topic="async basics"),
        AssessmentQuestion(id="ALO-AS-014", domain="Architecture", difficulty="advanced", question="What characterizes RESTful API design?", choices=["Stateful interactions", "XML only", "Stateless, client-server, cacheable communications", "Direct database access"], correct_choice_index=2, explanation="REST is stateless and uses standard HTTP methods.", weakness_topic="API boundaries"),
        AssessmentQuestion(id="ALO-AS-015", domain="Testing", difficulty="advanced", question="What is test-driven development (TDD)?", choices=["Writing tests after the code is done", "Writing tests before writing the implementation code", "Testing only the UI", "Testing with real users"], correct_choice_index=1, explanation="TDD involves writing tests first.", weakness_topic="test design"),
        AssessmentQuestion(id="ALO-AS-016", domain="Git and GitHub", difficulty="advanced", question="What is a good practice for pull requests?", choices=["Include massive unrelated changes", "Keep them small, focused, and well-described", "Merge without review", "Use cryptic titles"], correct_choice_index=1, explanation="PRs should be small and focused.", weakness_topic="code review"),
        AssessmentQuestion(id="ALO-AS-017", domain="AI-Native Development", difficulty="advanced", question="What is a technique to get structured JSON outputs from LLMs?", choices=["Just ask nicely", "Using schema enforcement and structured prompting", "LLMs cannot produce JSON", "Writing a Regex parser only"], correct_choice_index=1, explanation="Schema enforcement ensures structured outputs.", weakness_topic="LLM structured outputs"),

        AssessmentQuestion(id="ALO-AS-018", domain="Python", difficulty="expert", question="What is a metaclass in Python?", choices=["A class that inherits from multiple classes", "The class of a class, responsible for class creation", "A decorator", "A generic type"], correct_choice_index=1, explanation="A metaclass defines how a class behaves.", weakness_topic="Advanced Python"),
        AssessmentQuestion(id="ALO-AS-019", domain="Architecture", difficulty="expert", question="What is the CAP theorem?", choices=["Consistency, Availability, Partition tolerance", "Compute, API, Performance", "Cache, Authorization, Policy", "Code, Architecture, Product"], correct_choice_index=0, explanation="CAP theorem states you can only have 2 of 3.", weakness_topic="Distributed Systems"),
        AssessmentQuestion(id="ALO-AS-020", domain="Product Engineering", difficulty="expert", question="How should you handle API keys and secrets?", choices=["Hardcode them in source code", "Store them in environment variables and use secret managers", "Commit them to GitHub", "Print them to logs"], correct_choice_index=1, explanation="Secrets should be managed securely via env vars or managers.", weakness_topic="privacy and secrets"),
    ]

def normalize_answer(raw: str) -> int | None:
    raw = raw.strip().upper()
    mapping = {"A": 0, "B": 1, "C": 2, "D": 3, "1": 0, "2": 1, "3": 2, "4": 3}
    return mapping.get(raw, None)

def get_level_from_score(score: int) -> str:
    if score <= 39:
        return "foundation gaps detected"
    elif score <= 59:
        return "early intermediate"
    elif score <= 74:
        return "intermediate"
    elif score <= 89:
        return "advanced"
    else:
        return "professional calibration"

def score_assessment(mode: AssessmentMode, questions: list[AssessmentQuestion], answers: list[int | None]) -> AssessmentResult:
    total_q = len(questions)
    correct_count = 0
    missed = []
    
    domain_totals = {}
    domain_correct = {}
    diff_totals = {}
    diff_correct = {}
    
    for q, a in zip(questions, answers):
        domain_totals[q.domain] = domain_totals.get(q.domain, 0) + 1
        diff_totals[q.difficulty] = diff_totals.get(q.difficulty, 0) + 1
        
        if a == q.correct_choice_index:
            correct_count += 1
            domain_correct[q.domain] = domain_correct.get(q.domain, 0) + 1
            diff_correct[q.difficulty] = diff_correct.get(q.difficulty, 0) + 1
        else:
            missed.append(q)
            
    score_percent = int((correct_count / total_q) * 100) if total_q > 0 else 0
    level = get_level_from_score(score_percent)
    
    d_scores = []
    for d, total in domain_totals.items():
        corr = domain_correct.get(d, 0)
        perc = int((corr / total) * 100) if total > 0 else 0
        d_scores.append(AssessmentDomainScore(domain=d, score_percent=perc, correct=corr, total=total))
        
    diff_scores = []
    for d, total in diff_totals.items():
        corr = diff_correct.get(d, 0)
        perc = int((corr / total) * 100) if total > 0 else 0
        diff_scores.append(AssessmentDifficultyScore(difficulty=d, score_percent=perc, correct=corr, total=total))
        
    strengths = [ds.domain for ds in d_scores if ds.score_percent >= 75]
    weaknesses = [ds.domain for ds in d_scores if ds.score_percent < 50]
    
    recommendations = ["Use results for Phase 5 learning path recommendations."]
    if score_percent < 50:
        recommendations.append("Focus on foundation concepts in weaker domains.")
        
    return AssessmentResult(
        mode=mode,
        total_questions=total_q,
        correct_answers=correct_count,
        score_percent=score_percent,
        level=level,
        domain_scores=d_scores,
        difficulty_scores=diff_scores,
        missed_questions=missed,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        date=datetime.datetime.now().strftime("%Y-%m-%d")
    )
