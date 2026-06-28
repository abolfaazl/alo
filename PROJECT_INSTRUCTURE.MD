# ALO — Agentic Learning OS Development Prompt

## Role

You are acting as a Senior Python Engineer, AI Architect, Product Engineer, and CLI Tooling Specialist.

Your task is to build a production-quality, CLI-based personal learning operating system named **ALO**.

ALO stands for **Agentic Learning OS**.

Do not build the whole system in one pass. This project must be developed incrementally, phase by phase, with clear audits, implementation plans, acceptance criteria, tests, and verification after each phase.

## Product Goal

ALO is a Git-backed personal learning system.

The user starts the CLI, describes what they already know, optionally takes an AI-generated assessment, chooses or receives recommended learning paths, and then receives a structured roadmap.

After onboarding, the system can run daily learning sessions. Each session teaches a small concept, evaluates the user's understanding, updates the user's skills, weaknesses, roadmap, and learning log, then safely syncs the state to Git.

ALO must behave like a serious professional tutor, not a generic beginner course generator.

## Core User Flow

The intended user flow is:

1. User runs:

```bash
alo init
```

2. ALO asks the user what they already know.

3. ALO asks whether the user wants to take an optional assessment.

4. If the user agrees, ALO generates a 20-question multiple-choice assessment.

5. The assessment should be adaptive to the user's declared skills and target area.

6. ALO scores the assessment by domain and difficulty.

7. ALO generates or updates the user's learning profile, skill map, weaknesses, and roadmap.

8. ALO then asks whether:

   * the system should recommend learning paths, or
   * the user already knows what they want to learn.

9. If the user wants recommendations, ALO suggests 3 professional learning paths based on current skills, gaps, and goals.

10. If the user chooses a path, ALO generates a roadmap.

11. On later runs, the user can run:

```bash
alo learn
```

12. ALO chooses the next best learning session based on:

* roadmap status,
* weaknesses,
* previous failures,
* recently learned topics,
* user goal,
* skill gaps.

13. ALO teaches a short lesson, asks a practical question, evaluates the answer, updates the state, logs the session, and optionally syncs to Git.

## Non-Negotiable Design Principles

### 1. Incremental Development

Do not attempt to implement all features at once.

Every implementation step must follow this output format:

```text
Audit:
- What exists now?
- What did you inspect?

Plan:
- What will be changed?
- What will not be changed?

Changed Files:
- List every changed file.

Verification:
- Commands run.
- Test results.
- Manual checks.

Risks:
- Known limitations.
- Follow-up work.

Next Step:
- The next logical phase.
```

### 2. Safety Around Secrets

Never store LLM API keys inside the Git repository.

Do not write API keys to tracked files.

Local secrets and local machine configuration must live outside the learning repository, for example:

```text
~/.alo/config.json
```

or environment variables.

The learning repository may contain only a safe example file:

```text
alo_config.example.json
```

The project must include `.gitignore` rules that prevent local secrets from being committed.

### 3. Git Safety

ALO must not blindly run destructive Git operations.

Before `git pull`, `commit`, or `push`, ALO must check:

* Is the repository initialized?
* Is the working tree dirty?
* Are there uncommitted user changes?
* Is there a remote configured?
* Did a conflict occur?
* Did push fail?

If there are uncommitted manual changes, ALO must not overwrite them silently.

ALO must support a safe mode where it updates files locally but does not push.

### 4. Markdown as User-Facing State

The learning repository is primarily human-readable.

The main state files should be Markdown files.

ALO should maintain these files:

```text
README.md
learning-profile.md
skill-map.md
roadmap.md
progress-log.md
weaknesses.md
tutor-rules.md
privacy-rules.md
```

Optional machine-readable files may exist under:

```text
.alo/
```

But secrets must never be stored there if `.alo/` is inside the repository.

### 5. Existing Repository Compatibility

If the repository already contains learning files, ALO must read and preserve them.

Do not overwrite existing Markdown files without creating a backup or showing a migration plan.

If files are missing, create them.

If files exist, update them carefully.

### 6. Professional-Level Learning

ALO must not assume the user is a beginner.

The onboarding flow should detect level.

The system should be able to support users with professional programming experience.

Assessment and roadmap generation should include topics such as:

* Python engineering maturity
* Git and GitHub workflow
* testing discipline
* debugging
* software architecture
* code review
* API design
* CLI design
* AI-native development workflows
* LLM application architecture
* prompt engineering
* structured outputs
* security and privacy
* technical writing
* product-engineering thinking

### 7. Privacy

ALO must not store private company, client, repository, or product details unless the user explicitly enters them and approves storing them.

The system should prefer general professional learning language.

Avoid leaking private project names into generated learning files.

The `privacy-rules.md` file must clearly explain what ALO can and cannot store.

## Recommended CLI Commands

Implement the CLI using `typer`.

Required commands over the project lifecycle:

```bash
alo init
alo status
alo assess
alo paths
alo roadmap
alo learn
alo review
alo sync
alo doctor
```

### Command Responsibilities

#### `alo init`

Initializes ALO in a learning repository.

Responsibilities:

* detect existing repo or initialize one,
* create missing state files,
* set up safe local config outside repo,
* ask the user about existing skills,
* ask whether to run assessment,
* generate initial learning profile,
* generate initial skill map,
* generate initial roadmap or path options,
* optionally commit safe files.

#### `alo status`

Shows current learning state:

* active goal,
* current roadmap item,
* skill levels,
* active weaknesses,
* last session,
* Git sync status.

#### `alo assess`

Runs a standalone assessment.

Assessment modes:

```text
self-report
multiple-choice
mixed
```

The default multiple-choice assessment should contain 20 questions.

The assessment should classify results by:

```text
domain
difficulty
confidence
score
recommended next action
```

#### `alo paths`

Suggests 3 learning paths based on current profile.

Each path must include:

```text
title
who it is for
why it matches the user
expected outcome
core topics
estimated duration
tradeoffs
```

#### `alo roadmap`

Generates or updates the roadmap for a selected path or user-defined goal.

The roadmap must be chunked into small learning units.

Each unit should include:

```text
id
title
level
prerequisites
status
estimated time
success criteria
practice task
```

#### `alo learn`

Runs one learning session.

Session flow:

1. Pull or check Git state safely.
2. Read all state files.
3. Planner chooses the next topic.
4. Teacher gives a short lesson.
5. Evaluator asks a question or coding task.
6. User answers.
7. Evaluator grades the answer.
8. State manager updates Markdown files.
9. Session is appended to `progress-log.md`.
10. Weaknesses are updated if needed.
11. Git commit and push happen only if safe and enabled.

#### `alo review`

Focuses only on weaknesses and previously failed topics.

#### `alo sync`

Safely commits and pushes learning state.

#### `alo doctor`

Checks environment health:

* Python version,
* required packages,
* Git availability,
* repo status,
* local config,
* LLM provider configuration,
* Markdown state validity.

## Technical Stack

Use:

```text
Python 3.10+
typer
rich
pydantic
GitPython
openai or anthropic provider abstraction
instructor for structured LLM outputs, if appropriate
pytest
ruff
```

Avoid LangChain in the initial version unless there is a clear need. The first version should be simple, inspectable, and reliable.

## Proposed Project Structure

Use this structure:

```text
alo/
  __init__.py
  cli.py
  config.py
  git_manager.py
  state_manager.py
  markdown_store.py
  models.py
  assessment.py
  roadmap.py
  session.py
  llm/
    __init__.py
    client.py
    prompts.py
    schemas.py
  agents/
    __init__.py
    assessor.py
    planner.py
    teacher.py
    evaluator.py
  ui/
    __init__.py
    console.py
tests/
  test_config.py
  test_state_manager.py
  test_markdown_store.py
  test_assessment.py
  test_roadmap.py
  test_git_manager.py
pyproject.toml
README.md
```

## Structured Output Requirements

All LLM calls that modify state must use structured outputs.

Use Pydantic models for:

```text
SkillProfile
SkillItem
AssessmentQuestion
AssessmentResult
LearningPath
Roadmap
RoadmapItem
LearningSessionPlan
EvaluationResult
StateUpdate
```

Example model concepts:

```python
class AssessmentQuestion(BaseModel):
    id: str
    domain: str
    difficulty: Literal["foundation", "intermediate", "advanced", "expert"]
    question: str
    choices: list[str]
    correct_choice_index: int
    explanation: str

class EvaluationResult(BaseModel):
    result: Literal["pass", "partial", "fail"]
    score: int
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    recommended_state_updates: list[str]
```

## Markdown State Rules

Markdown files must be predictable enough to update safely.

Do not generate random Markdown structures every time.

Use stable headings.

### `learning-profile.md`

Should include:

```markdown
# Learning Profile

## Current Level Summary

## Declared Skills

## Assessment Summary

## Goals

## Preferred Learning Style

## Constraints

## Last Updated
```

### `skill-map.md`

Should include:

```markdown
# Skill Map

## Python

## Git and GitHub

## Testing

## Architecture

## AI-Native Development

## Product Engineering

## Technical Writing
```

Each skill should have:

```text
level: 1-5
confidence: low/medium/high
evidence
last_practiced
status
```

### `roadmap.md`

Should include:

```markdown
# Roadmap

## Active Path

## Roadmap Items

### ALO-RM-001: Topic Title
Status: todo
Level: intermediate
Estimated Time: 30 minutes
Prerequisites:
Success Criteria:
Practice Task:
```

Statuses:

```text
todo
in_progress
practiced
passed_once
mastered
needs_review
skipped
```

### `weaknesses.md`

Should include:

```markdown
# Weaknesses

## Active Weaknesses

### Weakness ID
Topic:
Source:
Observed On:
Severity:
Evidence:
Recommended Practice:
Status:
```

### `progress-log.md`

Should include append-only daily entries:

```markdown
# Progress Log

## YYYY-MM-DD

### Session: Topic
Outcome:
Score:
What was learned:
Mistakes:
Next recommendation:
```

## Assessment Design

The optional 20-question assessment is central to ALO.

It must support:

```text
professional calibration
domain scoring
difficulty scoring
weakness detection
roadmap generation
```

The flow:

1. Ask the user for declared skills.
2. Ask target area, or infer from skills.
3. Generate 20 multiple-choice questions.
4. Questions must span multiple levels.
5. User answers in CLI.
6. Score the result.
7. Build a skill profile.
8. Save assessment summary to `learning-profile.md`.
9. Add detected gaps to `weaknesses.md`.
10. Use the result to suggest paths or generate a roadmap.

Question distribution should be approximately:

```text
5 foundation questions
7 intermediate questions
5 advanced questions
3 expert-calibration questions
```

Do not make the assessment feel like a school exam. It should feel like a professional calibration interview.

## Learning Path Recommendation Logic

When the user does not know what to learn next, ALO must recommend 3 paths.

Example path categories:

```text
AI-Native Python Engineer
Backend and API Architecture
Testing and Engineering Discipline
GitHub Workflow and Code Review
LLM Application Developer
Product-Minded Technical Lead
```

Each recommendation must explain:

* why this path fits,
* what gap it solves,
* what the user will be able to do after finishing it,
* what should be learned first,
* what should be avoided for now.

## Daily Learning Session Design

A session should be small and focused.

Default session length:

```text
15 to 30 minutes
```

Each session should include:

```text
1 concept
1 short explanation
1 concrete example
1 practical question or coding task
1 evaluation
1 update to state
```

The lesson should be concise, engaging, and practical.

The evaluator should not be overly generous.

Grading options:

```text
pass
partial
fail
```

Rules:

* `pass`: user understood the concept and applied it correctly.
* `partial`: user understood part of it but missed an important detail.
* `fail`: user could not apply the concept or had a major misunderstanding.

A single pass must not automatically mark a whole skill as mastered.

## Git Commit Rules

ALO-generated commits should use predictable messages:

```text
ALO: initialize learning state
ALO: update assessment results
ALO: update roadmap for [Path]
ALO: learned [Topic]
ALO: reviewed [Topic]
ALO: update weaknesses
```

Do not commit secrets.

Do not commit if no files changed.

Do not push if remote is missing unless the user explicitly configures it.

## Testing Requirements

Every phase that changes code must include tests.

Minimum tests:

```text
pytest
ruff check
```

Core test coverage should include:

* config path does not store secrets in repo,
* Markdown files are created if missing,
* existing Markdown files are not overwritten,
* assessment scoring works,
* roadmap status update works,
* progress log append works,
* Git dirty state is detected,
* CLI commands execute with test runner.

## Development Phases

Build the project in these phases.

Do not jump ahead unless the current phase passes its acceptance criteria.

---

# Phase 0 — Audit and Architecture

Goal:

Inspect the repository and produce a technical implementation plan.

Tasks:

* inspect existing files,
* detect whether this is a new or existing learning repo,
* identify missing files,
* propose final architecture,
* propose CLI commands,
* propose state schema,
* propose tests.

Do not write production code in this phase unless explicitly asked.

Acceptance criteria:

* clear architecture proposal,
* clear file plan,
* clear phase plan,
* no destructive changes.

---

# Phase 1 — CLI Skeleton and Safe Config

Goal:

Create a working CLI foundation.

Tasks:

* create Python package structure,
* implement `alo --help`,
* implement `alo doctor`,
* implement local config loading from outside the repo,
* implement `.gitignore`,
* add basic tests.

Acceptance criteria:

* `alo --help` works,
* `alo doctor` works,
* config is not stored in repo,
* tests pass.

---

# Phase 2 — Markdown State Manager

Goal:

Create and update learning state files safely.

Tasks:

* implement state file detection,
* create missing Markdown files,
* preserve existing files,
* implement append-only progress log,
* implement roadmap item status update,
* implement weakness add/update,
* add tests.

Acceptance criteria:

* missing files are created,
* existing files are not overwritten,
* roadmap can be updated,
* progress log can be appended,
* tests pass.

---

# Phase 3 — Onboarding and Self-Report

Goal:

Implement `alo init` without assessment first.

Tasks:

* ask user what they know,
* ask user goals,
* ask preferred learning style,
* ask constraints,
* generate initial `learning-profile.md`,
* generate initial `skill-map.md`,
* optionally commit changes.

Acceptance criteria:

* onboarding can run end-to-end,
* generated Markdown is stable,
* no secrets are written,
* tests pass.

---

# Phase 4 — 20-Question Assessment

Goal:

Implement optional AI-generated assessment.

Tasks:

* implement `alo assess`,
* generate 20 multiple-choice questions using structured output,
* support manual fallback if LLM is unavailable,
* collect user answers,
* score by domain and difficulty,
* write assessment summary,
* update weaknesses,
* update skill map.

Acceptance criteria:

* assessment runs end-to-end,
* scoring is deterministic,
* weaknesses are generated from missed questions,
* result is saved to Markdown,
* tests pass.

---

# Phase 5 — Learning Path Recommendations

Goal:

Implement `alo paths`.

Tasks:

* read learning profile,
* read skill map,
* read weaknesses,
* generate 3 recommended paths,
* let user select one,
* store active path.

Acceptance criteria:

* 3 paths are generated,
* each path includes reasoning and tradeoffs,
* selected path is saved,
* tests pass.

---

# Phase 6 — Roadmap Generator

Goal:

Implement `alo roadmap`.

Tasks:

* generate roadmap from selected path or user-defined goal,
* chunk roadmap into small learning units,
* write stable roadmap format,
* support updating existing roadmap without destroying old progress.

Acceptance criteria:

* roadmap has stable IDs,
* each item has success criteria,
* each item has practice task,
* existing completed items are preserved,
* tests pass.

---

# Phase 7 — Daily Learning Loop

Goal:

Implement `alo learn`.

Tasks:

* read current state,
* planner chooses next topic,
* teacher generates short lesson,
* evaluator asks question,
* user answers,
* evaluation result updates roadmap, skill map, weaknesses, and progress log,
* optional Git sync.

Acceptance criteria:

* one full learning session works,
* pass/partial/fail update state differently,
* progress log is append-only,
* tests pass.

---

# Phase 8 — Review Mode

Goal:

Implement `alo review`.

Tasks:

* prioritize active weaknesses,
* teach/retest weak topics,
* update weakness status,
* update progress log.

Acceptance criteria:

* weaknesses are prioritized,
* repeated failures increase severity,
* successful review reduces severity or closes weakness,
* tests pass.

---

# Phase 9 — Git Sync Hardening

Goal:

Make Git operations safe and reliable.

Tasks:

* implement safe pull,
* implement dirty tree detection,
* implement commit only when files changed,
* implement push with error handling,
* support no-push mode,
* support dry-run mode.

Acceptance criteria:

* dirty tree is detected,
* no accidental overwrite,
* no empty commits,
* failed push is reported clearly,
* tests pass.

---

# Phase 10 — Packaging and Polish

Goal:

Make ALO ready to install and use.

Tasks:

* finalize `pyproject.toml`,
* add installation instructions,
* add example workflow,
* add README,
* add CLI help text,
* add error messages,
* add documentation for config and privacy.

Acceptance criteria:

* clean install works,
* CLI commands are documented,
* tests pass,
* README explains the full workflow.

## Implementation Rule

When asked to implement a phase, implement only that phase.

Do not silently implement future phases.

Do not invent unrelated features.

Do not remove existing user content.

Do not store secrets.

Always run tests or explain why tests could not be run.

Always end with a clear next step.
