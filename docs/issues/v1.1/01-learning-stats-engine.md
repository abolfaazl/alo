# Issue: Learning Stats Engine

## Title
Build the Learning Stats Engine

## Problem
Currently, ALO stores learning progress in Markdown state files but does not expose analytical insights. Users cannot easily see their consistency, completed lessons, or how much of the roadmap is accomplished.

## Goal
Create a localized, zero-dependency Stats Engine that aggregates data from the user's workspace Markdown files.

## Scope
- Extract data from `progress-log.md`, `roadmap.md`, and `weaknesses.md`
- Compute metrics: `lessons_completed`, `reviews_completed`, `practice_sessions`, `active_learning_days`, `current_streak_days`, `longest_streak_days`, `lessons_per_day`, `lessons_per_week`, `review_frequency`, `roadmap_completion_percent`, `weaknesses_open`, `weaknesses_resolved`, `consistency_score`

## Non-goals
- No external tracking or telemetry
- No cloud storage or remote APIs
- No fake or extrapolated metrics

## Acceptance Criteria
- Stats engine can parse valid workspace markdown logs reliably.
- Computed metrics reflect accurate historical counts.
- Fallback gracefully when log files are empty.

## Test Requirements
- Unit tests with mock Markdown files simulating different progression scenarios.
- Tests for robust date parsing.

## Security Considerations
- Data parsing must not execute code.
- File parsing must remain tightly scoped to known ALO workspaces.

## Labels Suggestion
`enhancement`, `core`, `v1.1.0`

## Priority
P0
