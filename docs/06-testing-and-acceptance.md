# Testing and Acceptance

## Test Categories

### Scoring Logic

- deuce loops require a two-point margin,
- tiebreak serving order follows tennis rules,
- set completion is correct,
- best-of-5 match completion stops at the right set count.

### Engine Invariants

- every point ends with a legal winner,
- service and return point totals reconcile,
- scorelines are valid,
- deterministic seeds reproduce the same result and event log.

### Differentiation Checks

- elite servers hold more often than weak servers,
- strong returners create more pressure on serve,
- clay-friendly players improve on clay relative to grass or hard,
- aggressive players produce more direct-point outcomes.

### CLI Checks

- `simulate-match` runs end to end,
- `simulate-batch` prints aggregate metrics,
- `calibrate` runs deterministic scenario checks,
- `inspect-player` resolves a profile and prints useful detail.

## Acceptance Criteria

The current milestone is accepted when:

1. One full ATP singles match runs from the CLI.
2. Batch simulation reveals meaningful player and surface differentiation.
3. Tests cover the main scoring edge cases.
4. The repository contains enough markdown documentation for another engineer to continue without reverse engineering the code.

## Calibration Acceptance

Once external benchmark ranges are available, release acceptance should also require batch outputs to stay within agreed tolerance bands for key ATP metrics.
