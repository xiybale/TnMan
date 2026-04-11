from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .models import MatchConfig, Surface
from .roster import load_roster
from .simulator import MatchSimulator
from .web_payloads import (
    build_batch_payload,
    build_compare_payload,
    build_health_payload,
    build_match_report_payload,
    build_player_directory_payload,
    build_player_payload,
)


class MatchSimulationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_one: str = Field(alias="playerOne")
    player_two: str = Field(alias="playerTwo")
    surface: Surface = Surface.HARD
    best_of_sets: int = Field(default=3, alias="bestOfSets")
    seed: int = 1
    initial_server: str | None = Field(default=None, alias="initialServer")


class BatchSimulationRequest(MatchSimulationRequest):
    iterations: int = 100


def create_app(roster_path: str | Path | None = None) -> Any:
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError as exc:  # pragma: no cover - exercised only when web deps missing
        raise RuntimeError("Install the web extras first: python3 -m pip install -e '.[web]'") from exc

    roster = load_roster(roster_path)
    simulator = MatchSimulator(roster)
    app = FastAPI(
        title="Tennis Pro Manager API",
        version=__version__,
        description="Structured player and simulation API for the Tennis Pro Manager web UI.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def resolve_player(player_id: str):
        try:
            return roster[player_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown player id: {player_id}") from exc

    def build_config(request: MatchSimulationRequest) -> MatchConfig:
        try:
            return MatchConfig(
                surface=request.surface,
                best_of_sets=request.best_of_sets,
                initial_server=request.initial_server,
                seed=request.seed,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/health")
    def health() -> dict[str, Any]:
        return build_health_payload(roster)

    @app.get("/players")
    def players(q: str | None = None, surface: Surface | None = None) -> dict[str, Any]:
        return build_player_directory_payload(roster, query=q, surface=surface)

    @app.get("/players/{player_id}")
    def player_detail(player_id: str) -> dict[str, Any]:
        return build_player_payload(resolve_player(player_id))

    @app.get("/compare")
    def compare(player_one: str, player_two: str, surface: Surface = Surface.HARD) -> dict[str, Any]:
        return build_compare_payload(
            resolve_player(player_one),
            resolve_player(player_two),
            surface=surface,
        )

    @app.post("/simulate/match")
    def simulate_match(request: MatchSimulationRequest) -> dict[str, Any]:
        config = build_config(request)
        try:
            result = simulator.simulate_match(request.player_one, request.player_two, config)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return build_match_report_payload(result, roster)

    @app.post("/simulate/batch")
    def simulate_batch(request: BatchSimulationRequest) -> dict[str, Any]:
        config = build_config(request)
        if request.iterations <= 0:
            raise HTTPException(status_code=400, detail="iterations must be positive")
        try:
            result = simulator.simulate_batch(
                request.player_one,
                request.player_two,
                config,
                iterations=request.iterations,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return build_batch_payload(result, roster)

    return app
