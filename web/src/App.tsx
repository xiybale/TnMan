import { FormEvent, startTransition, useDeferredValue, useEffect, useState } from "react";

import { api } from "./api";
import type {
  BatchSummary,
  ComparePayload,
  GameEntry,
  MatchReport,
  MatchStats,
  PlayerDetail,
  PlayerSummary,
  PointEntry,
  SetEntry,
  Surface,
} from "./types";

const SURFACES: Surface[] = ["hard", "clay", "grass"];

export default function App() {
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [compareOneId, setCompareOneId] = useState<string>("");
  const [compareTwoId, setCompareTwoId] = useState<string>("");
  const [surface, setSurface] = useState<Surface>("hard");
  const [search, setSearch] = useState("");
  const [playerDetail, setPlayerDetail] = useState<PlayerDetail | null>(null);
  const [comparison, setComparison] = useState<ComparePayload | null>(null);
  const [matchReport, setMatchReport] = useState<MatchReport | null>(null);
  const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
  const [seed, setSeed] = useState(7);
  const [batchIterations, setBatchIterations] = useState(100);
  const [loadingRoster, setLoadingRoster] = useState(true);
  const [loadingPlayer, setLoadingPlayer] = useState(false);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [runningMatch, setRunningMatch] = useState(false);
  const [runningBatch, setRunningBatch] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const deferredSearch = useDeferredValue(search);
  const filteredPlayers = players.filter((player) => {
    const needle = deferredSearch.trim().toLowerCase();
    if (!needle) {
      return true;
    }
    return (
      player.name.toLowerCase().includes(needle) ||
      player.playerId.toLowerCase().includes(needle) ||
      player.country.toLowerCase().includes(needle)
    );
  });

  useEffect(() => {
    let cancelled = false;

    async function loadPlayers() {
      setLoadingRoster(true);
      setErrorMessage("");
      try {
        const payload = await api.players();
        if (cancelled) {
          return;
        }
        setPlayers(payload.players);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage((error as Error).message);
        }
      } finally {
        if (!cancelled) {
          setLoadingRoster(false);
        }
      }
    }

    void loadPlayers();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!players.length) {
      return;
    }
    if (!selectedPlayerId) {
      setSelectedPlayerId(players[0].playerId);
    }
    if (!compareOneId) {
      setCompareOneId(players[0].playerId);
    }
    if (!compareTwoId) {
      setCompareTwoId(players[1]?.playerId ?? players[0].playerId);
    }
  }, [players, selectedPlayerId, compareOneId, compareTwoId]);

  useEffect(() => {
    if (!selectedPlayerId) {
      return;
    }
    let cancelled = false;

    async function loadPlayer() {
      setLoadingPlayer(true);
      try {
        const payload = await api.player(selectedPlayerId);
        if (!cancelled) {
          setPlayerDetail(payload);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage((error as Error).message);
        }
      } finally {
        if (!cancelled) {
          setLoadingPlayer(false);
        }
      }
    }

    void loadPlayer();
    return () => {
      cancelled = true;
    };
  }, [selectedPlayerId]);

  useEffect(() => {
    if (!compareOneId || !compareTwoId || compareOneId === compareTwoId) {
      return;
    }
    let cancelled = false;

    async function loadComparison() {
      setLoadingCompare(true);
      try {
        const payload = await api.compare(compareOneId, compareTwoId, surface);
        if (!cancelled) {
          setComparison(payload);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage((error as Error).message);
        }
      } finally {
        if (!cancelled) {
          setLoadingCompare(false);
        }
      }
    }

    void loadComparison();
    return () => {
      cancelled = true;
    };
  }, [compareOneId, compareTwoId, surface]);

  async function handleMatchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!compareOneId || !compareTwoId) {
      return;
    }
    setRunningMatch(true);
    setErrorMessage("");
    try {
      const payload = await api.simulateMatch({
        playerOne: compareOneId,
        playerTwo: compareTwoId,
        surface,
        bestOfSets: 3,
        seed,
      });
      setMatchReport(payload);
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setRunningMatch(false);
    }
  }

  async function handleBatchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!compareOneId || !compareTwoId) {
      return;
    }
    setRunningBatch(true);
    setErrorMessage("");
    try {
      const payload = await api.simulateBatch({
        playerOne: compareOneId,
        playerTwo: compareTwoId,
        surface,
        bestOfSets: 3,
        seed,
        iterations: batchIterations,
      });
      setBatchSummary(payload);
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setRunningBatch(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="hero-panel">
        <div>
          <p className="eyebrow">Simulation Desk</p>
          <h1>Tennis Pro Manager</h1>
          <p className="hero-copy">
            Scoreboard-first analysis for ATP match simulation. Browse the roster, compare profiles,
            run seeded matches, and inspect point-by-point reports.
          </p>
        </div>
        <div className="surface-toggle">
          {SURFACES.map((item) => (
            <button
              key={item}
              type="button"
              className={item === surface ? "surface-chip is-active" : "surface-chip"}
              onClick={() => setSurface(item)}
            >
              {item}
            </button>
          ))}
        </div>
      </header>

      {errorMessage ? <div className="status-banner is-error">{errorMessage}</div> : null}

      <main className="dashboard-grid">
        <aside className="panel roster-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Roster</p>
              <h2>ATP Directory</h2>
            </div>
            <span className="panel-count">{players.length} players</span>
          </div>
          <label className="field">
            <span>Search</span>
            <input
              value={search}
              onChange={(event) => {
                const nextValue = event.target.value;
                startTransition(() => setSearch(nextValue));
              }}
              placeholder="Djokovic, Sinner, USA..."
            />
          </label>
          <div className="roster-list">
            {loadingRoster ? <p className="muted-copy">Loading roster...</p> : null}
            {filteredPlayers.map((player) => (
              <button
                key={player.playerId}
                type="button"
                className={player.playerId === selectedPlayerId ? "roster-row is-active" : "roster-row"}
                onClick={() => {
                  setSelectedPlayerId(player.playerId);
                  if (!compareOneId) {
                    setCompareOneId(player.playerId);
                  }
                }}
              >
                <div>
                  <strong>{player.name}</strong>
                  <span>
                    {player.country} · {player.handedness} · {player.backhandHands === 1 ? "1HBH" : "2HBH"}
                  </span>
                </div>
                <span className="rating-pill">{player.overallRating.toFixed(1)}</span>
              </button>
            ))}
          </div>
        </aside>

        <div className="content-column">
          <section className="panel spotlight-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Profile</p>
                <h2>Player Spotlight</h2>
              </div>
            </div>
            {loadingPlayer || !playerDetail ? (
              <p className="muted-copy">Loading player profile...</p>
            ) : (
              <div className="spotlight-grid">
                <div className="identity-card">
                  <div className="identity-topline">
                    <span className="country-badge">{playerDetail.summary.country}</span>
                    <span className="rating-pill">{playerDetail.summary.overallRating.toFixed(1)}</span>
                  </div>
                  <h3>{playerDetail.summary.name}</h3>
                  <p className="muted-copy">
                    {playerDetail.summary.handedness}-handed ·{" "}
                    {playerDetail.summary.backhandHands === 1 ? "one-handed backhand" : "two-handed backhand"}
                  </p>
                  <div className="tag-row">
                    {playerDetail.summary.tags.map((tag) => (
                      <span key={tag} className="tag">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="surface-bars">
                    {SURFACES.map((item) => (
                      <SkillBar
                        key={item}
                        label={`${item} comfort`}
                        value={playerDetail.surfaceProfile[item]}
                        accent={item}
                      />
                    ))}
                  </div>
                </div>

                <div className="skill-column">
                  <h3>Key Strengths</h3>
                  {playerDetail.strengths.map((entry) => (
                    <SkillBar key={entry.label} label={entry.label} value={entry.value} />
                  ))}
                </div>

                <div className="skill-column">
                  <h3>Skill Floor</h3>
                  {playerDetail.weaknesses.map((entry) => (
                    <SkillBar key={entry.label} label={entry.label} value={entry.value} muted />
                  ))}
                </div>
              </div>
            )}
          </section>

          <div className="content-split">
            <section className="panel compare-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Compare</p>
                  <h2>Matchup Profile</h2>
                </div>
              </div>

              <div className="compare-controls">
                <label className="field">
                  <span>Player One</span>
                  <select value={compareOneId} onChange={(event) => setCompareOneId(event.target.value)}>
                    {players.map((player) => (
                      <option key={player.playerId} value={player.playerId}>
                        {player.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Player Two</span>
                  <select value={compareTwoId} onChange={(event) => setCompareTwoId(event.target.value)}>
                    {players.map((player) => (
                      <option key={player.playerId} value={player.playerId}>
                        {player.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {loadingCompare || !comparison ? (
                <p className="muted-copy">Loading matchup...</p>
              ) : (
                <>
                  <div className="compare-headline">
                    <PlayerMiniCard player={comparison.playerOne.summary} />
                    <div className="surface-pill">{comparison.surface}</div>
                    <PlayerMiniCard player={comparison.playerTwo.summary} />
                  </div>

                  <div className="tag-row">
                    {comparison.matchupTags.map((tag) => (
                      <span key={tag} className="tag">
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="theme-list">
                    {comparison.tacticalThemes.map((theme) => (
                      <div key={`${theme.edgeFor}-${theme.label}`} className="theme-row">
                        <span>{summaryName(theme.edgeFor, comparison)}</span>
                        <span>{theme.label}</span>
                      </div>
                    ))}
                  </div>

                  <div className="compare-rows">
                    {comparison.skillDeltas.slice(0, 8).map((entry) => (
                      <CompareRow
                        key={entry.skill}
                        label={entry.label}
                        playerOneLabel={comparison.playerOne.summary.name}
                        playerTwoLabel={comparison.playerTwo.summary.name}
                        playerOneValue={entry.playerOne}
                        playerTwoValue={entry.playerTwo}
                      />
                    ))}
                  </div>
                </>
              )}
            </section>

            <section className="panel workbench-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Workbench</p>
                  <h2>Simulation Controls</h2>
                </div>
              </div>

              <form className="control-stack" onSubmit={handleMatchSubmit}>
                <label className="field">
                  <span>Seed</span>
                  <input
                    type="number"
                    value={seed}
                    onChange={(event) => setSeed(Number(event.target.value))}
                    min={1}
                  />
                </label>
                <button type="submit" className="action-button" disabled={runningMatch}>
                  {runningMatch ? "Running match..." : "Run single simulation"}
                </button>
              </form>

              <form className="control-stack" onSubmit={handleBatchSubmit}>
                <label className="field">
                  <span>Batch iterations</span>
                  <input
                    type="number"
                    value={batchIterations}
                    onChange={(event) => setBatchIterations(Number(event.target.value))}
                    min={10}
                  />
                </label>
                <button type="submit" className="action-button is-secondary" disabled={runningBatch}>
                  {runningBatch ? "Running batch..." : "Run batch simulation"}
                </button>
              </form>

              {batchSummary ? <BatchPanel batchSummary={batchSummary} /> : null}
            </section>
          </div>

          <section className="panel report-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Match Report</p>
                <h2>Scoreboard and Point Log</h2>
              </div>
            </div>
            {matchReport ? (
              <MatchReportPanel report={matchReport} />
            ) : (
              <p className="muted-copy">
                Run a single simulation to populate the live report view. The report renders per-set
                stats, game breakdowns, and point-by-point shot detail.
              </p>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function PlayerMiniCard({ player }: { player: PlayerSummary }) {
  return (
    <div className="mini-card">
      <strong>{player.name}</strong>
      <span>
        {player.country} · {player.handedness}
      </span>
    </div>
  );
}

function SkillBar({
  label,
  value,
  muted = false,
  accent,
}: {
  label: string;
  value: number;
  muted?: boolean;
  accent?: Surface;
}) {
  return (
    <div className="skill-bar">
      <div className="skill-bar-label">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className={muted ? "skill-track is-muted" : "skill-track"}>
        <span
          className={accent ? `skill-fill is-${accent}` : "skill-fill"}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

function CompareRow({
  label,
  playerOneLabel,
  playerTwoLabel,
  playerOneValue,
  playerTwoValue,
}: {
  label: string;
  playerOneLabel: string;
  playerTwoLabel: string;
  playerOneValue: number;
  playerTwoValue: number;
}) {
  return (
    <div className="compare-row">
      <div className="compare-header">
        <span>{label}</span>
        <span>
          {playerOneValue} / {playerTwoValue}
        </span>
      </div>
      <div className="compare-track">
        <div className="compare-side is-left" style={{ width: `${playerOneValue}%` }}>
          <span>{shortLabel(playerOneLabel)}</span>
        </div>
        <div className="compare-side is-right" style={{ width: `${playerTwoValue}%` }}>
          <span>{shortLabel(playerTwoLabel)}</span>
        </div>
      </div>
    </div>
  );
}

function BatchPanel({ batchSummary }: { batchSummary: BatchSummary }) {
  const [playerOneId, playerTwoId] = batchSummary.meta.players;
  const playerOne = batchSummary.players[playerOneId];
  const playerTwo = batchSummary.players[playerTwoId];

  return (
    <div className="batch-summary">
      <div className="score-strip">
        <div>
          <span className="eyebrow">Win rate</span>
          <strong>{playerOne.name}</strong>
          <p>{formatPercent(batchSummary.winRates[playerOneId])}</p>
        </div>
        <div className="score-divider">vs</div>
        <div>
          <span className="eyebrow">Win rate</span>
          <strong>{playerTwo.name}</strong>
          <p>{formatPercent(batchSummary.winRates[playerTwoId])}</p>
        </div>
      </div>
      <div className="metric-grid">
        <MetricTile label="Avg rally" value={batchSummary.meta.averageRallyLength.toFixed(2)} />
        <MetricTile label="Avg points/match" value={batchSummary.meta.averagePointsPerMatch.toFixed(1)} />
        <MetricTile label="P1 hold" value={formatPercent(batchSummary.holdRate[playerOneId])} />
        <MetricTile label="P2 hold" value={formatPercent(batchSummary.holdRate[playerTwoId])} />
      </div>
    </div>
  );
}

function MatchReportPanel({ report }: { report: MatchReport }) {
  const [playerOneId, playerTwoId] = report.meta.players;
  const playerOne = report.players[playerOneId];
  const playerTwo = report.players[playerTwoId];
  const playerOneStats = report.matchStats[playerOneId];
  const playerTwoStats = report.matchStats[playerTwoId];
  const patternSummary = report.patternSummary as {
    rallyBands?: Record<string, number>;
    players?: Record<string, { serveDirections?: Record<string, number>; serveSpins?: Record<string, number> }>;
  };

  return (
    <div className="report-stack">
      <div className="scoreboard">
        <div className={report.meta.winnerId === playerOneId ? "scorecard is-winner" : "scorecard"}>
          <span>{playerOne.country}</span>
          <strong>{playerOne.name}</strong>
          <p>{playerOneStats.totalPointsWon} pts won</p>
        </div>
        <div className="score-center">
          <p className="surface-pill">{report.meta.surface}</p>
          <h3>{report.meta.scoreline}</h3>
          <span>
            Seed {report.meta.seed} · Avg rally {report.meta.averageRallyLength.toFixed(2)}
          </span>
        </div>
        <div className={report.meta.winnerId === playerTwoId ? "scorecard is-winner" : "scorecard"}>
          <span>{playerTwo.country}</span>
          <strong>{playerTwo.name}</strong>
          <p>{playerTwoStats.totalPointsWon} pts won</p>
        </div>
      </div>

      <div className="metric-grid">
        <MetricTile label={`${shortLabel(playerOne.name)} 1st serve`} value={formatPercent(playerOneStats.firstServePercentage)} />
        <MetricTile label={`${shortLabel(playerTwo.name)} 1st serve`} value={formatPercent(playerTwoStats.firstServePercentage)} />
        <MetricTile label={`${shortLabel(playerOne.name)} break pts`} value={`${playerOneStats.breakPointsConverted}/${playerOneStats.breakPointsCreated}`} />
        <MetricTile label={`${shortLabel(playerTwo.name)} break pts`} value={`${playerTwoStats.breakPointsConverted}/${playerTwoStats.breakPointsCreated}`} />
      </div>

      {patternSummary.rallyBands ? (
        <div className="rally-band-panel">
          {Object.entries(patternSummary.rallyBands).map(([label, value]) => (
            <div key={label} className="rally-band">
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      ) : null}

      {report.sets.map((setEntry) => (
        <SetPanel
          key={setEntry.setNumber}
          setEntry={setEntry}
          players={report.players}
          playerOneId={playerOneId}
          playerTwoId={playerTwoId}
        />
      ))}
    </div>
  );
}

function SetPanel({
  setEntry,
  players,
  playerOneId,
  playerTwoId,
}: {
  setEntry: SetEntry;
  players: Record<string, PlayerSummary>;
  playerOneId: string;
  playerTwoId: string;
}) {
  const playerOneStats = setEntry.stats[playerOneId];
  const playerTwoStats = setEntry.stats[playerTwoId];

  return (
    <section className="set-panel">
      <div className="set-header">
        <div>
          <p className="eyebrow">Set {setEntry.setNumber}</p>
          <h3>{setEntry.score}</h3>
        </div>
        <div className="winner-badge">Winner: {players[setEntry.winnerId].name}</div>
      </div>

      <div className="set-stats-grid">
        <StatsStrip label={players[playerOneId].name} stats={playerOneStats} />
        <StatsStrip label={players[playerTwoId].name} stats={playerTwoStats} />
      </div>

      <div className="games-list">
        {setEntry.gamesTimeline.map((game) => (
          <GameDisclosure key={`${setEntry.setNumber}-${game.gameNumber}`} game={game} players={players} />
        ))}
      </div>
    </section>
  );
}

function StatsStrip({ label, stats }: { label: string; stats: MatchStats }) {
  return (
    <div className="stats-strip">
      <strong>{label}</strong>
      <div className="stats-strip-grid">
        <span>Aces {stats.aces}</span>
        <span>DF {stats.doubleFaults}</span>
        <span>1st In {formatPercent(stats.firstServePercentage)}</span>
        <span>Svc Won {formatPercent(stats.servicePointsWonPercentage)}</span>
        <span>Ret Won {formatPercent(stats.returnPointsWonPercentage)}</span>
        <span>W/UFE {stats.totalWinners}/{stats.unforcedErrors}</span>
      </div>
    </div>
  );
}

function GameDisclosure({
  game,
  players,
}: {
  game: GameEntry;
  players: Record<string, PlayerSummary>;
}) {
  return (
    <details className="game-disclosure">
      <summary>
        <div>
          <strong>
            Game {game.gameNumberInSet} · {game.scoreBefore} → {game.scoreAfter}
          </strong>
          <span>
            {players[game.serverId].name} serving · {game.holdsServe ? "hold" : "break"}
            {game.isTiebreak ? " · tiebreak" : ""}
          </span>
        </div>
        <span>{players[game.winnerId].name}</span>
      </summary>
      <div className="point-log">
        {game.points.map((point) => (
          <PointRow key={point.pointNumber} point={point} players={players} />
        ))}
      </div>
    </details>
  );
}

function PointRow({
  point,
  players,
}: {
  point: PointEntry;
  players: Record<string, PlayerSummary>;
}) {
  return (
    <details className="point-row">
      <summary>
        <div>
          <strong>
            P{point.pointNumber} · {point.pointScoreBefore} → {point.pointScoreAfter}
          </strong>
          <span>
            {players[point.winnerId].name} · {point.terminalOutcome.replaceAll("_", " ")} ·{" "}
            {point.rallyLength} shots
          </span>
        </div>
        <span className={`pressure-pill is-${point.pressureLabel}`}>{point.pressureLabel}</span>
      </summary>
      <div className="shot-list">
        <div className="point-meta-grid">
          <span>Score before: {point.scoreBefore}</span>
          <span>Score after: {point.scoreAfter}</span>
          <span>Pressure: {point.pressureIndex}</span>
          <span>
            Flags: {flagSummary(point)}
          </span>
        </div>
        {point.shots.map((shot) => (
          <div key={`${shot.pointNumber}-${shot.shotNumber}`} className="shot-row">
            <span>
              S{shot.shotNumber} · {players[shot.strikerId].name}
            </span>
            <span>
              {shot.shotKind} / {shot.shotHand} / {shot.spinType}
            </span>
            <span>{shot.outcome}</span>
          </div>
        ))}
      </div>
    </details>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function shortLabel(value: string) {
  const [first, last] = value.split(" ");
  if (!last) {
    return value;
  }
  return `${first[0]}. ${last}`;
}

function summaryName(playerId: string, comparison: ComparePayload) {
  if (comparison.playerOne.summary.playerId === playerId) {
    return comparison.playerOne.summary.name;
  }
  return comparison.playerTwo.summary.name;
}

function flagSummary(point: PointEntry) {
  const flags = [];
  if (point.breakPointFor) {
    flags.push("break point");
  }
  if (point.setPointFor) {
    flags.push("set point");
  }
  if (point.matchPointFor) {
    flags.push("match point");
  }
  return flags.length ? flags.join(", ") : "routine";
}
