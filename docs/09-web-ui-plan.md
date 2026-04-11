# Web UI Plan

## Goal

Build a premium simulation and analytics UI around the current tennis engine without coupling presentation code to the match core.

The first web release is not a full manager game shell. It is a simulation console with:

- fast player browsing
- side-by-side profile comparison
- single-match simulation
- batch simulation
- dense match reports with per-set stats and point-by-point detail

## Product Principles

- API-first: the frontend must consume structured JSON, never CLI text.
- Scoreboard-first: match outcomes and score progression should be visually dominant.
- Dense but scannable: the UI should feel closer to a modern sports data product than an internal admin dashboard.
- Deterministic simulation: seeded simulations must be reproducible across CLI and web.
- Frontend isolation: the engine should remain importable and testable without the web stack.

## First Release Scope

### Player Browser

- searchable and filterable ATP roster
- surface comfort badges
- handedness and backhand type indicators
- key skill bars
- current source notes and profile tags

### Compare View

- side-by-side player cards
- skill deltas
- surface-specific edge summary
- likely matchup themes such as serve edge, spin mismatch, pressure edge

### Single Match Simulation

- select players, surface, format, seed, and initial server
- run a match and receive a complete structured report
- render scoreline, match stats, set breakdown, serve patterns, rally bands, and point-by-point data

### Batch Simulation

- select matchup and iteration count
- render win rate split
- render scoreline distribution
- render serve and return metrics
- render rally-length and pressure distributions

### Match Report

- scoreboard header with set scores
- per-set stat tables
- per-game breakdown grouped by set
- point-by-point rows inside each game
- expandable shot sequence per point

## Recommended Technical Shape

### Backend

- keep the simulation engine in `src/tennis_pro_manager`
- add structured web payload builders in Python
- expose a small HTTP API with FastAPI
- keep FastAPI and Uvicorn in a `web` optional dependency group

### Frontend

- create a separate `web/` app
- use React, TypeScript, and Vite
- use TanStack Query for data fetching and cache management
- use Recharts or Visx for charts
- use CSS variables and a custom component system instead of a dashboard template

## Milestones

### Milestone 1: Report Model and API

- add structured point timeline data to match results
- add per-set and per-game report builders
- add player, compare, match, and batch API endpoints
- lock the initial JSON contracts in tests

### Milestone 2: Frontend Shell

- create app shell, routing, theme, and base layout
- build player browser and player detail pages
- build compare page

### Milestone 3: Simulation Workbench

- build single-match simulation flow
- build batch simulation dashboard
- add recent simulations state in the browser

### Milestone 4: Match Report Experience

- build Flashscore-style report view
- add per-set tabs or sections
- add collapsible games with point sequences
- add expandable shot-by-shot point drilldown

## Acceptance Criteria

- a user can browse the full ATP roster from the browser
- a user can compare any two players on any surface
- a user can run a single match and inspect a structured match report
- a user can run a batch simulation and understand the matchup through charts
- the API remains deterministic for fixed seeds

## Non-Goals For This Phase

- no live matches
- no multiplayer
- no tournament calendar UI
- no save-game management UI
- no graphical court rendering
