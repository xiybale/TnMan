# Roadmap

## Milestone 0: Foundations

Deliverables:

- Python project scaffold.
- Markdown documentation set.
- Core domain types and repository layout.
- Sample ATP roster.

Exit criteria:

- Project can load player profiles.
- CLI entry points are wired.
- Test harness runs locally.

## Milestone 1: Match Engine MVP

Deliverables:

- Scoring engine for games, sets, tiebreaks, best-of-3, and best-of-5.
- Seeded point simulation.
- Rally loop with serve, return, and rally events.
- Match report output and shot log preview.

Exit criteria:

- One full singles match can be simulated end to end.
- Same seed always reproduces the same result.
- Scorelines are valid across tested edge cases.

## Milestone 2: Realism Pass

Deliverables:

- Surface modifiers for hard, clay, and grass.
- Pressure and fatigue modifiers.
- Player style differentiation.
- Batch simulation metrics for early calibration.

Exit criteria:

- Strong servers hold more often than weak servers.
- Surface specialists show meaningful performance splits.
- Aggregate metrics can be compared to benchmark ranges.

## Milestone 3: Data Pipeline

Deliverables:

- Public-data normalization pipeline into internal profiles.
- Mapping from ATP-facing stats to internal skill ratings.
- Override mechanism for missing or noisy data.

Exit criteria:

- New player profiles can be generated from structured rows.
- Internal schema remains stable while data sources vary.

## Milestone 4: World Layer

Deliverables:

- Tournament calendar.
- Rankings and points.
- Schedule-driven fatigue carry-over.
- Basic season progression loop.

Exit criteria:

- User can run a sequence of tournaments with persistent player state.
- Match engine remains reusable without redesign.

## Milestone 5: Manager Systems

Deliverables:

- Training and tactical presets.
- Injuries and recovery windows.
- Staff and scouting abstractions.
- Finance and contract systems.

Exit criteria:

- User choices between tournaments measurably affect future match outcomes.

## Dependency Notes

- Match simulation quality blocks every higher-level system.
- Calibration work should run in parallel with data ingestion once the engine is stable.
- UI work should begin only after the service boundaries in the current architecture remain stable for several iterations.

