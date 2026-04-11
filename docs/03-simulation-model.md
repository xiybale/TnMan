# Simulation Model

## Match Flow

Each match is simulated point by point. Each point follows the same core pipeline:

1. First-serve attempt.
2. Optional second-serve attempt.
3. Serve threat evaluation.
4. Return resolution.
5. Rally loop until a terminal outcome is reached.
6. Score update.

## Skill Model

Every player profile uses the following primary ratings on a 0-100 scale:

- `serve_power`
- `serve_accuracy`
- `second_serve_reliability`
- `return_quality`
- `forehand_quality`
- `backhand_quality`
- `movement`
- `anticipation`
- `rally_tolerance`
- `net_play`
- `composure`
- `pressure_handling`
- `stamina`

These raw ratings are supported by style fields:

- `baseline_aggression`
- `preferred_serve_direction`
- `short_ball_attack`
- `net_frequency`
- `surface_profile`

Player identity factors also matter in point resolution:

- `handedness` changes serve geometry and common forehand-to-backhand patterns.
- `backhand_hands` differentiates one-handed and two-handed backhands under spin pressure.
- `spin_profile` captures serve spin, forehand topspin, backhand topspin, and slice usage.

## Pressure Model

Pressure is tracked as a score-state index on a 0-100 scale.

Pressure rises in these contexts:

- `30-30` is elevated pressure,
- `30-40` and other one-point-from-game states are high pressure,
- deuce and advantage points,
- break points,
- set points,
- match points,
- tiebreaks.

Set point and match point are treated as maximum pressure (`100/100`).

`pressure_handling` is the primary clutch skill. It reduces execution penalties on high-pressure points across serves, returns, and rallies. `composure` still matters, but now acts as a secondary stabilizer rather than the only pressure-control attribute.

## Fatigue Model

Fatigue accumulates through:

- points played,
- shots struck,
- and longer rallies.

Lower stamina increases fatigue accumulation, which then reduces serve quality, movement, and execution stability as the match progresses.

## Surface Model

Surface is implemented through modifiers, not separate engines.

### Hard

- neutral baseline,
- balanced serve and return value,
- medium rally length.

### Clay

- longer rallies,
- more value on movement and rally tolerance,
- slightly reduced free points on serve.

### Grass

- shorter rallies,
- higher serve reward,
- reduced neutral-rally duration.

## Shot Resolution

Each shot is resolved in three stages.

### 1. Shot Selection

The engine picks a shot family from current context:

- serve or return,
- baseline drive,
- slice,
- approach,
- volley,
- lob,
- smash.

The selection is influenced by player tactics, whether an opponent is already at net, and how much pressure the current ball carries.

One-handed backhand players are more likely to mix slice and transition forward. Opposite-handed matchups create more forehand-to-backhand patterns than same-handed matchups.

### 2. Shot Quality

The selected shot gets an execution score based on:

- the relevant technical skill,
- aggression intent,
- handedness matchup,
- one-handed or two-handed backhand style,
- chosen spin type,
- movement and anticipation,
- fatigue,
- pressure handling and composure under pressure,
- surface comfort.

The result is mapped into a quality band:

- defensive,
- neutral,
- aggressive,
- finishing.

### 3. Shot Outcome

The quality band and attacker-vs-defender comparison drive one of five outcomes:

- continue rally,
- winner,
- forced error,
- unforced error,
- serve-led direct point outcome such as ace or service winner.

## RNG and Reproducibility

- Every match uses a seeded random generator.
- Same players plus same config plus same seed must reproduce the same shot log and result.
- Batch simulation should vary only through seed changes.

## Logging Contract

Each shot event should retain:

- point number,
- shot number,
- current score context,
- striker and receiver,
- shot type,
- hand used where relevant,
- spin type,
- quality band,
- pressure value,
- fatigue value,
- terminal outcome.
