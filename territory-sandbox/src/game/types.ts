export type Faction = {
  id: number
  name: string
  color: string
}

export type TerrainKind = 'sea' | 'plain' | 'ridge' | 'pass'

export type HexCell = {
  id: string
  q: number
  r: number
  x: number
  y: number
  terrain: TerrainKind
  isLand: boolean
  ownerId: number | null
  population: number
  growthRate: number
  maxPopulation: number
  neighbors: string[]
  wanderSeeds: number[]
  frontlinePressure: number
  recentConflict: number
  conflictTargetId: string | null
  conflictMomentum: number
  conflictProgress: number
  occupationRecovery: number
  occupationAnchorId: string | null
}

export type ReinforcementTransfer = {
  id: string
  factionId: number
  fromCellId: string
  toCellId: string
  pathCellIds: string[]
  currentHop: number
  amount: number
  elapsedMs: number
  durationMs: number
}

export type World = {
  width: number
  height: number
  hexSize: number
  cells: HexCell[]
  cellMap: Record<string, HexCell>
  factions: Faction[]
  selectedCellId: string | null
  tick: number
  battleAccumulatorMs: number
  reinforcements: ReinforcementTransfer[]
  reinforcementAccumulatorMs: number
  nextReinforcementId: number
}

export type SimulationOptions = {
  growthMultiplier: number
  conquestIntervalMs: number
  attackThreshold: number
  sendRatio: number
  defenseBonus: number
  passDefenseBonus: number
  passPressureBonus: number
  minOccupationGarrison: number
  occupationRecoverySeconds: number
  occupationDefenseBonus: number
  occupationGrowthPenalty: number
  battleCommitmentScale: number
  battleDefenseLossScale: number
  battleAttackerLossScale: number
  reinforcementIntervalMs: number
  reinforcementMinDonorPopulation: number
  reinforcementSendRatio: number
  reinforcementMinBatch: number
  reinforcementMaxBatch: number
  reinforcementTravelMsBase: number
  reinforcementTravelMsPerStep: number
  reinforcementMaxIncomingPerTarget: number
  occupationSupportBatch: number
}
