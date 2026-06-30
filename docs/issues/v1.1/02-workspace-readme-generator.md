# Issue: Workspace README Generator

## Title
Implement `alo readme` to generate a Workspace README

## Problem
Currently, the ALO learning workspace has many markdown files, but no central, shareable overview of the user's progress. A `README.md` in the workspace root would solve this.

## Goal
Provide a command (`alo readme` or `alo portfolio`) to generate a beautiful, Git-friendly `README.md` at the root of the workspace showing learning stats and progress.

## Scope
- Implement `alo readme` command
- Support `--dry-run` and `--force`
- Pull metrics from the newly introduced Stats Engine
- Do not overwrite existing README unless `--force` is applied or ALO manages it.

## Non-goals
- Generating a web portfolio
- Network dependencies or external APIs

## Acceptance Criteria
- `alo readme` produces a valid, attractive Markdown file containing progress context.
- Safety rails prevent accidental overwriting of user-crafted READMEs without `--force`.

## Test Requirements
- End-to-end test verifying the file is successfully created in a temp workspace.
- Unit test ensuring `--dry-run` mutates no files.

## Security Considerations
- The generator must strictly scrub all LLM API keys and private configuration from the output.

## Labels Suggestion
`enhancement`, `cli`, `v1.1.0`

## Priority
P1

## Implementation Note
Implemented in Phase 16.
