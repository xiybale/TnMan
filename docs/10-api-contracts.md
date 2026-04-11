# API Contracts

## Scope

The first API is read-heavy and simulation-focused. It exists to support the player browser, compare page, single-match report, and batch dashboard.

## Endpoints

### `GET /health`

Purpose: readiness probe for the local web server.

Response:

```json
{
  "status": "ok",
  "players": 101
}
```

### `GET /players`

Purpose: roster browser listing.

Query parameters:

- `q`: optional case-insensitive search against id, name, or country
- `surface`: optional surface for contextual comfort sorting and edge hints

Response shape:

```json
{
  "players": [
    {
      "playerId": "novak-djokovic",
      "name": "Novak Djokovic",
      "country": "SRB",
      "tour": "ATP",
      "handedness": "right",
      "backhandHands": 2,
      "overallRating": 89.4,
      "surfaceComfort": {
        "hard": 94,
        "clay": 88,
        "grass": 92
      },
      "tags": ["elite return", "pressure resistant"],
      "topSkills": [
        {"label": "Return quality", "value": 95},
        {"label": "Pressure handling", "value": 94},
        {"label": "Composure", "value": 93}
      ]
    }
  ]
}
```

### `GET /players/{player_id}`

Purpose: detailed player profile for browser and compare pages.

Response includes:

- identity and handedness
- skills
- tactics
- spin profile
- physical profile
- surface profile
- derived stats
- strengths and weaknesses
- profile tags

### `GET /compare`

Query parameters:

- `player_one`
- `player_two`
- `surface`

Purpose: matchup preview contract for the compare page.

Response includes:

- both player detail payloads
- per-skill deltas
- surface edge
- matchup tags
- likely tactical themes

### `POST /simulate/match`

Request body:

```json
{
  "playerOne": "novak-djokovic",
  "playerTwo": "carlos-alcaraz",
  "surface": "hard",
  "bestOfSets": 3,
  "seed": 42,
  "initialServer": "novak-djokovic"
}
```

Response includes:

- match metadata
- overview match stats
- pattern summary
- set-by-set reports
- game-by-game reports
- point-by-point rows

### `POST /simulate/batch`

Request body:

```json
{
  "playerOne": "hubert-hurkacz",
  "playerTwo": "alexander-bublik",
  "surface": "grass",
  "bestOfSets": 3,
  "seed": 200,
  "iterations": 500
}
```

Response includes:

- win rates
- aggregate stats by player
- common scorelines
- rally-band distribution
- matchup metadata

## Contract Rules

- all enum values are lowercase strings
- player ids are stable slugs
- API keys use camelCase
- deterministic endpoints must produce identical responses for identical seeds and inputs
- point-by-point responses must preserve match order

## Error Contract

For invalid inputs or unknown players, the API should return:

```json
{
  "detail": "Unknown player id: foo-bar"
}
```
