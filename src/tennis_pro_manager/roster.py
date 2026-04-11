from __future__ import annotations

import json
from pathlib import Path

from .models import PlayerProfile


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_roster_path() -> Path:
    return project_root() / "data" / "players" / "atp_profiles.json"


def load_roster(roster_path: str | Path | None = None) -> dict[str, PlayerProfile]:
    path = Path(roster_path) if roster_path is not None else default_roster_path()
    payload = json.loads(path.read_text())
    return {entry["player_id"]: PlayerProfile.from_dict(entry) for entry in payload}


def load_player(player_id: str, roster_path: str | Path | None = None) -> PlayerProfile:
    roster = load_roster(roster_path)
    try:
        return roster[player_id]
    except KeyError as exc:
        raise KeyError(f"Unknown player id: {player_id}") from exc

