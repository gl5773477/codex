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

const hostileNeighbors = (cell: HexCell, world: World) => {
  return cell.neighbors
    .map((id) => world.cellMap[id])
    .filter(
      (neighbor): neighbor is HexCell =>
        Boolean(neighbor && neighbor.isLand && neighbor.ownerId !== null && neighbor.ownerId !== cell.ownerId),
    )
}

const weakestEnemyNeighbor = (cell: HexCell, world: World) => {
  return hostileNeighbors(cell, world)
    .sort((a, b) => a.population - b.population)[0]
}

const updateFrontlinePressure = (world: World) => {
  for (const cell of world.cells) {
    if (!cell.isLand || cell.ownerId === null) {
      cell.frontlinePressure = 0
      cell.recentConflict = 0
      continue
    }

    const enemies = hostileNeighbors(cell, world)
    if (enemies.length === 0) {
      cell.frontlinePressure = 0
      continue
    }

    const hostilePopulation = enemies.reduce((sum, enemy) => sum + enemy.population, 0)
    const readiness = Math.max(0, cell.population - SIMULATION.attackThreshold)
      / Math.max(1, cell.maxPopulation - SIMULATION.attackThreshold)
    const neighborFactor = Math.min(0.4, enemies.length * 0.14)
    const hostileFactor = Math.min(0.24, hostilePopulation / Math.max(1, cell.maxPopulation * 2.4))
    const conflictFactor = cell.recentConflict * 0.22

    cell.frontlinePressure = Math.min(1, 0.24 + neighborFactor + hostileFactor + readiness * 0.16 + conflictFactor)
  }
}

export const addPopulationToCell = (world: World, cellId: string, amount: number) => {
  const next = cloneWorld(world)
  const cell = next.cellMap[cellId]
  if (!cell || !cell.isLand) return world

  cell.population = Math.min(cell.maxPopulation, cell.population + amount)
  updateFrontlinePressure(next)
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
    if (!cell.isLand || cell.ownerId === null) {
      cell.frontlinePressure = 0
      cell.recentConflict = 0
      continue
    }

    cell.recentConflict = Math.max(0, cell.recentConflict - dt * 0.85)
    const growth = cell.growthRate * SIMULATION.growthMultiplier * dt
    cell.population = Math.min(cell.maxPopulation, cell.population + growth)
  }

  const shouldConquer = deltaMs >= SIMULATION.conquestIntervalMs * 0.5 || next.tick % 4 === 0
  if (!shouldConquer) {
    updateFrontlinePressure(next)
    return next
  }

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
    const clashIntensity = Math.min(1, sendForce / Math.max(12, attacker.maxPopulation * 0.62))
    attacker.population = Math.max(6, attacker.population - sendForce)
    attacker.recentConflict = Math.min(1, attacker.recentConflict + clashIntensity * 0.72)
    target.recentConflict = Math.min(1, target.recentConflict + clashIntensity)

    if (sendForce > defense) {
      target.ownerId = attacker.ownerId
      target.population = Math.max(6, sendForce - defense)
      target.recentConflict = Math.min(1, target.recentConflict + 0.24)
    } else {
      target.population = Math.max(0, target.population - sendForce * 0.72)
    }
  }

  updateFrontlinePressure(next)
  return next
}
