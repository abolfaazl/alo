# ALO v1.1.0 Roadmap & Product Spec

## v1.1.0 Goal
**Learning Portfolio, Stats, Progress Charts & Gamification**

ALO will evolve from a local workspace manager into a motivating, shareable, and measurable learning system. The focus is on providing insights into the user's progress through localized stats, auto-generated progress charts, and a beautiful workspace README.

## Non-Goals
- No cloud services or backend dependencies
- No telemetry or external tracking
- No user accounts or authentications
- No external hosted dashboards
- No dark patterns or leaderboards

## Target Users
- Self-learners seeking motivation and consistency
- Developers organizing their continuous education
- Students needing an offline-first progress tracker

## Feature List & Scope
1. **P0:** Learning Stats Engine (Derived from local Markdown files)
2. **P1:** Workspace README Generator (`alo readme`)
3. **P1:** Progress Charts / SVG Assets (Renderable on GitHub)
4. **P2:** Lightweight Gamification (Streaks, Badges, Milestones)
5. **P3:** Roadmap Import Research (Spec for roadmap.sh compatibility/JSON/MD imports)

## Priority Order
1. Learning Stats Engine (foundation)
2. Workspace README Generator (presentation)
3. Progress Charts / SVG Assets (visuals)
4. Gamification (motivation layer)
5. Roadmap Import (research backlog)

## Risks
- Generating a README without overwriting user customizations
- Making SVG charts look native and attractive without external web rendering tools
- Accurate streak tracking over local Git commits

## Technical Architecture Notes
**Planned Modules:**
- `alo/services/stats_service.py` - Core metric aggregation
- `alo/services/readme_service.py` - Templating and I/O for `alo readme`
- `alo/services/chart_service.py` - Local SVG asset generation
- `alo/services/gamification_service.py` - Badge and streak logic
- `alo/models/stats.py` - Pydantic models for stats state
- `alo/ui/views.py` - Dashboard updates for stats visualization

**Data Flow:**
Workspace State (MD) -> Stats Service -> Gamification Service -> Chart Service -> Readme Service -> Workspace Output (MD + SVG)

**Security Model:**
- No API keys in generated README
- No raw provider config in generated README
- No secrets in SVG files
- Secret scan runs before generated files are synced
- No unknown files staged by sync unless explicitly safe-listed
- No telemetry or external tracking pixels

## Testing Strategy
- Core unit tests for the Stats Engine using mock Markdown fixtures
- Security tests to verify secret sanitization in generated readmes
- Integration tests simulating `alo readme --dry-run` and `--force`
- Verify SVG assets render successfully offline in standard browsers

## Release Criteria
- Stats engine successfully parses existing workspace files and computes metrics locally
- Stats engine has full unit test coverage
- README generator implements `--dry-run` and `--force` modes
- Generated README and SVGs do not expose LLM configurations or secrets
- Generated SVG assets render properly on GitHub
- Git sync safe-list handles generated public assets safely
- Gamification is optional and derived from real stats
- No network required for stats, readme, or charts
- All existing tests pass
- New tests cover stats, readme, and security mechanisms
- Documentation is fully updated
- PyPI installation remains functional
