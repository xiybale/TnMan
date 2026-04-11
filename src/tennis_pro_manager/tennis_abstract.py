from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


_TABLE_ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
_TABLE_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_COUNT_PERCENT_RE = re.compile(r"(?P<count>[\d,]+)\s+\((?P<pct>-?\d+|-)%\)")
_MATCH_COUNT_RE = re.compile(r"records of\s*<a[^>]*>\s*(\d+)\s+matches", re.I)


@dataclass(slots=True)
class ChartingSnapshot:
    player_id: str
    player_name: str
    source_url: str
    fetched_at: str
    charted_matches: int | None
    service_points: int
    return_points: int
    first_serve_in: float
    first_serve_points_won: float
    second_serve_points_won: float
    ace_rate: float
    return_points_won: float
    preferred_serve_direction: str
    net_approach_rate: float | None = None
    net_points_won: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ChartingSnapshot:
        return cls(
            player_id=str(payload["player_id"]),
            player_name=str(payload["player_name"]),
            source_url=str(payload["source_url"]),
            fetched_at=str(payload["fetched_at"]),
            charted_matches=(
                int(payload["charted_matches"])
                if payload.get("charted_matches") is not None
                else None
            ),
            service_points=int(payload["service_points"]),
            return_points=int(payload["return_points"]),
            first_serve_in=float(payload["first_serve_in"]),
            first_serve_points_won=float(payload["first_serve_points_won"]),
            second_serve_points_won=float(payload["second_serve_points_won"]),
            ace_rate=float(payload["ace_rate"]),
            return_points_won=float(payload["return_points_won"]),
            preferred_serve_direction=str(payload["preferred_serve_direction"]),
            net_approach_rate=(
                float(payload["net_approach_rate"])
                if payload.get("net_approach_rate") is not None
                else None
            ),
            net_points_won=(
                float(payload["net_points_won"])
                if payload.get("net_points_won") is not None
                else None
            ),
        )


def charting_player_slug(player_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", player_name).encode("ascii", "ignore").decode("ascii")
    parts = re.findall(r"[A-Za-z0-9]+", normalized)
    return "".join(part[:1].upper() + part[1:] for part in parts)


def charting_player_url(player_name: str) -> str:
    return f"https://www.tennisabstract.com/charting/{charting_player_slug(player_name)}.html"


def player_id_from_name(player_name: str) -> str:
    normalized = unicodedata.normalize("NFKD", player_name).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("-", " ")
    normalized = re.sub(r"[^a-z0-9 ]+", " ", normalized)
    return re.sub(r"\s+", "-", normalized.strip())


def load_charting_cache(path: str | Path) -> dict[str, ChartingSnapshot]:
    cache_path = Path(path)
    if not cache_path.exists():
        return {}

    payload = json.loads(cache_path.read_text())
    if isinstance(payload, list):
        items = payload
    else:
        items = list(payload.values())
    return {
        str(item["player_id"]): ChartingSnapshot.from_dict(item)
        for item in items
    }


def save_charting_cache(snapshots: dict[str, ChartingSnapshot], path: str | Path) -> None:
    cache_path = Path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {player_id: snapshot.to_dict() for player_id, snapshot in sorted(snapshots.items())}
    cache_path.write_text(json.dumps(ordered, indent=2) + "\n")


def parse_charting_page(
    page_html: str,
    *,
    player_name: str,
    source_url: str,
    fetched_at: str,
) -> ChartingSnapshot | None:
    serve_fragment = _extract_js_html(page_html, "serve")
    serve_breakdown_fragment = _extract_js_html(page_html, "serve1")
    return_fragment = _extract_js_html(page_html, "return1")
    net_fragment = _extract_js_html(page_html, "netpts1")
    if serve_fragment is None or return_fragment is None:
        return None

    serve_rows = _parse_table_rows(_first_table(serve_fragment))
    serve_breakdown_rows = (
        _parse_table_rows(_first_table(serve_breakdown_fragment))
        if serve_breakdown_fragment is not None
        else {}
    )
    return_rows = _parse_table_rows(_first_table(return_fragment))
    net_rows = _parse_table_rows(_first_table(net_fragment)) if net_fragment is not None else {}

    all_serves = serve_rows.get("All Serves")
    first_serves = serve_rows.get("First Serves")
    second_serves = serve_rows.get("Second Serves")
    return_total = return_rows.get("Total")
    if not all_serves or not first_serves or not second_serves or not return_total:
        return None

    service_points = _parse_integer(all_serves[0])
    first_serve_points = _parse_integer(first_serves[0])
    second_serve_points = _parse_integer(second_serves[0])
    return_points = _parse_integer(return_total[0])
    if service_points <= 0 or first_serve_points <= 0 or second_serve_points <= 0 or return_points <= 0:
        return None

    first_serve_in = _first_serve_in_from_breakdown(serve_breakdown_rows)
    if first_serve_in is None:
        first_serve_in = first_serve_points / service_points

    wide_pct = _parse_count_percent(all_serves[6])[1]
    body_pct = _parse_count_percent(all_serves[7])[1]
    t_pct = _parse_count_percent(all_serves[8])[1]
    direction_mix = {
        "wide": wide_pct or 0.0,
        "body": body_pct or 0.0,
        "t": t_pct or 0.0,
    }

    net_approach_rate = None
    net_points_won = None
    net_row = net_rows.get("All Net Approaches")
    if net_row:
        net_approach_points = _parse_integer(net_row[0])
        total_points = service_points + return_points
        if total_points > 0:
            net_approach_rate = net_approach_points / total_points
        net_points_won = _parse_count_percent(net_row[1])[1]

    return ChartingSnapshot(
        player_id=player_id_from_name(player_name),
        player_name=player_name,
        source_url=source_url,
        fetched_at=fetched_at,
        charted_matches=_extract_match_count(page_html),
        service_points=service_points,
        return_points=return_points,
        first_serve_in=first_serve_in,
        first_serve_points_won=_parse_count_percent(first_serves[1])[1] or 0.0,
        second_serve_points_won=_parse_count_percent(second_serves[1])[1] or 0.0,
        ace_rate=_parse_count_percent(all_serves[2])[1] or 0.0,
        return_points_won=_parse_count_percent(return_total[1])[1] or 0.0,
        preferred_serve_direction=max(
            direction_mix.items(),
            key=lambda item: (item[1], item[0] == "wide", item[0] == "t"),
        )[0],
        net_approach_rate=net_approach_rate,
        net_points_won=net_points_won,
    )


def _extract_js_html(page_html: str, variable_name: str) -> str | None:
    match = re.search(rf"var\s+{re.escape(variable_name)}\s*=\s*'(.*?)';", page_html, re.S)
    if match is None:
        return None
    return html.unescape(match.group(1))


def _first_table(fragment: str) -> str:
    return fragment.split("</table>", 1)[0] + "</table>"


def _parse_table_rows(fragment: str) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for row_html in _TABLE_ROW_RE.findall(fragment):
        cells = [_clean_html(cell) for cell in _TABLE_CELL_RE.findall(row_html)]
        if cells:
            rows[cells[0]] = cells[1:]
    return rows


def _clean_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).replace("\xa0", " ").strip()


def _parse_integer(value: str) -> int:
    return int(re.sub(r"[^0-9]", "", value))


def _parse_count_percent(value: str) -> tuple[int | None, float | None]:
    match = _COUNT_PERCENT_RE.search(value)
    if match is None:
        return None, None
    count = int(match.group("count").replace(",", ""))
    pct_token = match.group("pct")
    pct = None if pct_token == "-" else float(pct_token) / 100.0
    return count, pct


def _extract_match_count(page_html: str) -> int | None:
    match = _MATCH_COUNT_RE.search(page_html)
    if match is None:
        return None
    return int(match.group(1))


def _first_serve_in_from_breakdown(rows: dict[str, list[str]]) -> float | None:
    total_points = 0
    total_first_in = 0
    for label in ("Deuce Court", "Ad Court"):
        row = rows.get(label)
        if not row or len(row) < 7:
            continue
        points = _parse_integer(row[0])
        first_in_count, _ = _parse_count_percent(row[6])
        if first_in_count is None or points <= 0:
            continue
        total_points += points
        total_first_in += first_in_count
    if total_points <= 0:
        return None
    return total_first_in / total_points
