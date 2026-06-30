# Issue: Gamification, Streaks & Badges

## Title
Implement Lightweight Gamification (Streaks & Badges)

## Problem
Learning is difficult without intrinsic and extrinsic motivation. ALO needs lightweight ways to reward consistent effort.

## Goal
Add local-only, optional gamification features like learning streaks, weekly goals, and milestone badges.

## Scope
- Implement streak tracking algorithm based on `progress-log.md` commit timestamps or internal tracking lines.
- Define a set of initial badges (e.g., First Lesson, 7-Day Streak, Deep Practice Week).
- Display badges and streaks in the dashboard UI and generated READMEs.

## Non-goals
- No dark patterns, guilt-tripping, or mandatory notifications.
- No social leaderboards.
- No external tracking. Everything computed locally.

## Acceptance Criteria
- Streak calculations handle timezone variations and missed days logically.
- Badges unlock conditionally based on aggregated local metrics from the Stats Engine.

## Test Requirements
- Logic tests for streak edge cases (e.g., bridging weekends, leap years).

## Security Considerations
- Gamification state should not bloat the workspace or leak external tracking data.

## Labels Suggestion
`enhancement`, `motivation`, `v1.1.0`

## Priority
P2
