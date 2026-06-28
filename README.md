# ALO (Agentic Learning OS)

ALO is a globally installed CLI tool that allows you to initialize and manage independent learning workspaces for any subject. 

Whether you're learning English grammar, Java Spring Boot, or Product Management, ALO manages your learning state, roadmaps, weaknesses, and assessments dynamically via LLM-driven intelligence.

## Installation

Install globally using `pipx` (recommended):

```bash
pipx install alo
```

Or for development:

```bash
pip install -e .[dev]
```

## Usage

ALO separates the tool from your learning data. You should install ALO once, then create separate folders for each subject you want to learn.

### 1. Initialize a Learning Workspace

Create a new folder for your learning project and run `alo init`:

```bash
mkdir learning-english
cd learning-english
alo init
```

ALO will ask you a few questions about your background, experience level, and goals, and then create the necessary subject-agnostic Markdown state files (like `learning-profile.md` and `skill-map.md`). ALO will also optionally initialize a Git repository to version control your learning progress.

### 2. Configure the LLM

To generate domain-specific assessments and roadmaps, you must configure ALO with an LLM provider:

```bash
alo config
```

### 3. Run an Assessment

Run a domain-specific LLM assessment based on your initialized workspace profile:

```bash
alo assess
```

ALO will read your learning profile and dynamically generate exactly 20 appropriate questions based on your current subject, goal, and knowledge level.

*(Note: ALO source code is never stored in your learning workspaces.)*
