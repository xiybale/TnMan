# Tennis Pro Manager

Tennis Pro Manager is a simulation-first tennis management game prototype inspired by the long-form decision making of Football Manager. The current implementation focuses on the hardest foundational problem first: a seeded, shot-by-shot ATP singles match engine that can be calibrated toward realistic aggregate tennis outcomes.

## Current Scope

- CLI-first experience with no graphics.
- Current ATP top-100 roster snapshot plus curated legacy extras.
- Deterministic match simulation from a seed.
- Surface-aware scoring, fatigue, pressure, tactical tendencies, and handedness/spin matchup effects.
- Batch simulation for early calibration and balancing work.

## Project Layout

- `docs/`: design, roadmap, simulation, architecture, and testing contracts.
- `src/tennis_pro_manager/`: engine, scoring, roster loading, ingest utilities, reporting, and CLI.
- `web/`: React + TypeScript web UI scaffold for the simulation desk.
- `data/players/`: ATP player profiles used by the current prototype.
- `scripts/`: build-time utilities for roster generation and other offline prep tasks.
- `data/external/`: cached third-party inputs used to enrich roster generation.
- `tests/`: scoring, engine, and CLI verification.

## Quick Start

The cleanest local workflow is an editable install in `.venv`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e '.[dev,web]'
.venv/bin/python -m tennis_pro_manager inspect-player jannik-sinner
```

On this host, `python3 -m venv` is currently blocked because the distro package `python3.12-venv` is missing. To keep development repeatable without modifying the system Python, use the local setup script instead:

```bash
./scripts/setup-dev.sh
```

That script prefers `.venv` when available and otherwise installs a self-contained backend toolchain into `.pydeps/` plus the frontend dependencies into `web/node_modules/`.

Legacy convenience launcher:

```bash
python3 tpm.py simulate-match novak-djokovic carlos-alcaraz --surface hard --seed 42
python3 tpm.py simulate-batch novak-djokovic hubert-hurkacz --surface grass --iterations 50 --seed 100
python3 tpm.py inspect-player carlos-alcaraz
python3 tpm.py calibrate
```

To rebuild the roster snapshot from downloaded source files:

```bash
python3 scripts/fetch_tennis_abstract_charting.py \
  --output data/external/tennis_abstract_charting.json

python3 scripts/build_atp_top_100_roster.py \
  --players-csv /tmp/atp_players.csv \
  --matches-csv /tmp/atp_matches_2024.csv \
  --ta-charting-cache data/external/tennis_abstract_charting.json
```

## CLI Commands

- `simulate-match`: run one seeded match and print the scoreline, key stats, and a shot log preview.
- `simulate-batch`: run many matches and print win rates and calibration-style aggregates.
- `inspect-player`: inspect a player profile from the ATP sample roster.
- `calibrate`: run deterministic benchmark scenarios from `data/calibration/benchmark_scenarios.json`.

## Documentation Index

- [Product Vision](docs/01-product-vision.md)
- [Roadmap](docs/02-roadmap.md)
- [Simulation Model](docs/03-simulation-model.md)
- [Data and Calibration](docs/04-data-and-calibration.md)
- [Architecture](docs/05-architecture.md)
- [Testing and Acceptance](docs/06-testing-and-acceptance.md)
- [Calibration Plan](docs/07-calibration-plan.md)
- [Roster Generation](docs/08-roster-generation.md)
- [Web UI Plan](docs/09-web-ui-plan.md)
- [API Contracts](docs/10-api-contracts.md)
- [Match Report Model](docs/11-match-report-model.md)
- [Design System](docs/12-design-system.md)

## What Exists Today

The engine already resolves each point as `serve -> return -> rally loop -> terminal event`. Each shot is influenced by the player's technical skills, tactical lean, handedness, one-handed or two-handed backhand profile, spin tendencies, current score pressure, fatigue load, and the selected surface.

This is not yet a full manager game. There is no tournament calendar, persistence layer, rankings engine, finances, staff, injuries, or training loop in the current build. The codebase is intentionally structured so those systems can call into the match engine without rewriting it.

## Next Product Layer

After the match engine, the best next step is a lightweight world layer:

1. Tournament scheduling.
2. Rankings and points.
3. Carry-over fatigue and recovery.
4. Basic player progression and tactical presets.

## Web API Foundation

The backend contract exposes structured player, compare, match, and batch payloads so the UI can render simulation dashboards and Flashscore-style match reports without parsing CLI output.

Backend dev server:

```bash
./scripts/dev-backend.sh
```

Frontend dev server:

```bash
cp web/.env.example web/.env
./scripts/dev-frontend.sh
```

Backend tests:

```bash
./scripts/test-backend.sh -q
```

If the host later gets `python3.12-venv`, rerun `./scripts/setup-dev.sh` and it will switch back to the cleaner editable `.venv` workflow automatically.
