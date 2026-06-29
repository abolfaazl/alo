# ALO (Agentic Learning OS)

ALO is a globally installed CLI tool that allows you to initialize and manage independent learning workspaces for any subject. 

Whether you're learning English grammar, Java Spring Boot, or Product Management, ALO manages your learning state, roadmaps, weaknesses, and assessments dynamically via LLM-driven intelligence.

## Installation

Install globally using `pipx` or `uv` (recommended):

```bash
pipx install D:\ALO
# or
uv tool install D:\ALO
```

### Developer / Local Test Installation

If you are developing ALO, you can install it into a test virtual environment:

```powershell
# In PowerShell:
cd D:\ALO
python -m venv .venv-test
.\.venv-test\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
alo --help
alo doctor
```

## Quickstart

ALO separates the tool from your learning data. You should install ALO once, then create separate folders for each subject you want to learn.

**Important**: Do not run learning workspace `init` inside the ALO source repo.

### 1. Create a Learning Workspace

Create a new folder for your learning project and open it:

```powershell
mkdir D:\learn\English
cd D:\learn\English
alo
```

### 2. Initialize

From inside the interactive dashboard (or CLI), initialize the workspace state files:

*   **Command**: `init` (or `alo init`)

ALO will ask you a few questions about your background, experience level, and goals, and then create the necessary subject-agnostic Markdown state files (like `learning-profile.md` and `skill-map.md`).

### 3. Configure the LLM

To generate domain-specific assessments and roadmaps, you must configure ALO with an LLM provider:

*   **Command**: `config` (or `alo config`)

#### Safe API Key Guidance
*   **Recommended**: `keyring` mode. You will be prompted to paste your API key securely into a masked terminal prompt. It is stored securely in your OS credential manager.
*   **Alternative**: `env` mode. You can export an environment variable in your shell (e.g. `OPENAI_API_KEY`) and tell ALO to read from that variable name.
*   **Never** paste API keys directly into Markdown files.
*   **Never** commit API keys to Git.

**Example for OpenAI-compatible providers:**
```text
Provider: openai-compatible
Base URL: https://api.example.com/v1
Model: gpt-4o-mini
API key storage: keyring
```

### 4. Test LLM Connection

Once configured, verify the connection works:

*   **Command**: `Test LLM Connection` from the settings menu.

### 5. Learning Flow

Continue through the guided flow:

*   `paths` - Generate learning path options based on your profile and assessment.
*   `roadmap` - Generate or update the roadmap for the active path.
*   `learn` - Run a single daily learning session based on the current workspace roadmap.
*   `review` - Review past concepts and update your weaknesses profile.

### 6. Git Sync

ALO safely commits changes to your Markdown state files.

*   `sync --dry-run` - Preview which learning-state files would be committed without changing Git.
*   `sync --no-push` - Commit changes locally without pushing to a remote.
*   `sync` - Commit and push (if auto-push is enabled and a remote is configured).

*(Note: ALO only commits files specified in its internal safe-list. It will never commit unknown files or secrets.)*
