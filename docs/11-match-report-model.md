# Match Report Model

## Goal

The match report model exists to support a Flashscore-style tennis report UI without forcing the frontend to reverse-engineer match state.

## Core Report Layers

### Match Meta

- player ids and names
- winner id
- scoreline
- surface
- best-of format
- seed
- average rally length
- total points

### Match Stats

Per player:

- aces
- service winners
- double faults
- first-serve percentage
- service points won
- return points won
- break points created and converted
- winners
- return winners
- forced errors drawn
- unforced errors

### Pattern Summary

Per player:

- serve direction mix
- serve spin mix
- targeted wing mix
- rally spin mix
- winners by hand
- forced errors drawn by hand
- unforced errors by hand

### Set Report

For each completed set:

- set number
- score
- winner id
- tiebreak points when present
- per-player set stats
- ordered game timeline

### Game Report

For each game:

- set number
- game number within set
- score before the game
- score after the game
- server id
- winner id
- hold or break classification
- tiebreak flag
- ordered point list

### Point Report

For each point:

- point number
- set number
- game number within set
- server id
- receiver id
- winner id
- score before
- score after
- point score before
- point score after
- pressure index and label
- break point, set point, and match point flags
- rally length
- terminal shot kind and outcome
- ordered shot list for drilldown

## Builder Strategy

- record point-level results during simulation
- derive game and set groupings from point records
- compute set stats by replaying point contributions into per-set accumulators
- expose the nested structure directly to the frontend

## Why This Model

- the frontend can render a scoreboard and report pages without tennis-specific state logic
- the CLI can continue using its own formatting path
- later features such as saved reports, live playback, and tactic overlays can reuse the same structure
