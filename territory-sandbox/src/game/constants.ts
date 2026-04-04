import type { Faction, SimulationOptions } from './types'

export const HEX_COLUMNS = 18
export const HEX_ROWS = 11
export const HEX_SIZE = 28

export const FACTIONS: Faction[] = [
  { id: 1, name: '赤曜', color: '#e85d75' },
  { id: 2, name: '苍岭', color: '#4f8cff' },
  { id: 3, name: '金穗', color: '#f4b942' },
  { id: 4, name: '翠森', color: '#47b881' },
  { id: 5, name: '紫幕', color: '#9b6ef3' },
  { id: 6, name: '白潮', color: '#c7d2da' },
]

export const SIMULATION: SimulationOptions = {
  growthMultiplier: 1,
  conquestIntervalMs: 800,
  attackThreshold: 34,
  sendRatio: 0.5,
  defenseBonus: 1.08,
}

export const WORLD_STYLE = {
  sea: '#0f172a',
  background: '#020617',
  neutralLand: '#1f2937',
  outline: 'rgba(255,255,255,0.08)',
  selected: '#ffffff',
}
