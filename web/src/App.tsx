import { FormEvent, startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { api } from "./api";
import type {
  BatchSummary,
  ComparePayload,
  GameEntry,
  MatchReport,
  MatchStats,
  PatternSummaryPlayer,
  PlayerDetail,
  PlayerSummary,
  PointEntry,
  RecentSimulation,
  SetEntry,
  Surface,
} from "./types";

const SURFACES: Surface[] = ["hard", "clay", "grass"];
const BEST_OF_OPTIONS = [3, 5] as const;
const SKILL_LABELS: Record<string, string> = {
  servePower: "Serve power",
  serveAccuracy: "Serve accuracy",
  secondServeReliability: "Second serve reliability",
  returnQuality: "Return quality",
  forehandQuality: "Forehand quality",
  backhandQuality: "Backhand quality",
  movement: "Movement",
  anticipation: "Anticipation",
  rallyTolerance: "Rally tolerance",
  netPlay: "Net play",
  composure: "Composure",
  pressureHandling: "Pressure handling",
  stamina: "Stamina",
};

const RADAR_GROUPS: Array<{ key: string; label: string; skills: string[] }> = [
  { key: "technique", label: "Technique", skills: ["forehandQuality", "backhandQuality", "netPlay"] },
  { key: "movement", label: "Movement", skills: ["movement", "anticipation", "stamina"] },
  { key: "serve", label: "Serve", skills: ["servePower", "serveAccuracy", "secondServeReliability"] },
  { key: "return", label: "Return", skills: ["returnQuality", "anticipation"] },
  { key: "mental", label: "Mental", skills: ["composure", "pressureHandling", "rallyTolerance"] },
  { key: "rally", label: "Rally", skills: ["rallyTolerance", "forehandQuality", "backhandQuality"] },
];

const SKILL_GROUPS: Array<{ key: string; label: string; skills: string[] }> = [
  {
    key: "technical",
    label: "Technical",
    skills: ["servePower", "serveAccuracy", "secondServeReliability", "returnQuality", "forehandQuality", "backhandQuality", "netPlay"],
  },
  {
    key: "mental",
    label: "Mental",
    skills: ["composure", "pressureHandling", "anticipation", "rallyTolerance"],
  },
  {
    key: "physical",
    label: "Physical",
    skills: ["movement", "stamina"],
  },
];

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
  const [isMatchReportOpen, setIsMatchReportOpen] = useState(false);
  const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
  const [seed, setSeed] = useState(7);
  const [bestOfSets, setBestOfSets] = useState<3 | 5>(3);
  const [batchIterations, setBatchIterations] = useState(100);
  const [initialServerId, setInitialServerId] = useState<string>("");
  const [loadingRoster, setLoadingRoster] = useState(true);
  const [loadingPlayer, setLoadingPlayer] = useState(false);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [runningMatch, setRunningMatch] = useState(false);
  const [runningBatch, setRunningBatch] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [recentSimulations, setRecentSimulations] = useState<RecentSimulation[]>([]);

  const deferredSearch = useDeferredValue(search);
  const rosterCountLabel = loadingRoster ? "Loading..." : `${players.length} players`;
  const sortedPlayers = useMemo(
    () => [...players].sort((left, right) => {
      const ratingDelta = right.overallRating - left.overallRating;
      if (ratingDelta !== 0) {
        return ratingDelta;
      }
      const surfaceDelta = (right.surfaceComfort[surface] ?? 0) - (left.surfaceComfort[surface] ?? 0);
      if (surfaceDelta !== 0) {
        return surfaceDelta;
      }
      return left.name.localeCompare(right.name);
    }),
    [players, surface],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadPlayers() {
      setLoadingRoster(true);
      setErrorMessage("");
      try {
        const payload = await api.players({ q: deferredSearch, surface });
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
  }, [deferredSearch, surface]);

  useEffect(() => {
    if (!sortedPlayers.length) {
      return;
    }

    if (!sortedPlayers.some((player) => player.playerId === selectedPlayerId)) {
      setSelectedPlayerId(sortedPlayers[0].playerId);
    }
    if (!sortedPlayers.some((player) => player.playerId === compareOneId)) {
      setCompareOneId(sortedPlayers[0].playerId);
    }
    if (!sortedPlayers.some((player) => player.playerId === compareTwoId)) {
      setCompareTwoId(sortedPlayers[1]?.playerId ?? sortedPlayers[0].playerId);
    }
  }, [sortedPlayers, selectedPlayerId, compareOneId, compareTwoId]);

  useEffect(() => {
    if (!compareOneId || !compareTwoId) {
      return;
    }
    if (initialServerId && [compareOneId, compareTwoId].includes(initialServerId)) {
      return;
    }
    setInitialServerId(compareOneId);
  }, [compareOneId, compareTwoId, initialServerId]);

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
      setComparison(null);
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

  const comparePlayers = useMemo(
    () => [sortedPlayers.find((player) => player.playerId === compareOneId), sortedPlayers.find((player) => player.playerId === compareTwoId)],
    [sortedPlayers, compareOneId, compareTwoId],
  );

  function pushRecent(entry: RecentSimulation) {
    setRecentSimulations((current) => [entry, ...current.filter((item) => item.id !== entry.id)].slice(0, 6));
  }

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
        bestOfSets,
        seed,
        initialServer: initialServerId,
      });
      setMatchReport(payload);
      setIsMatchReportOpen(true);
      const [playerOneId, playerTwoId] = payload.meta.players;
      pushRecent({
        id: `match:${playerOneId}:${playerTwoId}:${surface}:${seed}:${bestOfSets}`,
        kind: "match",
        label: `${payload.players[playerOneId].name} vs ${payload.players[playerTwoId].name}`,
        meta: `${surface} · best of ${bestOfSets} · ${payload.meta.scoreline}`,
      });
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
        bestOfSets,
        seed,
        iterations: batchIterations,
        initialServer: initialServerId,
      });
      setBatchSummary(payload);
      const [playerOneId, playerTwoId] = payload.meta.players;
      pushRecent({
        id: `batch:${playerOneId}:${playerTwoId}:${surface}:${seed}:${bestOfSets}:${batchIterations}`,
        kind: "batch",
        label: `${payload.players[playerOneId].name} vs ${payload.players[playerTwoId].name}`,
        meta: `${surface} · ${batchIterations} sims · ${formatPercent(payload.winRates[playerOneId])} / ${formatPercent(payload.winRates[playerTwoId])}`,
      });
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
            Premium, scoreboard-first analysis for ATP match simulation. Browse the roster, compare
            profiles, run seeded matches, and inspect structured point-by-point reports.
          </p>
        </div>
        <div className="hero-actions">
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
          <div className="hero-meta-card">
            <span>Surface context updates roster, compare, and simulations together.</span>
          </div>
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
            <span className="panel-count">{rosterCountLabel}</span>
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
            {!loadingRoster && !sortedPlayers.length ? <p className="muted-copy">No players match this filter.</p> : null}
            {sortedPlayers.map((player, index) => (
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
                  <strong>#{index + 1} · {player.name}</strong>
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
                <div className="identity-card spotlight-identity-card">
                  <div className="identity-topline">
                    <span className="country-badge">{playerDetail.summary.country}</span>
                    <span className="rating-pill">{playerDetail.summary.overallRating.toFixed(1)}</span>
                  </div>
                  <h3>{playerDetail.summary.name}</h3>
                  <p className="muted-copy">
                    {playerDetail.summary.handedness}-handed · {playerDetail.summary.backhandHands === 1 ? "one-handed" : "two-handed"} backhand
                  </p>
                  <div className="tag-row">
                    {playerDetail.summary.tags.map((tag) => (
                      <span key={tag} className="tag">{tag}</span>
                    ))}
                  </div>
                </div>

                <div className="spotlight-lower-grid">
                  <div className="skill-column skill-column-wide">
                    <div className="subsection-header compact-header">
                      <h3>All Skills</h3>
                      <span className="panel-count">Grouped and complete</span>
                    </div>
                    <div className="skill-list dense-skill-list">
                      {skillGroups(playerDetail.skills).map((group) => (
                        <div key={group.key} className="skill-group compact-skill-group">
                          <p className="eyebrow">{group.label}</p>
                          <div className="skill-grid">
                            {group.entries.map((entry) => (
                              <SkillValue key={entry.key} label={entry.label} value={entry.value} />
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="skill-column">
                    <div className="subsection-header compact-header">
                      <h3>Tactics</h3>
                    </div>
                    <div className="skill-list tactics-stack">
                      <div className="skill-group compact-skill-group">
                        <p className="eyebrow">Tactical profile</p>
                        <div className="skill-grid secondary-skill-grid">
                          <SkillValue label="Baseline aggression" value={playerDetail.tactics.baselineAggression} />
                          <SkillValue label="Short-ball attack" value={playerDetail.tactics.shortBallAttack} />
                          <SkillValue label="Net frequency" value={playerDetail.tactics.netFrequency} />
                        </div>
                      </div>

                      <div className="skill-group compact-skill-group">
                        <p className="eyebrow">Surface comfort</p>
                        <div className="skill-grid secondary-skill-grid">
                          {SURFACES.map((item) => (
                            <SkillValue
                              key={item}
                              label={`${item[0].toUpperCase()}${item.slice(1)}`}
                              value={playerDetail.surfaceProfile[item]}
                            />
                          ))}
                        </div>
                      </div>

                      <div className="skill-group compact-skill-group">
                        <p className="eyebrow">Conditioning</p>
                        <div className="skill-grid secondary-skill-grid">
                          <SkillValue label="Recovery" value={playerDetail.physical.recovery} muted />
                          <SkillValue label="Durability" value={playerDetail.physical.durability} muted />
                          <SkillValue label="Peak condition" value={playerDetail.physical.peakCondition} muted />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="skill-column radar-column">
                    <div className="subsection-header compact-header">
                      <h3>Profile Radar</h3>
                      <span className="panel-count">Grouped categories</span>
                    </div>
                    <RadarChart detail={playerDetail} />
                  </div>
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
                      <option key={player.playerId} value={player.playerId}>{player.name}</option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Player Two</span>
                  <select value={compareTwoId} onChange={(event) => setCompareTwoId(event.target.value)}>
                    {players.map((player) => (
                      <option key={player.playerId} value={player.playerId}>{player.name}</option>
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

                  <div className="metric-grid compact-grid">
                    <MetricTile label={`${shortLabel(comparison.playerOne.summary.name)} surface`} value={comparison.surfaceEdge.playerOne.toFixed(0)} />
                    <MetricTile label={`${shortLabel(comparison.playerTwo.summary.name)} surface`} value={comparison.surfaceEdge.playerTwo.toFixed(0)} />
                    <MetricTile label="Surface delta" value={comparison.surfaceEdge.delta.toFixed(1)} />
                  </div>

                  <div className="tag-row">
                    {comparison.matchupTags.map((tag) => (
                      <span key={tag} className="tag">{tag}</span>
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
                <div className="form-grid">
                  <label className="field">
                    <span>Format</span>
                    <select value={bestOfSets} onChange={(event) => setBestOfSets(Number(event.target.value) as 3 | 5)}>
                      {BEST_OF_OPTIONS.map((value) => (
                        <option key={value} value={value}>Best of {value}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Seed</span>
                    <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} min={1} />
                  </label>
                  <label className="field field-full">
                    <span>Initial server</span>
                    <select value={initialServerId} onChange={(event) => setInitialServerId(event.target.value)}>
                      {comparePlayers.filter(Boolean).map((player) => (
                        <option key={player!.playerId} value={player!.playerId}>{player!.name}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <button type="submit" className="action-button" disabled={runningMatch || compareOneId === compareTwoId}>
                  {runningMatch ? "Running match..." : "Run single simulation"}
                </button>
              </form>

              <form className="control-stack" onSubmit={handleBatchSubmit}>
                <label className="field">
                  <span>Batch iterations</span>
                  <input type="number" value={batchIterations} onChange={(event) => setBatchIterations(Number(event.target.value))} min={10} />
                </label>
                <button type="submit" className="action-button is-secondary" disabled={runningBatch || compareOneId === compareTwoId}>
                  {runningBatch ? "Running batch..." : "Run batch simulation"}
                </button>
              </form>

              {recentSimulations.length ? (
                <div className="recent-panel">
                  <div className="subsection-header">
                    <h3>Recent simulations</h3>
                  </div>
                  <div className="recent-list">
                    {recentSimulations.map((entry) => (
                      <div key={entry.id} className="recent-row">
                        <strong>{entry.label}</strong>
                        <span>{entry.meta}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {batchSummary ? <BatchPanel batchSummary={batchSummary} /> : null}
            </section>
          </div>

          <section className="panel report-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Match Report</p>
                <h2>Flashscore-style breakdown</h2>
              </div>
              {matchReport ? (
                <button type="button" className="action-button" onClick={() => setIsMatchReportOpen(true)}>
                  Open report view
                </button>
              ) : null}
            </div>
            {matchReport ? (
              <MatchReportPreview report={matchReport} onOpen={() => setIsMatchReportOpen(true)} />
            ) : (
              <p className="muted-copy">
                Run a single simulation to unlock the full-screen match report with overall stats,
                per-set breakdowns, patterns, and point-by-point drilldown.
              </p>
            )}
          </section>
         {matchReport && isMatchReportOpen ? <MatchReportModal report={matchReport} onClose={() => setIsMatchReportOpen(false)} /> : null}
        </div>
      </main>
    </div>
  );
}

function PlayerMiniCard({ player }: { player: PlayerSummary }) {
  return (
    <div className="mini-card">
      <strong>{player.name}</strong>
      <span>{player.country} · {player.handedness}</span>
    </div>
  );
}

function SkillBar({ label, value, muted = false, accent }: { label: string; value: number; muted?: boolean; accent?: Surface }) {
  return (
    <div className="skill-bar">
      <div className="skill-bar-label">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className={muted ? "skill-track is-muted" : "skill-track"}>
        <span className={accent ? `skill-fill is-${accent}` : "skill-fill"} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function SkillValue({ label, value, muted = false }: { label: string; value: number; muted?: boolean }) {
  const valueClassName = value >= 90 ? "skill-value-score is-elite" : "skill-value-score";

  return (
    <div className={muted ? "skill-value is-muted" : "skill-value"}>
      <span className="skill-value-label">{label}</span>
      <strong className={valueClassName}>{value}</strong>
    </div>
  );
}

function RadarChart({ detail }: { detail: PlayerDetail }) {
  const size = 320;
  const center = size / 2;
  const radius = 112;
  const levels = [0.25, 0.5, 0.75, 1];
  const series = radarSeries(detail.skills);
  const points = series.map((entry, index) => polarPoint(index, series.length, center, radius * (entry.value / 100)));
  const polygon = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="radar-shell">
      <svg viewBox={`0 0 ${size} ${size}`} className="radar-chart" role="img" aria-label="Grouped skill radar chart">
        {levels.map((level) => {
          const ring = series.map((_, index) => {
            const point = polarPoint(index, series.length, center, radius * level);
            return `${point.x},${point.y}`;
          }).join(" ");
          return <polygon key={level} points={ring} className="radar-ring" />;
        })}
        {series.map((entry, index) => {
          const outer = polarPoint(index, series.length, center, radius);
          return <line key={entry.key} x1={center} y1={center} x2={outer.x} y2={outer.y} className="radar-axis" />;
        })}
        <polygon points={polygon} className="radar-shape" />
        {points.map((point, index) => (
          <circle key={series[index].key} cx={point.x} cy={point.y} r="4" className="radar-dot" />
        ))}
        {series.map((entry, index) => {
          const labelPoint = polarPoint(index, series.length, center, radius + 24);
          return (
            <text key={entry.key} x={labelPoint.x} y={labelPoint.y} className="radar-label" textAnchor={labelPoint.anchor} dominantBaseline="middle">
              {entry.label}
            </text>
          );
        })}
      </svg>
      <div className="radar-legend">
        {series.map((entry) => (
          <div key={entry.key} className="radar-legend-row">
            <span>{entry.label}</span>
            <strong>{entry.value}</strong>
          </div>
        ))}
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
        <span>{playerOneValue} / {playerTwoValue}</span>
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
  const commonScorelines = Object.entries(batchSummary.commonScorelines).slice(0, 5);
  const rallyBands = Object.entries(batchSummary.rallyBandDistribution);

  return (
    <div className="batch-summary">
      <div className="subsection-header">
        <h3>Batch dashboard</h3>
        <span className="panel-count">{batchSummary.meta.iterations} sims</span>
      </div>
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
        <MetricTile label="P1 return" value={formatPercent(batchSummary.returnPointsWonRate[playerOneId])} />
        <MetricTile label="P2 return" value={formatPercent(batchSummary.returnPointsWonRate[playerTwoId])} />
      </div>
      <div className="distribution-grid">
        <div className="distribution-panel">
          <div className="subsection-header"><h3>Common scorelines</h3></div>
          {commonScorelines.map(([label, value]) => (
            <DataBar key={label} label={label} value={value} max={commonScorelines[0]?.[1] ?? 1} />
          ))}
        </div>
        <div className="distribution-panel">
          <div className="subsection-header"><h3>Rally bands</h3></div>
          {rallyBands.map(([label, value]) => (
            <DataBar key={label} label={label} value={value} max={Math.max(...rallyBands.map(([, amount]) => amount), 1)} />
          ))}
        </div>
      </div>
    </div>
  );
}

function MatchReportPreview({ report, onOpen }: { report: MatchReport; onOpen: () => void }) {
  const [playerOneId, playerTwoId] = report.meta.players;
  const playerOne = report.players[playerOneId];
  const playerTwo = report.players[playerTwoId];
  const playerOneStats = report.matchStats[playerOneId];
  const playerTwoStats = report.matchStats[playerTwoId];

  return (
    <button type="button" className="report-preview-card" onClick={onOpen}>
      <div className="scoreboard report-preview-scoreboard">
        <div className={report.meta.winnerId === playerOneId ? "scorecard is-winner" : "scorecard"}>
          <span>{playerOne.country}</span>
          <strong>{playerOne.name}</strong>
          <p>{playerOneStats.totalPointsWon} pts won</p>
        </div>
        <div className="score-center">
          <p className="surface-pill">{report.meta.surface}</p>
          <h3>{report.meta.scoreline}</h3>
          <span>{report.sets.length} sets · {report.meta.totalPoints} points</span>
        </div>
        <div className={report.meta.winnerId === playerTwoId ? "scorecard is-winner" : "scorecard"}>
          <span>{playerTwo.country}</span>
          <strong>{playerTwo.name}</strong>
          <p>{playerTwoStats.totalPointsWon} pts won</p>
        </div>
      </div>
      <div className="metric-grid compact-grid">
        <MetricTile label={`${shortLabel(playerOne.name)} winners`} value={`${playerOneStats.totalWinners}`} />
        <MetricTile label={`${shortLabel(playerTwo.name)} winners`} value={`${playerTwoStats.totalWinners}`} />
        <MetricTile label="View" value="Open full report" />
      </div>
    </button>
  );
}

function MatchReportModal({ report, onClose }: { report: MatchReport; onClose: () => void }) {
  const [activeView, setActiveView] = useState("overview");
  const [playerOneId, playerTwoId] = report.meta.players;
  const playerOne = report.players[playerOneId];
  const playerTwo = report.players[playerTwoId];
  const patternPlayers = report.patternSummary.players ?? {};
  const activeSet = report.sets.find((setEntry) => `set-${setEntry.setNumber}` === activeView);

  return (
    <div className="report-modal-backdrop" role="presentation" onClick={onClose}>
      <section className="report-modal" role="dialog" aria-modal="true" aria-label="Match report" onClick={(event) => event.stopPropagation()}>
        <div className="report-modal-header">
          <div>
            <p className="eyebrow">Match report</p>
            <h2>{playerOne.name} vs {playerTwo.name}</h2>
          </div>
          <div className="report-modal-actions">
            <div className="report-tab-strip" role="tablist" aria-label="Report sections">
              {[
                { key: "overview", label: "Overview" },
                ...report.sets.map((setEntry) => ({ key: `set-${setEntry.setNumber}`, label: `Set ${setEntry.setNumber}` })),
                { key: "points", label: "Point log" },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={activeView === key}
                  className={activeView === key ? "surface-chip is-active" : "surface-chip"}
                  onClick={() => setActiveView(key)}
                >
                  {label}
                </button>
              ))}
            </div>
            <button type="button" className="action-button is-secondary" onClick={onClose}>Close</button>
          </div>
        </div>

        <div className="report-stack report-modal-body">
          <div className="scoreboard">
            <div className={report.meta.winnerId === playerOneId ? "scorecard is-winner" : "scorecard"}>
              <span>{playerOne.country}</span>
              <strong>{playerOne.name}</strong>
              <p>{report.matchStats[playerOneId].totalPointsWon} pts won</p>
            </div>
            <div className="score-center">
              <p className="surface-pill">{report.meta.surface}</p>
              <h3>{report.meta.scoreline}</h3>
              <span>Seed {report.meta.seed} · Best of {report.meta.bestOfSets} · Avg rally {report.meta.averageRallyLength.toFixed(2)}</span>
            </div>
            <div className={report.meta.winnerId === playerTwoId ? "scorecard is-winner" : "scorecard"}>
              <span>{playerTwo.country}</span>
              <strong>{playerTwo.name}</strong>
              <p>{report.matchStats[playerTwoId].totalPointsWon} pts won</p>
            </div>
          </div>

          {activeView === "overview" ? (
            <>
              <div className="metric-grid">
                <MetricTile label="Total points" value={`${report.meta.totalPoints}`} />
                <MetricTile label="Average rally" value={report.meta.averageRallyLength.toFixed(2)} />
                <MetricTile label={`${shortLabel(playerOne.name)} sets`} value={`${report.sets.filter((setEntry) => setEntry.winnerId === playerOneId).length}`} />
                <MetricTile label={`${shortLabel(playerTwo.name)} sets`} value={`${report.sets.filter((setEntry) => setEntry.winnerId === playerTwoId).length}`} />
              </div>
              <StatsMatrix title="Overall match stats" leftPlayer={playerOne} rightPlayer={playerTwo} leftStats={report.matchStats[playerOneId]} rightStats={report.matchStats[playerTwoId]} />
              {report.patternSummary.rallyBands ? (
                <div className="distribution-panel">
                  <div className="subsection-header"><h3>Rally length bands</h3></div>
                  {Object.entries(report.patternSummary.rallyBands).map(([label, value]) => (
                    <DataBar key={label} label={label} value={value} max={Math.max(...Object.values(report.patternSummary.rallyBands ?? {}), 1)} />
                  ))}
                </div>
              ) : null}
              <div className="distribution-grid">
                {[playerOneId, playerTwoId].map((playerId) => (
                  <PatternPanel key={playerId} player={report.players[playerId]} pattern={patternPlayers[playerId]} />
                ))}
              </div>
            </>
          ) : null}

          {activeSet ? (
            <SetPanel setEntry={activeSet} players={report.players} playerOneId={playerOneId} playerTwoId={playerTwoId} />
          ) : null}

          {activeView === "points" ? (
            <div className="report-stack">
              {report.sets.map((setEntry) => (
                <section key={setEntry.setNumber} className="set-panel">
                  <div className="set-header">
                    <div>
                      <p className="eyebrow">Set {setEntry.setNumber}</p>
                      <h3>{setEntry.score}</h3>
                    </div>
                    <div className="winner-badge">Winner: {report.players[setEntry.winnerId].name}</div>
                  </div>
                  <div className="games-list">
                    {setEntry.gamesTimeline.map((game) => (
                      <GameDisclosure key={`${setEntry.setNumber}-${game.gameNumber}`} game={game} players={report.players} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function SetPanel({ setEntry, players, playerOneId, playerTwoId }: { setEntry: SetEntry; players: Record<string, PlayerSummary>; playerOneId: string; playerTwoId: string }) {
  const playerOneStats = setEntry.stats[playerOneId];
  const playerTwoStats = setEntry.stats[playerTwoId];

  return (
    <section className="set-panel">
      <div className="set-header">
        <div>
          <p className="eyebrow">Set {setEntry.setNumber}</p>
          <h3>{setEntry.score}</h3>
          {setEntry.tiebreakPoints ? <span className="muted-copy">Tiebreak: {Object.values(setEntry.tiebreakPoints).join("-")}</span> : null}
        </div>
        <div className="winner-badge">Winner: {players[setEntry.winnerId].name}</div>
      </div>

      <StatsMatrix title={`Set ${setEntry.setNumber} stats`} leftPlayer={players[playerOneId]} rightPlayer={players[playerTwoId]} leftStats={playerOneStats} rightStats={playerTwoStats} />
    </section>
  );
}

function StatsMatrix({ title, leftPlayer, rightPlayer, leftStats, rightStats }: { title: string; leftPlayer: PlayerSummary; rightPlayer: PlayerSummary; leftStats: MatchStats; rightStats: MatchStats }) {
  return (
    <section className="distribution-panel stats-matrix-panel">
      <div className="subsection-header"><h3>{title}</h3></div>
      <div className="stats-matrix-header">
        <strong>{leftPlayer.name}</strong>
        <span>Stat</span>
        <strong>{rightPlayer.name}</strong>
      </div>
      <div className="stats-matrix">
        {statsRows(leftStats, rightStats).map((row) => (
          <div key={row.label} className="stats-matrix-row">
            <strong>{row.left}</strong>
            <span>{row.label}</span>
            <strong>{row.right}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function PatternPanel({ player, pattern }: { player: PlayerSummary; pattern: PatternSummaryPlayer | undefined }) {
  const groups = [
    ["Serve directions", pattern?.serveDirections],
    ["Serve spins", pattern?.serveSpins],
    ["Targeted wings", pattern?.targetedWings],
    ["Rally spins", pattern?.rallySpins],
    ["Winners by hand", pattern?.winnersByHand],
    ["Forced errors by hand", pattern?.forcedErrorsByHand],
    ["Unforced errors by hand", pattern?.unforcedErrorsByHand],
  ].filter(([, values]) => values && Object.keys(values).length) as Array<[string, Record<string, number>]>;

  if (!groups.length) {
    return null;
  }

  return (
    <div className="distribution-panel">
      <div className="subsection-header"><h3>{player.name} patterns</h3></div>
      <div className="report-stack">
        {groups.map(([label, values]) => {
          const entries = Object.entries(values);
          const max = Math.max(...entries.map(([, value]) => value), 1);
          return (
            <div key={label} className="report-stack">
              <strong>{label}</strong>
              {entries.map(([entryLabel, value]) => (
                <DataBar key={entryLabel} label={entryLabel} value={value} max={max} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GameDisclosure({ game, players }: { game: GameEntry; players: Record<string, PlayerSummary> }) {
  return (
    <details className="game-disclosure">
      <summary>
        <div>
          <strong>Game {game.gameNumberInSet} · {game.scoreBefore} → {game.scoreAfter}</strong>
          <span>{players[game.serverId].name} serving · {game.holdsServe ? "hold" : "break"}{game.isTiebreak ? " · tiebreak" : ""}</span>
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

function PointRow({ point, players }: { point: PointEntry; players: Record<string, PlayerSummary> }) {
  return (
    <details className="point-row">
      <summary>
        <div>
          <strong>P{point.pointNumber} · {point.pointScoreBefore} → {point.pointScoreAfter}</strong>
          <span>{players[point.winnerId].name} · {point.terminalOutcome.replaceAll("_", " ")} · {point.rallyLength} shots</span>
        </div>
        <span className={`pressure-pill is-${point.pressureLabel}`}>{point.pressureLabel}</span>
      </summary>
      <div className="shot-list">
        <div className="point-meta-grid">
          <span>Score before: {point.scoreBefore}</span>
          <span>Score after: {point.scoreAfter}</span>
          <span>Pressure: {point.pressureIndex}</span>
          <span>Flags: {flagSummary(point)}</span>
        </div>
        {point.shots.map((shot) => (
          <div key={`${shot.pointNumber}-${shot.shotNumber}`} className="shot-row">
            <span>S{shot.shotNumber} · {players[shot.strikerId].name}</span>
            <span>{shot.shotKind} / {shot.shotHand} / {shot.spinType}</span>
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

function DataBar({ label, value, max }: { label: string; value: number; max: number }) {
  const width = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="data-bar-row">
      <div className="data-bar-label"><span>{label}</span><strong>{value}</strong></div>
      <div className="data-bar-track"><span className="data-bar-fill" style={{ width: `${width}%` }} /></div>
    </div>
  );
}

function statsRows(leftStats: MatchStats, rightStats: MatchStats) {
  return [
    ["Points won", leftStats.totalPointsWon, rightStats.totalPointsWon],
    ["Points played", leftStats.pointsPlayed, rightStats.pointsPlayed],
    ["Service points won", `${leftStats.servicePointsWon}/${leftStats.servicePointsPlayed}`, `${rightStats.servicePointsWon}/${rightStats.servicePointsPlayed}`],
    ["Return points won", `${leftStats.returnPointsWon}/${leftStats.returnPointsPlayed}`, `${rightStats.returnPointsWon}/${rightStats.returnPointsPlayed}`],
    ["Aces", leftStats.aces, rightStats.aces],
    ["Service winners", leftStats.serviceWinners, rightStats.serviceWinners],
    ["Double faults", leftStats.doubleFaults, rightStats.doubleFaults],
    ["Winners", leftStats.winners, rightStats.winners],
    ["Return winners", leftStats.returnWinners, rightStats.returnWinners],
    ["Forced errors drawn", leftStats.forcedErrorsDrawn, rightStats.forcedErrorsDrawn],
    ["Unforced errors", leftStats.unforcedErrors, rightStats.unforcedErrors],
    ["Break points", `${leftStats.breakPointsConverted}/${leftStats.breakPointsCreated}`, `${rightStats.breakPointsConverted}/${rightStats.breakPointsCreated}`],
    ["Break points saved", `${leftStats.breakPointsSaved}/${leftStats.breakPointsFaced}`, `${rightStats.breakPointsSaved}/${rightStats.breakPointsFaced}`],
    ["Games served", leftStats.gamesServed, rightStats.gamesServed],
    ["Service games won", leftStats.serviceGamesWon, rightStats.serviceGamesWon],
    ["Total shots", leftStats.totalShots, rightStats.totalShots],
    ["First serves", `${leftStats.firstServesIn}/${leftStats.firstServeAttempts}`, `${rightStats.firstServesIn}/${rightStats.firstServeAttempts}`],
    ["Second serves in", `${leftStats.secondServesIn}/${leftStats.secondServeAttempts}`, `${rightStats.secondServesIn}/${rightStats.secondServeAttempts}`],
    ["Total winners", leftStats.totalWinners, rightStats.totalWinners],
    ["1st serve %", formatPercent(leftStats.firstServePercentage), formatPercent(rightStats.firstServePercentage)],
    ["Service points won %", formatPercent(leftStats.servicePointsWonPercentage), formatPercent(rightStats.servicePointsWonPercentage)],
    ["Return points won %", formatPercent(leftStats.returnPointsWonPercentage), formatPercent(rightStats.returnPointsWonPercentage)],
    ["Hold %", formatPercent(leftStats.holdPercentage), formatPercent(rightStats.holdPercentage)],
    ["Ace rate", formatPercent(leftStats.aceRate), formatPercent(rightStats.aceRate)],
    ["Double fault rate", formatPercent(leftStats.doubleFaultRate), formatPercent(rightStats.doubleFaultRate)],
    ["2nd serve DF rate", formatPercent(leftStats.secondServeDoubleFaultRate), formatPercent(rightStats.secondServeDoubleFaultRate)],
    ["Winner/error ratio", leftStats.winnerToErrorRatio.toFixed(2), rightStats.winnerToErrorRatio.toFixed(2)],
  ].map(([label, left, right]) => ({ label, left: String(left), right: String(right) }));
}

function skillGroups(skills: PlayerDetail["skills"]) {
  return SKILL_GROUPS.map((group) => ({
    key: group.key,
    label: group.label,
    entries: group.skills.map((key) => ({
      key,
      label: SKILL_LABELS[key] ?? startCase(key),
      value: skills[key] ?? 0,
    })),
  }));
}

function radarSeries(skills: PlayerDetail["skills"]) {
  return RADAR_GROUPS.map((group) => {
    const total = group.skills.reduce((sum, key) => sum + (skills[key] ?? 0), 0);
    return {
      key: group.key,
      label: group.label,
      value: Math.round(total / group.skills.length),
    };
  });
}

function polarPoint(index: number, total: number, center: number, radius: number) {
  const angle = (-Math.PI / 2) + ((Math.PI * 2 * index) / total);
  const x = center + Math.cos(angle) * radius;
  const y = center + Math.sin(angle) * radius;
  const anchor: "middle" | "start" | "end" = Math.abs(Math.cos(angle)) < 0.2 ? "middle" : Math.cos(angle) > 0 ? "start" : "end";
  return { x, y, anchor };
}

function startCase(value: string) {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
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
  const flags: string[] = [];
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
