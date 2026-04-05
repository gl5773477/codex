export type Faction = {
  id: number
  name: string
  color: string
}

export type HexCell = {
  id: string
  q: number
  r: number
  x: number
  y: number
  isLand: boolean
  ownerId: number | null
  population: number
  growthRate: number
  maxPopulation: number
  neighbors: string[]
  wanderSeeds: number[]
  frontlinePressure: number
  recentConflict: number
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
}

export type SimulationOptions = {
  growthMultiplier: number
  conquestIntervalMs: number
  attackThreshold: number
  sendRatio: number
  defenseBonus: number
}
