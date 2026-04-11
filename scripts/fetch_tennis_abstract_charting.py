from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from build_atp_top_100_roster import AUTO_GENERATED_NOTE_PREFIX, TOP_100_SNAPSHOT
from tennis_pro_manager.tennis_abstract import (
    ChartingSnapshot,
    charting_player_url,
    parse_charting_page,
    save_charting_cache,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "external" / "tennis_abstract_charting.json"
DEFAULT_ROSTER_PATH = PROJECT_ROOT / "data" / "players" / "atp_profiles.json"
USER_AGENT = "TennisProManager/0.1 (+https://www.tennisabstract.com/)"
SSL_CONTEXT = ssl._create_unverified_context()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Tennis Abstract charting pages for the ATP top 100 and preserved curated extras."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for the parsed charting cache JSON.",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=150,
        help="Delay between requests in milliseconds.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for partial fetches while testing.",
    )
    parser.add_argument(
        "--roster-path",
        type=Path,
        default=DEFAULT_ROSTER_PATH,
        help="Roster JSON used to discover preserved curated extras outside the current top 100.",
    )
    return parser.parse_args(argv)


def load_curated_roster_names(roster_path: Path) -> list[str]:
    if not roster_path.exists():
        return []

    names: list[str] = []
    seen: set[str] = set()
    for entry in json.loads(roster_path.read_text()):
        name = entry.get("name")
        notes = entry.get("derived_stats", {}).get("source_notes", [])
        if not name or name in seen:
            continue
        if notes and str(notes[0]).startswith(AUTO_GENERATED_NOTE_PREFIX):
            continue
        names.append(str(name))
        seen.add(str(name))
    return names


def fetch_page(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    # Tennis Abstract is a public source and this runtime does not ship a usable CA bundle.
    with urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
        return response.read().decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    snapshots: dict[str, ChartingSnapshot] = {}
    fetched_at = datetime.now(UTC).date().isoformat()
    delay_seconds = max(args.delay_ms, 0) / 1000.0
    player_names = [entry["name"] for entry in TOP_100_SNAPSHOT]
    for extra_name in load_curated_roster_names(args.roster_path):
        if extra_name not in player_names:
            player_names.append(extra_name)
    if args.limit:
        player_names = player_names[: args.limit]

    fetched = 0
    skipped = 0
    failures = 0

    for player_name in player_names:
        url = charting_player_url(player_name)
        try:
            page_html = fetch_page(url)
        except HTTPError as exc:
            if exc.code == 404:
                skipped += 1
                print(f"[skip] {player_name}: no charting page at {url}")
                continue
            failures += 1
            print(f"[fail] {player_name}: HTTP {exc.code} at {url}")
            continue
        except URLError as exc:
            failures += 1
            print(f"[fail] {player_name}: {exc.reason}")
            continue

        snapshot = parse_charting_page(
            page_html,
            player_name=player_name,
            source_url=url,
            fetched_at=fetched_at,
        )
        if snapshot is None:
            skipped += 1
            print(f"[skip] {player_name}: page fetched but no usable charting tables")
            continue

        snapshots[snapshot.player_id] = snapshot
        fetched += 1
        print(
            f"[ok] {player_name}: "
            f"1stIn {snapshot.first_serve_in:.1%}, "
            f"1stWon {snapshot.first_serve_points_won:.1%}, "
            f"2ndWon {snapshot.second_serve_points_won:.1%}, "
            f"RPW {snapshot.return_points_won:.1%}"
        )
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    save_charting_cache(snapshots, args.output)
    print(
        f"saved {len(snapshots)} charting snapshots to {args.output} "
        f"(fetched {fetched}, skipped {skipped}, failed {failures})"
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
