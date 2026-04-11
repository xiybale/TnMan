# Calibration Plan

## Purpose

The calibration layer exists to stop realism drift as the engine evolves. It is not a replacement for deep statistical validation, but it provides fast deterministic checks against a known set of archetypal ATP matchups.

## Current Benchmark Structure

- `data/calibration/benchmark_scenarios.json` defines deterministic scenarios.
- Each scenario locks:
  - player matchup,
  - surface,
  - best-of format,
  - iteration count,
  - RNG seed,
  - target ranges for selected metrics.

## Current Metrics

- player win rate
- player hold rate
- player break rate
- service points won rate
- return points won rate
- combined ace rate
- combined first-serve-in rate
- combined double-fault rate
- average rally length
- average points per match
- rally length band distribution

## Intended Workflow

1. Run `tpm calibrate`.
2. Review any failed scenarios.
3. Compare failed metrics against recent engine changes.
4. Tune formulas or profile data.
5. Re-run the benchmark suite before merging further realism changes.

## Limits

- The current suite is engine-relative, not ATP-truth-complete.
- Target bands should tighten as the roster grows and external benchmark references improve.
- A passing suite only means the engine remains within expected ranges for the modeled archetypes.
