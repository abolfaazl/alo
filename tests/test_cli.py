import pytest
from typer.testing import CliRunner
from alo.cli import app

runner = CliRunner()


def test_init_refuses_source_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "alo").mkdir()
    (tmp_path / "PROJECT_INSTRUCTURE.MD").touch()
    
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 1
    assert "inside the ALO source repository" in result.stdout
    
    # allow-source-repo works
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    result2 = runner.invoke(app, ["init", "--allow-source-repo"], input=inputs)
    assert result2.exit_code == 0

def test_init_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    # Inputs:
    # Subject: English grammar
    # Background: Some words
    # Experience: 2
    # Goal: Fluency
    # Assess now: y
    # Privacy: n
    # Connect remote: n
    inputs = "English grammar\nSome words\n2\nFluency\ny\nn\nn\n"
    
    result = runner.invoke(app, ["init"], input=inputs)
    assert result.exit_code == 0
    assert "Workspace setup complete" in result.stdout
    
    lp = (tmp_path / "learning-profile.md").read_text(encoding="utf-8")
    assert "Subject: English grammar" in lp
    
    sm = (tmp_path / "skill-map.md").read_text(encoding="utf-8")
    assert "Subject Skill Areas" in sm
    
    assert (tmp_path / ".git").exists()

def test_assess_requires_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    # Ensure config missing
    cfg_dir = tmp_path / ".alo"
    monkeypatch.setattr("alo.config.get_config_dir", lambda: cfg_dir)
    
    result = runner.invoke(app, ["assess"])
    assert result.exit_code == 1
    assert "needs LLM configuration" in result.stdout

def test_assess_missing_env_var(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    # Ensure config exists but env var doesn't
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="MY_MISSING_KEY")
    save_config(cfg)
    
    # Remove env var if exists
    monkeypatch.delenv("MY_MISSING_KEY", raising=False)
    
    result = runner.invoke(app, ["assess"])
    assert result.exit_code == 1
    assert "environment variable is missing" in result.stdout

def test_assess_real_openai_mocked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Java Spring Boot\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    # Config and env var
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="TEST_API_KEY")
    save_config(cfg)
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    
    # Mock OpenAI
    class MockMessage:
        @property
        def parsed(self):
            from alo.llm.schemas import AssessmentResponse, GeneratedAssessmentQuestion
            return AssessmentResponse(questions=[
                GeneratedAssessmentQuestion(
                    id=f"Q{i}",
                    domain="Java",
                    difficulty="foundation",
                    question=f"Java Q{i}",
                    choices=["A", "B", "C", "D"],
                    correct_choice_index=0,
                    explanation="Exp",
                    weakness_topic="Topic"
                ) for i in range(20)
            ])
            
    class MockChoice:
        message = MockMessage()
        
    class MockCompletions:
        def parse(self, **kwargs):
            return type('obj', (object,), {'choices': [MockChoice()]})
            
    class MockChat:
        completions = MockCompletions()
        
    class MockBeta:
        chat = MockChat()

    class MockOpenAI:
        def __init__(self, api_key):
            assert api_key == "fake-key"
        beta = MockBeta()
        
    import openai
    monkeypatch.setattr(openai, "OpenAI", MockOpenAI)
    
    assess_inputs = "A\n" * 20
    result = runner.invoke(app, ["assess"], input=assess_inputs)
    
    assert result.exit_code == 0
    assert "Assessment saved successfully" in result.stdout
    assert "Java" in result.stdout

def test_assess_mock(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    # mock assess
    assess_inputs = "A\n" * 20
    result = runner.invoke(app, ["assess", "--mock"], input=assess_inputs)
    assert result.exit_code == 0
    assert "Mock assessment mode" in result.stdout
    assert "Assessment saved successfully" in result.stdout
    
    lp = (tmp_path / "learning-profile.md").read_text(encoding="utf-8")
    assert "Score:" in lp

def test_assess_fallback_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Java Spring Boot\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="TEST_API_KEY", base_url="http://local", llm_provider="openai-compatible")
    save_config(cfg)
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    
    class MockMessage:
        @property
        def content(self):
            import json
            return json.dumps({"questions": [
                {
                    "id": f"Q{i}",
                    "domain": "Java",
                    "difficulty": "foundation",
                    "question": f"Java Q{i}",
                    "choices": ["A", "B", "C", "D"],
                    "correct_choice_index": 0,
                    "explanation": "Exp",
                    "weakness_topic": "Topic"
                } for i in range(20)
            ]})
            
    class MockChoice:
        message = MockMessage()
        
    class MockCompletions:
        def parse(self, **kwargs):
            raise Exception("Parsing not supported")
        def create(self, **kwargs):
            return type('obj', (object,), {'choices': [MockChoice()]})
            
    class MockChat:
        completions = MockCompletions()
        
    class MockBetaChat:
        completions = MockCompletions()

    class MockBeta:
        chat = MockBetaChat()

    class MockOpenAI:
        def __init__(self, api_key, base_url=None):
            assert api_key == "fake-key"
            assert base_url == "http://local"
        beta = MockBeta()
        chat = MockChat()
        
    import openai
    monkeypatch.setattr(openai, "OpenAI", MockOpenAI)
    
    assess_inputs = "A\n" * 20
    result = runner.invoke(app, ["assess"], input=assess_inputs)
    assert result.exit_code == 0
    assert "Java Q0" in result.stdout

def test_assess_invalid_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Java Spring Boot\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="TEST_API_KEY")
    save_config(cfg)
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    
    class MockMessage:
        @property
        def content(self):
            return "not json"
            
    class MockChoice:
        message = MockMessage()
        
    class MockCompletions:
        def parse(self, **kwargs):
            raise Exception("Parsing not supported")
        def create(self, **kwargs):
            return type('obj', (object,), {'choices': [MockChoice()]})
            
    class MockChat:
        completions = MockCompletions()
        
    class MockBetaChat:
        completions = MockCompletions()

    class MockBeta:
        chat = MockBetaChat()

    class MockOpenAI:
        def __init__(self, api_key, base_url=None):
            pass
        beta = MockBeta()
        chat = MockChat()
        
    import openai
    monkeypatch.setattr(openai, "OpenAI", MockOpenAI)
    
    result = runner.invoke(app, ["assess"])
    assert result.exit_code == 1
    assert "Failed to generate valid JSON" in result.stdout

def test_paths_no_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    # Remove config
    from alo.config import get_config_path
    if get_config_path().exists():
        get_config_path().unlink()
        
    result = runner.invoke(app, ["paths"])
    assert result.exit_code == 1
    assert "needs LLM configuration" in result.stdout

def test_paths_missing_env_var(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="MISSING_ENV_VAR")
    save_config(cfg)
    monkeypatch.delenv("MISSING_ENV_VAR", raising=False)
    
    result = runner.invoke(app, ["paths"])
    assert result.exit_code == 1
    assert "environment variable is missing" in result.stdout

def test_paths_mock_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    result = runner.invoke(app, ["paths", "--mock", "--dry-run"], input="skip\n")
    assert result.exit_code == 0
    assert "Mock path recommendation mode is for development/testing only" in result.stdout
    assert "English grammar" in result.stdout
    assert "Skipped path selection" in result.stdout
    
    # Dry run shouldn't write paths to learning-paths.md
    lp_content = (tmp_path / "learning-paths.md").read_text(encoding="utf-8")
    assert "ALO-PATH-001" not in lp_content
    
def test_paths_mock_save_and_skip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    result = runner.invoke(app, ["paths", "--mock"], input="skip\n")
    assert result.exit_code == 0
    
    # Check learning-paths.md
    lp = (tmp_path / "learning-paths.md").read_text(encoding="utf-8")
    assert "ALO-PATH-001" in lp
    assert "Status: proposed" in lp
    assert "Status: selected" not in lp
    
    # Check progress-log.md
    log = (tmp_path / "progress-log.md").read_text(encoding="utf-8")
    assert "Path recommendations generated but none selected." in log

def test_paths_mock_select(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    result = runner.invoke(app, ["paths", "--mock"], input="2\n")
    assert result.exit_code == 0
    
    lp = (tmp_path / "learning-paths.md").read_text(encoding="utf-8")
    assert "Status: selected" in lp
    
    profile = (tmp_path / "learning-profile.md").read_text(encoding="utf-8")
    assert "Active Learning Path" in profile
    assert "ALO-PATH-002" in profile

def test_paths_real_openai_mocked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Java Spring Boot\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="TEST_API_KEY")
    save_config(cfg)
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    
    class MockMessage:
        @property
        def parsed(self):
            from alo.llm.schemas import LearningPathsResponse, LearningPath
            return LearningPathsResponse(paths=[
                LearningPath(
                    id=f"P{i}",
                    title=f"Java Path {i}",
                    summary="Java Summary",
                    who_it_is_for="Me",
                    why_it_matches_user="Because",
                    expected_outcome="Success",
                    core_topics=["Java", "Spring"],
                    estimated_duration="2 weeks",
                    difficulty="intermediate",
                    tradeoffs="None",
                    first_step="Start",
                    avoid_for_now="Kotlin",
                    confidence="medium"
                ) for i in range(3)
            ])
            
    class MockChoice:
        message = MockMessage()
        
    class MockCompletions:
        def parse(self, **kwargs):
            return type('obj', (object,), {'choices': [MockChoice()]})
            
    class MockChat:
        completions = MockCompletions()
        
    class MockBeta:
        chat = MockChat()

    class MockOpenAI:
        def __init__(self, api_key, **kwargs):
            assert api_key == "fake-key"
        beta = MockBeta()
        
    import openai
    monkeypatch.setattr(openai, "OpenAI", MockOpenAI)
    
    result = runner.invoke(app, ["paths"], input="1\n")
    assert result.exit_code == 0
    assert "Java Path 0" in result.stdout
    assert "Path 'Java Path 0' selected!" in result.stdout

def test_roadmap_no_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["roadmap"])
    assert result.exit_code == 1
    assert "Workspace not initialized" in result.stdout

def test_roadmap_no_active_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    result = runner.invoke(app, ["roadmap"])
    assert result.exit_code == 1
    assert "No active learning path selected" in result.stdout

def test_roadmap_no_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    
    from alo.config import get_config_path
    if get_config_path().exists():
        get_config_path().unlink()
        
    result = runner.invoke(app, ["roadmap"])
    assert result.exit_code == 1
    assert "needs LLM configuration" in result.stdout

def test_roadmap_missing_env_var(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="MISSING_ENV_VAR")
    save_config(cfg)
    monkeypatch.delenv("MISSING_ENV_VAR", raising=False)
    
    result = runner.invoke(app, ["roadmap"])
    assert result.exit_code == 1
    assert "environment variable is missing" in result.stdout

def test_roadmap_mock_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    
    result = runner.invoke(app, ["roadmap", "--mock", "--dry-run"])
    assert result.exit_code == 0
    assert "Mock roadmap mode" in result.stdout
    assert "English grammar Item" in result.stdout
    
    # Dry run shouldn't write roadmap
    rm_content = (tmp_path / "roadmap.md").read_text(encoding="utf-8")
    assert "ALO-RM-001" not in rm_content

def test_roadmap_mock_save(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    
    result = runner.invoke(app, ["roadmap", "--mock"])
    assert result.exit_code == 0
    assert "Successfully generated 10 roadmap items" in result.stdout
    
    rm = (tmp_path / "roadmap.md").read_text(encoding="utf-8")
    assert "ALO-RM-001: Mock English grammar Item 1" in rm
    assert "Status: todo" in rm
    
    log = (tmp_path / "progress-log.md").read_text(encoding="utf-8")
    assert "Generated new step-by-step roadmap." in log

def test_roadmap_preserve_status_and_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    # Manually change status
    rm_path = tmp_path / "roadmap.md"
    rm = rm_path.read_text(encoding="utf-8")
    rm = rm.replace("### ALO-RM-001: Mock English grammar Item 1\nStatus: todo", "### ALO-RM-001: Mock English grammar Item 1\nStatus: mastered")
    rm_path.write_text(rm, encoding="utf-8")
    
    # Regenerate without force should fail
    res = runner.invoke(app, ["roadmap", "--mock"])
    assert res.exit_code == 1
    assert "A roadmap already exists" in res.stdout
    
    # Regenerate with force and yes
    res = runner.invoke(app, ["roadmap", "--mock", "--force", "--yes"])
    assert res.exit_code == 0
    
    rm_new = rm_path.read_text(encoding="utf-8")
    assert "### ALO-RM-001: Mock English grammar Item 1\nStatus: mastered" in rm_new
    assert "### ALO-RM-002: Mock English grammar Item 2\nStatus: todo" in rm_new

def test_roadmap_real_openai_mocked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Java Spring Boot\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="TEST_API_KEY")
    save_config(cfg)
    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    
    class MockMessage:
        @property
        def parsed(self):
            from alo.llm.schemas import RoadmapResponse, RoadmapItem
            return RoadmapResponse(items=[
                RoadmapItem(
                    id=f"ALO-RM-{i:03d}",
                    title=f"Java Item {i}",
                    summary="Java Summary",
                    level="intermediate",
                    status="todo",
                    estimated_time="1 hour",
                    prerequisites="None",
                    success_criteria="Done",
                    practice_task="Do it",
                    assessment_method="Test",
                    resources_to_find="Book",
                    depends_on=""
                ) for i in range(1, 9) # 8 items exactly
            ])
            
    class MockChoice:
        message = MockMessage()
        
    class MockCompletions:
        def parse(self, **kwargs):
            return type('obj', (object,), {'choices': [MockChoice()]})
            
    class MockChat:
        completions = MockCompletions()
        
    class MockBeta:
        chat = MockChat()

    class MockOpenAI:
        def __init__(self, api_key, **kwargs):
            assert api_key == "fake-key"
        beta = MockBeta()
        
    import openai
    monkeypatch.setattr(openai, "OpenAI", MockOpenAI)
    
    result = runner.invoke(app, ["roadmap"])
    assert result.exit_code == 0
    assert "Java Item 1" in result.stdout
    assert "Successfully generated 8 roadmap items" in result.stdout

def test_learn_no_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["learn"])
    assert result.exit_code == 1
    assert "Workspace not initialized" in result.stdout

def test_learn_no_roadmap(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "Subject\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    result = runner.invoke(app, ["learn"])
    assert result.exit_code == 1
    assert "No learnable roadmap item found" in result.stdout

def test_learn_priority(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    # Change status of RM-003 to needs_review and RM-005 to in_progress
    rm_path = tmp_path / "roadmap.md"
    rm = rm_path.read_text(encoding="utf-8")
    rm = rm.replace("### ALO-RM-003: Mock English Item 3\nStatus: todo", "### ALO-RM-003: Mock English Item 3\nStatus: needs_review")
    rm = rm.replace("### ALO-RM-005: Mock English Item 5\nStatus: todo", "### ALO-RM-005: Mock English Item 5\nStatus: in_progress")
    rm_path.write_text(rm, encoding="utf-8")
    
    result = runner.invoke(app, ["learn", "--mock", "--dry-run"], input="answer\n")
    assert result.exit_code == 0
    assert "(ALO-RM-005)" in result.stdout

def test_learn_explicit_item(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    result = runner.invoke(app, ["learn", "--mock", "--dry-run", "--item", "ALO-RM-002"], input="answer\n")
    assert result.exit_code == 0
    assert "(ALO-RM-002)" in result.stdout

def test_learn_no_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    from alo.config import get_config_path
    if get_config_path().exists():
        get_config_path().unlink()
        
    result = runner.invoke(app, ["learn"])
    assert result.exit_code == 1
    assert "needs LLM configuration" in result.stdout

def test_learn_missing_env_var(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="MISSING_ENV_VAR")
    save_config(cfg)
    monkeypatch.delenv("MISSING_ENV_VAR", raising=False)
    
    result = runner.invoke(app, ["learn"])
    assert result.exit_code == 1
    assert "environment variable is missing" in result.stdout

def test_learn_mock_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    result = runner.invoke(app, ["learn", "--mock", "--dry-run"], input="pass answer\n")
    assert result.exit_code == 0
    assert "State not updated (dry run)" in result.stdout
    assert "Result: PASS" in result.stdout
    
    rm = (tmp_path / "roadmap.md").read_text(encoding="utf-8")
    assert "### ALO-RM-001: Mock English grammar Item 1\nStatus: todo" in rm

def test_learn_mock_pass(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    result = runner.invoke(app, ["learn", "--mock"], input="pass answer\n")
    assert result.exit_code == 0
    assert "State updated successfully" in result.stdout
    
    rm = (tmp_path / "roadmap.md").read_text(encoding="utf-8")
    assert "### ALO-RM-001: Mock English Item 1\nStatus: passed_once" in rm
    
    log = (tmp_path / "progress-log.md").read_text(encoding="utf-8")
    assert "Outcome: pass" in log

def test_learn_mock_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    result = runner.invoke(app, ["learn", "--mock"], input="fail answer\n")
    assert result.exit_code == 0
    
    rm = (tmp_path / "roadmap.md").read_text(encoding="utf-8")
    assert "### ALO-RM-001: Mock English Item 1\nStatus: needs_review" in rm
    
    wk = (tmp_path / "weaknesses.md").read_text(encoding="utf-8")
    assert "ALO-WK-ALO-RM-001-01" in wk
    assert "Mock weakness topic" in wk

def test_learn_cancel_on_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    runner.invoke(app, ["paths", "--mock"], input="1\n")
    runner.invoke(app, ["roadmap", "--mock"])
    
    result = runner.invoke(app, ["learn", "--mock"], input="\n\n")
    assert result.exit_code == 0
    assert "Session cancelled" in result.stdout

def test_dashboard_no_args_alo_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "alo").mkdir()
    (tmp_path / "PROJECT_INSTRUCTURE.MD").touch()
    (tmp_path / "pyproject.toml").touch()
    
    result = runner.invoke(app, ["--no-interactive"])
    assert result.exit_code == 0
    assert "Development Repository Detected" in result.stdout

def test_dashboard_no_args_uninitialized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--no-interactive"])
    assert result.exit_code == 0
    assert "No ALO workspace detected" in result.stdout
    assert not (tmp_path / "learning-profile.md").exists()

def test_dashboard_home_uninitialized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["home", "--no-interactive"])
    assert result.exit_code == 0
    assert "No ALO workspace detected" in result.stdout
    assert not (tmp_path / "learning-profile.md").exists()

def test_dashboard_initialized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    result = runner.invoke(app, ["home", "--no-interactive"])
    assert result.exit_code == 0
    assert "Subject" in result.stdout
    assert "English" in result.stdout
    assert "Suggested next command:" in result.stdout
    assert "alo paths" in result.stdout

def test_dashboard_no_secrets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    inputs = "English\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(app, ["init"], input=inputs)
    
    from alo.config import AloConfig, save_config
    cfg = AloConfig(api_key_env_var="MY_SECRET_KEY")
    save_config(cfg)
    monkeypatch.setenv("MY_SECRET_KEY", "sk-12345secret")
    
    result = runner.invoke(app, ["home", "--no-interactive"])
    assert result.exit_code == 0
    assert "sk-12345secret" not in result.stdout

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "home" in result.stdout
    assert "init" in result.stdout
    assert "learn" in result.stdout

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_dashboard_interactive_commands(tmp_path):
    from alo.ui.dashboard import AloApp
    from textual.widgets import Input
    
    # Initialize workspace
    import os
    from alo.cli import app as cli_app
    from typer.testing import CliRunner
    runner = CliRunner()
    
    # Needs a real initialized directory
    cwd = os.getcwd()
    os.chdir(tmp_path)
    inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
    runner.invoke(cli_app, ["init"], input=inputs)
    
    app = AloApp(is_workspace=True, workspace_info={"cwd": str(tmp_path), "subject": "English grammar"})
    
    async with app.run_test() as pilot:
        for _ in range(10):
            if app.query("#logo"):
                break
            await pilot.pause(0.1)
        assert app.query_one("#logo")
        
        inp = app.query_one("#chat-input", Input)
        
        # test / command
        inp.value = "/"
        await pilot.press("enter")
        assert app.is_running
        
        # test /status command
        inp.value = "/status"
        await pilot.press("enter")
        assert app.is_running
        
        # test paths --mock (requires selection)
        inp.value = "paths --mock"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "paths_selecting"
        
        # select path
        inp.value = "1"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "idle"
        
        # test roadmap --mock --force --yes
        inp.value = "roadmap --mock --force --yes"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "idle"
        
        # test learn --mock
        inp.value = "learn --mock"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "learn_answering"
        
        # answer learn
        inp.value = "This is my answer."
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "idle"
        
        # test assess --mock --dry-run
        inp.value = "assess --mock --dry-run"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "assess_answering"
        
        # answer all questions (mock has 20 questions typically, wait this will block if we don't loop)
        # to prevent infinite loops, answer 1
        inp.value = "A"
        await pilot.press("enter")
        await pilot.pause(0.1)
        # Note: assess --mock might require 20 inputs, which is tedious here. We just ensure it transitioned to answering.
        
        # To avoid blocking the test with 20 questions, let's force the state back to idle
        app.screen.app_state = "idle"
        
        # test typo
        inp.value = "asess"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.is_running
        
        # test command normalization
        inp.value = "alo paths --mock"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "paths_selecting"
        
        # select path 1 again to clear state
        inp.value = "1"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.screen.app_state == "idle"
        
        # review Phase 8 placeholder
        inp.value = "review"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.is_running
        
        # test quit
        inp.value = "quit"
        await pilot.press("enter")
        
    os.chdir(cwd)

