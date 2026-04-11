# Architecture

## Guiding Principle

The match engine is the product core and should remain reusable. UI and future management systems should call the engine through clean service boundaries rather than reaching into score or shot logic directly.

## Package Layout

- `tennis_pro_manager.models`
  Domain types, enums, and result models.
- `tennis_pro_manager.scoring`
  Pure tennis scoring logic.
- `tennis_pro_manager.simulator`
  Match and batch simulation services.
- `tennis_pro_manager.roster`
  Player profile loading and lookup.
- `tennis_pro_manager.ingest`
  Structured-row normalization into internal player profiles.
- `tennis_pro_manager.reporting`
  Human-readable CLI output.
- `tennis_pro_manager.analysis`
  Match-pattern and rally-distribution summaries derived from event logs.
- `tennis_pro_manager.calibration`
  Deterministic benchmark scenario loading and calibration evaluation.
- `tennis_pro_manager.cli`
  Command routing and argument parsing.

## Public Interfaces

The current codebase should keep these interfaces stable:

- `PlayerProfile`
- `MatchConfig`
- `MatchResult`
- `BatchSummary`
- `MatchSimulator.simulate_match(...)`
- `MatchSimulator.simulate_batch(...)`
- `load_roster(...)`
- `load_player(...)`

## Data Boundaries

- `data/players/atp_profiles.json` is the current playable roster.
- Future raw imports should remain separate from curated internal profiles.
- The internal player schema should be richer than any single external data source.

## Extension Hooks

The following systems should be added around the current engine rather than inside it:

- tournament scheduling,
- rankings,
- fatigue carry-over,
- training and progression,
- injuries,
- staff and scouting,
- finances and contracts.

## Persistence Strategy

The current build is file-based and stateless at runtime. That is intentional for early simulation work. Once a world layer exists, save files can store:

- player state,
- rankings,
- calendar position,
- tournament entries,
- long-term fatigue and form.
