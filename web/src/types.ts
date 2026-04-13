export type Surface = "hard" | "clay" | "grass";

export interface TopSkill {
  label: string;
  value: number;
}

export interface PlayerSummary {
  playerId: string;
  name: string;
  country: string;
  tour: string;
  handedness: "left" | "right";
  backhandHands: number;
  overallRating: number;
  surfaceComfort: Record<Surface, number>;
  tags: string[];
  topSkills: TopSkill[];
}

export interface PlayerDetail {
  summary: PlayerSummary;
  skills: Record<string, number>;
  tactics: {
    baselineAggression: number;
    preferredServeDirection: string;
    shortBallAttack: number;
    netFrequency: number;
  };
  spin: {
    serveSpin: number;
    forehandSpin: number;
    backhandSpin: number;
    sliceFrequency: number;
  };
  physical: {
    durability: number;
    recovery: number;
    peakCondition: number;
  };
  surfaceProfile: Record<Surface, number>;
  derivedStats: Record<string, number | null | string[]>;
  strengths: TopSkill[];
  weaknesses: TopSkill[];
}

export interface ComparePayload {
  surface: Surface;
  playerOne: PlayerDetail;
  playerTwo: PlayerDetail;
  skillDeltas: Array<{
    skill: string;
    label: string;
    playerOne: number;
    playerTwo: number;
    delta: number;
    edgeFor: string | null;
  }>;
  surfaceEdge: {
    playerOne: number;
    playerTwo: number;
    delta: number;
  };
  matchupTags: string[];
  tacticalThemes: Array<{
    edgeFor: string;
    label: string;
  }>;
}

export interface MatchStats {
  pointsPlayed: number;
  totalPointsWon: number;
  servicePointsPlayed: number;
  servicePointsWon: number;
  returnPointsPlayed: number;
  returnPointsWon: number;
  aces: number;
  serviceWinners: number;
  doubleFaults: number;
  winners: number;
  returnWinners: number;
  forcedErrorsDrawn: number;
  unforcedErrors: number;
  breakPointsCreated: number;
  breakPointsConverted: number;
  breakPointsFaced: number;
  breakPointsSaved: number;
  gamesServed: number;
  serviceGamesWon: number;
  totalShots: number;
  firstServeAttempts: number;
  firstServesIn: number;
  secondServeAttempts: number;
  secondServesIn: number;
  totalWinners: number;
  firstServePercentage: number;
  servicePointsWonPercentage: number;
  returnPointsWonPercentage: number;
  holdPercentage: number;
  aceRate: number;
  doubleFaultRate: number;
  secondServeDoubleFaultRate: number;
  winnerToErrorRatio: number;
}

export interface Shot {
  pointNumber: number;
  shotNumber: number;
  scoreBefore: string;
  strikerId: string;
  receiverId: string;
  shotKind: string;
  shotHand: string;
  quality: string;
  outcome: string;
  spinType: string;
  serveNumber?: number | null;
  serveDirection?: string | null;
  pressure: number;
  fatigue: number;
  detail: string;
}

export interface PointEntry {
  pointNumber: number;
  setNumber: number;
  gameNumberInSet: number;
  serverId: string;
  receiverId: string;
  winnerId: string;
  scoreBefore: string;
  scoreAfter: string;
  pointScoreBefore: string;
  pointScoreAfter: string;
  setsBefore: Record<string, number>;
  setsAfter: Record<string, number>;
  gamesBefore: Record<string, number>;
  gamesAfter: Record<string, number>;
  isTiebreak: boolean;
  breakPointFor: string | null;
  setPointFor: string | null;
  matchPointFor: string | null;
  pressureIndex: number;
  pressureLabel: string;
  rallyLength: number;
  terminalOutcome: string;
  terminalShotKind: string;
  terminalStrikerId: string;
  shotCount: number;
  gameCompleted: boolean;
  setCompleted: boolean;
  matchCompleted: boolean;
  shots: Shot[];
}

export interface GameEntry {
  gameNumber: number;
  setNumber: number;
  gameNumberInSet: number;
  scoreBefore: string;
  scoreAfter: string;
  serverId: string;
  winnerId: string;
  isTiebreak: boolean;
  holdsServe: boolean;
  pointCount: number;
  points: PointEntry[];
}

export interface SetEntry {
  setNumber: number;
  score: string;
  winnerId: string;
  games: Record<string, number>;
  tiebreakPoints: Record<string, number> | null;
  stats: Record<string, MatchStats>;
  gamesTimeline: GameEntry[];
}

export interface PatternSummaryPlayer {
  serveDirections?: Record<string, number>;
  serveSpins?: Record<string, number>;
  targetedWings?: Record<string, number>;
  rallySpins?: Record<string, number>;
  winnersByHand?: Record<string, number>;
  forcedErrorsByHand?: Record<string, number>;
  unforcedErrorsByHand?: Record<string, number>;
}

export interface PatternSummary {
  rallyBands?: Record<string, number>;
  players?: Record<string, PatternSummaryPlayer>;
}

export interface MatchReport {
  meta: {
    players: [string, string];
    winnerId: string;
    scoreline: string;
    surface: Surface;
    bestOfSets: number;
    seed: number;
    averageRallyLength: number;
    totalPoints: number;
  };
  players: Record<string, PlayerSummary>;
  matchStats: Record<string, MatchStats>;
  patternSummary: PatternSummary;
  sets: SetEntry[];
}

export interface BatchSummary {
  meta: {
    players: [string, string];
    iterations: number;
    surface: Surface;
    averageRallyLength: number;
    averagePointsPerMatch: number;
  };
  players: Record<string, PlayerSummary>;
  wins: Record<string, number>;
  winRates: Record<string, number>;
  holdRate: Record<string, number>;
  breakRate: Record<string, number>;
  aceRate: Record<string, number>;
  firstServeInRate: Record<string, number>;
  doubleFaultRate: Record<string, number>;
  secondServeDoubleFaultRate: Record<string, number>;
  servicePointsWonRate: Record<string, number>;
  returnPointsWonRate: Record<string, number>;
  winnerToErrorRatio: Record<string, number>;
  commonScorelines: Record<string, number>;
  rallyBandDistribution: Record<string, number>;
}

export interface RecentSimulation {
  id: string;
  kind: "match" | "batch";
  label: string;
  meta: string;
}
