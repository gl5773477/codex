import { SIMULATION } from './constants'
import type { HexCell, World } from './types'

const cloneWorld = (world: World): World => {
  const cells = world.cells.map((cell) => ({ ...cell, wanderSeeds: [...cell.wanderSeeds] }))
  const cellMap = Object.fromEntries(cells.map((cell) => [cell.id, cell]))
  return {
    ...world,
    cells,
    cellMap,
  }
}

const weakestEnemyNeighbor = (cell: HexCell, world: World) => {
  return cell.neighbors
    .map((id) => world.cellMap[id])
    .filter(
      (neighbor): neighbor is HexCell =>
        Boolean(neighbor && neighbor.isLand && neighbor.ownerId !== null && neighbor.ownerId !== cell.ownerId),
    )
    .sort((a, b) => a.population - b.population)[0]
}

export const addPopulationToCell = (world: World, cellId: string, amount: number) => {
  const next = cloneWorld(world)
  const cell = next.cellMap[cellId]
  if (!cell || !cell.isLand) return world

  cell.population = Math.min(cell.maxPopulation, cell.population + amount)
  return next
}

export const selectCell = (world: World, cellId: string | null) => ({
  ...world,
  selectedCellId: cellId,
})

export const stepWorld = (world: World, deltaMs: number) => {
  const next = cloneWorld(world)
  const dt = deltaMs / 1000
  next.tick += 1

  for (const cell of next.cells) {
    if (!cell.isLand || cell.ownerId === null) continue
    const growth = cell.growthRate * SIMULATION.growthMultiplier * dt
    cell.population = Math.min(cell.maxPopulation, cell.population + growth)
  }

  const shouldConquer = deltaMs >= SIMULATION.conquestIntervalMs * 0.5 || next.tick % 4 === 0
  if (!shouldConquer) return next

  const attackers = next.cells
    .filter((cell) => cell.isLand && cell.ownerId !== null && cell.population >= SIMULATION.attackThreshold)
    .sort((a, b) => b.population - a.population)

  for (const attacker of attackers) {
    const target = weakestEnemyNeighbor(attacker, next)
    if (!target) continue
    if (attacker.ownerId === null) continue

    const sendForce = Math.floor(attacker.population * SIMULATION.sendRatio)
    if (sendForce < 8) continue

    const defense = Math.ceil(target.population * SIMULATION.defenseBonus)
    attacker.population = Math.max(6, attacker.population - sendForce)

    if (sendForce > defense) {
      target.ownerId = attacker.ownerId
      target.population = Math.max(6, sendForce - defense)
    } else {
      target.population = Math.max(0, target.population - sendForce * 0.72)
    }
  }

  return next
}
