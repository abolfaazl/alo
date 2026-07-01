from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from alo.cli import app
from alo.config import load_config

runner = CliRunner()

class MockSession:
    def __init__(self):
        self.topic = "T1"
        self.short_lesson = "L1"
        self.example = "E1"
        self.common_mistake = "M1"
        self.practice_question = "1. Q1"

class MockCtx:
    def __init__(self):
        self.target_id = "ALO-RM-001"
        self.session = MockSession()

class MockEvaluation:
    def __init__(self):
        self.result = "pass"
        self.score = 100
        self.strengths = ["good"]
        self.weaknesses = ["none"]
        self.recommended_next_step = "Next"
        self.feedback = "Good job"

def test_obsidian_disabled_learn_flow_untouched(tmp_path):
    # Just checking if `alo learn` works when Obsidian is disabled and does not crash.
    # We mock generate_session and evaluate_answer to avoid LLM calls.
    with patch("alo.services.learn_service.generate_session") as mock_gen, \
         patch("alo.services.learn_service.evaluate_answer") as mock_eval:
         
        mock_gen.return_value = MagicMock(success=True, warning=None, context=MockCtx())
        mock_eval.return_value = MagicMock(success=True, evaluation=MockEvaluation())
        
        result = runner.invoke(app, ["learn"], input="My answer\n")
        
        assert result.exit_code == 0
        assert "L1" in result.stdout
        assert "Next" in result.stdout

def test_obsidian_setup_and_learn_flow(tmp_path):
    vault = tmp_path / "mock_vault"
    vault.mkdir()
    
    # 1. Setup Obsidian
    with patch("alo.services.obsidian_service.update_dashboard"):
        result = runner.invoke(app, ["obsidian", "setup", "--vault", str(vault), "--no-auto-open"])
        assert result.exit_code == 0
        assert "Obsidian integration configured!" in result.stdout
    
    # Check config
    cfg = load_config()
    assert cfg.obsidian.enabled
    assert cfg.obsidian.vault_path == str(vault)
    assert not cfg.obsidian.auto_open_lesson
    
    # 2. Run learn flow
    with patch("alo.services.learn_service.generate_session") as mock_gen, \
         patch("alo.services.learn_service.evaluate_answer") as mock_eval, \
         patch("alo.services.obsidian_service.auto_open_file") as mock_auto_open:
         
        mock_gen.return_value = MagicMock(success=True, warning=None, context=MockCtx())
        mock_eval.return_value = MagicMock(success=True, evaluation=MockEvaluation())
        
        result2 = runner.invoke(app, ["learn", "--mock"], input="My answer\n")
        assert result2.exit_code == 0
        
        # Check files were written
        alo_folder = vault / "ALO"
        lesson_file = alo_folder / "Courses" / "Learning Path" / "ALO-RM-001 - T1.md"
        
        assert lesson_file.exists()
        content = lesson_file.read_text(encoding="utf-8")
        assert "L1" in content
        assert "Score: 100" in content
        
        log_file = alo_folder / "Practice Log.md"
        assert log_file.exists()
        
        # Auto open shouldn't be called because --no-auto-open was passed
        mock_auto_open.assert_not_called()
