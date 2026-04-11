# Data and Calibration

## ATP-First Strategy

The first roster targets ATP singles only. This keeps the data model narrow while still providing enough variety to tune:

- elite servers,
- elite returners,
- all-court players,
- clay specialists,
- aggressive hard-court attackers.

## Player Profile Sources

V1 uses a hybrid strategy:

- a current ATP top-100 roster snapshot captured from the official ATP singles rankings page on 2026-04-09,
- manually curated profiles retained where the project already had explicit tuning and matchup traits,
- a normalization pipeline that can transform structured ATP-facing rows into internal profiles,
- manual overrides for players where public data is incomplete or noisy.
- explicit handedness, backhand style, and spin tendencies where those traits materially affect matchups.

## Current Roster Build

The committed roster is built from three layers:

- official ATP top-100 membership from `https://www.atptour.com/Rankings/Singles` as of 2026-04-09,
- biographical metadata from Jeff Sackmann's `atp_players.csv`,
- ATP tour-level 2024 match stats from Jeff Sackmann's `atp_matches_2024.csv`,
- current Tennis Abstract Match Charting Project player pages fetched on 2026-04-10 and cached locally for latest serve, return, serve-direction, and net-approach tendencies.

Where a current top-100 player has weak or no ATP-level 2024 stat coverage, the build pipeline falls back to ranking-based priors shaped by age, height, handedness, and broad surface-country heuristics. Where current Tennis Abstract charting coverage exists, the generator blends that more recent data back into serve accuracy, serve effectiveness, return strength, preferred serve direction, and net instincts before the top-100 normalization pass runs.

## Rating Derivation

Internal ratings are derived from observable public-style metrics wherever possible.

### Serve Cluster

- first-serve in %
- first-serve points won %
- second-serve points won %
- ace rate
- double-fault rate

### Return Cluster

- return points won %
- break rate
- surface splits

### Rally and Physical Cluster

- longer-run match performance
- surface spread
- clutch tendencies
- curated expert tuning when public stat coverage is weak

### Identity and Style Cluster

- left-handed or right-handed serving geometry
- one-handed or two-handed backhand profile
- serve spin, topspin usage, and slice frequency

## Calibration Benchmarks

The engine should be compared against surface-aware target ranges for:

- hold %
- break %
- ace %
- double-fault %
- first-serve in %
- average rally length
- winner to unforced-error relationship

The current codebase includes batch simulation output designed to support this loop, even before a full benchmark dataset is wired in.

## Calibration Workflow

1. Run batches across multiple matchups and surfaces.
2. Compare aggregate output against target ranges.
3. Tune formulas, not one-off hacks.
4. Re-run regression batches after each tuning pass.
5. Lock seeds for deterministic test scenarios.

## Known Data Limits

- Public ATP-style data does not fully describe shot intent or placement.
- Shot-by-shot realism in V1 is inferred rather than observed.
- Tennis Abstract charting is volunteer-collected and coverage quality varies by player.
- Some attributes such as pressure handling, composure, tactical aggression, and net instincts will remain partly curated until richer data is available.
