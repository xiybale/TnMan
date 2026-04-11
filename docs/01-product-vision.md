# Product Vision

## Core Fantasy

Tennis Pro Manager should make the user feel like they are running a serious elite tennis operation, not just watching random scorelines appear. The long-term fantasy is:

- build a player or stable of players over many seasons,
- make strategic, tactical, and developmental choices,
- understand why matches were won or lost,
- and trust that the simulation behaves like real tennis.

The project starts with match realism because every future management feature depends on the engine producing believable incentives and outcomes.

## Design Pillars

### 1. Simulation Credibility

The game must produce tennis results that feel internally consistent and statistically plausible. A dominant server should usually hold more often. Clay should create longer exchanges. Elite returners should pressure serve games even when they do not dominate outright.

### 2. Explainable Outcomes

The user should be able to inspect what happened at point level. Even without graphics, the game should expose enough event detail to understand momentum, tactical success, and error patterns.

### 3. Managerial Consequences

Every later management system should matter because of the simulation core. Training, fatigue, scheduling, coaching, scouting, and tactics must all have clear pathways into match outcomes.

### 4. Extensible Architecture

The match engine should not be coupled to a specific interface. CLI comes first, but the same services should later support a desktop or web front end.

## First Playable Version

The first playable version is intentionally narrow:

- ATP singles only.
- Non-graphical CLI experience.
- Shot-by-shot match simulation.
- Surface-aware player profiles.
- Seeded deterministic execution for testing and balancing.
- Batch simulation for calibration and tuning.

## Out of Scope for V1

- Doubles.
- WTA support.
- Real-time graphics or animation.
- Licensed ATP data ingestion automation.
- Tournament calendar.
- Rankings, contracts, finances, staff, injuries, scouting, and player development loops.

## Definition of “Accuracy”

V1 accuracy means statistical realism first:

- realistic hold and break dynamics,
- plausible ace and double-fault rates,
- believable rally length distribution by surface,
- recognisable player differences,
- and event logs that support tactical interpretation.

Full ball physics, tracking-data fidelity, and perfect shot-map realism are explicitly not the goal for the first version.

