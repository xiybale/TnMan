# Roster Generation

## Scope

The current committed roster covers the ATP top 100 as captured from the official ATP singles rankings page on 2026-04-09. The file also preserves curated legacy profiles that were already in the project and remain useful for simulation testing or comparison work.

## Sources

- ATP top-100 membership: `https://www.atptour.com/Rankings/Singles`
- Player metadata: Jeff Sackmann `atp_players.csv`
- Match-stat inputs: Jeff Sackmann `atp_matches_2024.csv`
- Latest charting enrichment: Tennis Abstract Match Charting Project player pages fetched on 2026-04-10

## Why The Build Uses Mixed Sources

The ATP rankings page is the right source for current membership, but it is not a convenient machine-readable batch feed in this workspace. Sackmann's files provide strong structured coverage for player metadata and ATP tour-level match stats, but they lag the live ATP ranking table. The roster builder combines them:

- current membership comes from ATP,
- IDs, countries, and handedness come from `atp_players.csv`,
- playable stat baselines come from 2024 ATP match-level data,
- current serve, return, serve-direction, and net-approach tendencies can be refreshed from Tennis Abstract charting pages,
- low-sample players fall back to rank-shaped priors.

## Build Logic

The script is [build_atp_top_100_roster.py](/Users/alexiy.bordoukov/Documents/TnMan/scripts/build_atp_top_100_roster.py).

It does six things:

1. Loads the current top-100 snapshot embedded in the script.
2. Resolves each player against `atp_players.csv`.
3. Aggregates 2024 ATP tour-level serve, return, and surface data from `atp_matches_2024.csv`.
4. Optionally blends in the latest Tennis Abstract charting cache for players with current shot-chart coverage.
5. Preserves existing curated profiles when they already exist in the roster, and generates the missing current top-100 players from structured rows plus fallback priors.
6. Normalizes auto-generated in-game ratings into a top-100-only scale so generated players do not look like generic tour-level or challenger-level profiles.

## Handedness And Backhand Style

Handedness comes from the structured player metadata where available. A small manual override layer exists for players with unknown entries in the source file. Backhand style is currently explicit for known one-handed players in the top 100 and defaults to two hands otherwise.

This is a pragmatic choice, not a final data model. If a richer biographical source becomes available, that layer should replace the manual one-handed set.

## Rebuild Command

```bash
python3 scripts/fetch_tennis_abstract_charting.py \
  --output data/external/tennis_abstract_charting.json

python3 scripts/build_atp_top_100_roster.py \
  --players-csv /tmp/atp_players.csv \
  --matches-csv /tmp/atp_matches_2024.csv \
  --roster-path data/players/atp_profiles.json \
  --output data/players/atp_profiles.json \
  --ta-charting-cache data/external/tennis_abstract_charting.json
```

## Known Limits

- The roster membership is current to the ATP snapshot date above, not automatically live.
- The structured ATP match feed is still anchored to 2024 because a newer machine-readable match file was not available in the source dataset during this build.
- Tennis Abstract charting coverage is current but volunteer-collected, so not every field is equally complete for every player.
- Some young or newly risen players are materially more prior-driven than established tour regulars.
- One-handed backhand coverage is manually curated for now.
- Curated legacy starter profiles and auto-generated profiles are closer than before, but they are still not fully unified under a single balancing pass.
