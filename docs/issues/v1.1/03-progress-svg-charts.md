# Issue: Progress SVG Charts

## Title
Generate GitHub-renderable local SVG Progress Charts

## Problem
Text stats are useful, but visuals are better. GitHub READMEs support SVG rendering, and ALO should provide a visual portfolio.

## Goal
Implement SVG chart generation derived purely from local stats to enrich the generated workspace README.

## Scope
- Create charts for: `alo-progress.svg`, `alo-practice.svg`, `alo-streak.svg`, `alo-roadmap.svg`
- Update the Git sync safe-list to track generated assets in the `assets/` folder.

## Non-goals
- Embedding interactive JS frameworks (D3, Chart.js). Charts must be static, offline SVGs.
- Utilizing external APIs to generate images.

## Acceptance Criteria
- Commands successfully write valid `.svg` output files inside `assets/`.
- The SVG renders natively inside standard browsers and GitHub's Markdown viewer.

## Test Requirements
- Assert that SVG tags are correctly formed.
- Check SVG file creation behavior across operating systems.

## Security Considerations
- Ensure no credential or configuration data accidentally interpolates into SVG templates.

## Labels Suggestion
`enhancement`, `frontend`, `v1.1.0`

## Priority
P1

## Implementation Note
Implemented in Phase 17.
