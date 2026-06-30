# Issue: Roadmap Import Research

## Title
Research Roadmap Integration and Import Formats

## Problem
Currently, ALO relies entirely on the LLM to generate learning roadmaps. Users might want to import established curricula (e.g., from roadmap.sh) or custom JSON/Markdown roadmaps.

## Goal
Draft a specification for how ALO could import external roadmaps into its native `roadmap.md` state format.

## Scope
- Spec a local JSON import adapter.
- Spec a local Markdown import adapter.
- Spec manual pasted text ingestion.
- Research future `roadmap.sh`-compatible adapters.

## Non-goals
- Full `roadmap.sh` integration is NOT in scope for v1.1.0 implementation.
- Do not scrape external sites aggressively or assume stable undocumented APIs exist.

## Acceptance Criteria
- A finalized architectural proposal document exists outlining how imports will work in future versions.

## Test Requirements
- None for the research phase.

## Security Considerations
- Importing external data must sanitize inputs to prevent injection attacks or malicious payload execution inside the CLI.

## Labels Suggestion
`research`, `architecture`, `v1.1.0`

## Priority
P3
