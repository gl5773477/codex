import { describe, expect, it } from 'vitest'
import { FACTIONS, HEX_SIZE, SIMULATION } from './constants'
import { axialToPixel, makeCellId, oddRNeighbors } from './hex'
import { getReinforcementTravelProgress } from './render'
import { stepWorld } from './simulation'
import type { HexCell, World } from './types'
import { createWorld } from './world'

const makeCell = (
  q: number,
  r: number,
  ownerId: number | null,
  population: number,
  neighbors: string[],
  overrides: Partial<HexCell> = {},
): HexCell => {
  const { x, y } = axialToPixel(q, r, HEX_SIZE)

  return {
    id: makeCellId(q, r),
    q,
    r,
    x,
    y,
    terrain: 'plain',
    isLand: true,
    ownerId,
    population,
    growthRate: 0,
    maxPopulation: 100,
    neighbors,
    wanderSeeds: [0.11, 0.27, 0.53],
    frontlinePressure: 0,
    recentConflict: 0,
    conflictTargetId: null,
    conflictMomentum: 0,
    conflictProgress: 0,
    occupationRecovery: 0,
    occupationAnchorId: null,
    ...overrides,
  }
}

const makeWorld = (cells: HexCell[]): World => ({
  width: 3,
  height: 3,
  hexSize: HEX_SIZE,
  cells,
  cellMap: Object.fromEntries(cells.map((cell) => [cell.id, cell])),
  factions: FACTIONS.slice(0, 3),
  selectedCellId: null,
  tick: 0,
  battleAccumulatorMs: 0,
  reinforcements: [],
  reinforcementAccumulatorMs: 0,
  nextReinforcementId: 1,
})

describe('regression audit', () => {
  it('uses the correct odd-r neighbor directions', () => {
    expect(oddRNeighbors(5, 2)).toEqual([
      { q: 6, r: 2 },
      { q: 5, r: 1 },
      { q: 4, r: 1 },
      { q: 4, r: 2 },
      { q: 4, r: 3 },
      { q: 5, r: 3 },
    ])

    expect(oddRNeighbors(5, 3)).toEqual([
      { q: 6, r: 3 },
      { q: 6, r: 2 },
      { q: 5, r: 2 },
      { q: 4, r: 3 },
      { q: 5, r: 4 },
      { q: 6, r: 4 },
    ])
  })

  it('clears invalid non-adjacent conflict targets on the next simulation step', () => {
    const a = makeCell(0, 0, 1, 60, [], {
      conflictTargetId: makeCellId(2, 0),
      recentConflict: 0.45,
      conflictMomentum: 0.4,
      conflictProgress: 0.5,
    })
    const b = makeCell(2, 0, 2, 52, [])
    const world = makeWorld([a, b])

    const next = stepWorld(world, 120)
    const nextA = next.cellMap[a.id]

    expect(nextA.conflictTargetId).toBeNull()
    expect(Math.abs(nextA.conflictMomentum)).toBeLessThan(0.15)
    expect(Math.abs(nextA.conflictProgress)).toBeLessThan(0.2)
  })

  it('keeps an active conflict link stable between battle rounds instead of blinking off', () => {
    const frontId = makeCellId(1, 0)
    const attacker = makeCell(0, 0, 1, 48, [frontId], {
      conflictTargetId: frontId,
      recentConflict: 0.07,
      conflictMomentum: 0.18,
      conflictProgress: 0.22,
    })
    const defender = makeCell(1, 0, 2, 32, [attacker.id], {
      conflictTargetId: attacker.id,
      recentConflict: 0.09,
      conflictMomentum: -0.15,
      conflictProgress: -0.2,
    })
    const world = makeWorld([attacker, defender])

    const next = stepWorld(world, 240)

    expect(next.cellMap[attacker.id].conflictTargetId).toBe(frontId)
    expect(next.cellMap[defender.id].conflictTargetId).toBe(attacker.id)
  })

  it('captures a zone after defenders are reduced to zero instead of leaving a dead tile', () => {
    const centerId = makeCellId(1, 0)
    const left = makeCell(0, 0, 1, 90, [centerId])
    const center = makeCell(1, 0, 2, 1, [left.id, makeCellId(2, 0)])
    const right = makeCell(2, 0, 3, 82, [centerId])
    const world = makeWorld([left, center, right])

    const next = stepWorld(world, SIMULATION.conquestIntervalMs)
    const conquered = next.cellMap[centerId]

    expect(conquered.ownerId).not.toBe(2)
    expect(conquered.population).toBeGreaterThan(0)
  })

  it('does not allow a freshly captured tile to flip back immediately', () => {
    const centerId = makeCellId(1, 0)
    const left = makeCell(0, 0, 1, 88, [centerId], {
      conflictTargetId: centerId,
      conflictProgress: 0.9,
    })
    const center = makeCell(1, 0, 2, 2, [left.id, makeCellId(2, 0)], {
      conflictTargetId: left.id,
      conflictProgress: -0.8,
    })
    const right = makeCell(2, 0, 2, 96, [centerId])
    const world = makeWorld([left, center, right])

    const captured = stepWorld(world, SIMULATION.conquestIntervalMs)
    const afterCapture = captured.cellMap[centerId]
    expect(afterCapture.ownerId).toBe(1)
    expect(afterCapture.occupationRecovery).toBeGreaterThan(0)

    const stabilized = stepWorld(captured, SIMULATION.conquestIntervalMs)
    expect(stabilized.cellMap[centerId].ownerId).toBe(1)
  })

  it('keeps dispatching adjacent occupation support from the victorious frontline after capture', () => {
    const centerId = makeCellId(1, 0)
    const left = makeCell(0, 0, 1, 88, [centerId], {
      conflictTargetId: centerId,
      conflictProgress: 0.9,
    })
    const center = makeCell(1, 0, 2, 2, [left.id, makeCellId(2, 0)], {
      conflictTargetId: left.id,
      conflictProgress: -0.8,
    })
    const right = makeCell(2, 0, 2, 72, [centerId])
    const world = makeWorld([left, center, right])

    const captured = stepWorld(world, SIMULATION.conquestIntervalMs)
    const occupied = captured.cellMap[centerId]
    expect(occupied.ownerId).toBe(1)
    expect(occupied.occupationAnchorId).toBe(left.id)

    const reinforced = stepWorld(captured, SIMULATION.reinforcementIntervalMs)
    const support = reinforced.reinforcements.find(
      (transfer) => transfer.fromCellId === left.id && transfer.toCellId === centerId,
    )

    expect(support).toBeDefined()
    expect(support?.pathCellIds).toEqual([left.id, centerId])
  })

  it('dispatches reinforcement batches from safe rear tiles to exposed allies', () => {
    const frontId = makeCellId(1, 0)
    const donor = makeCell(0, 0, 1, 72, [frontId])
    const front = makeCell(1, 0, 1, 12, [donor.id, makeCellId(2, 0)])
    const enemy = makeCell(2, 0, 2, 20, [frontId])
    const world = makeWorld([donor, front, enemy])

    const next = stepWorld(world, SIMULATION.reinforcementIntervalMs)
    const transfer = next.reinforcements[0]

    expect(next.reinforcements).toHaveLength(1)
    expect(transfer.fromCellId).toBe(donor.id)
    expect(transfer.toCellId).toBe(frontId)
    expect(transfer.pathCellIds).toEqual([donor.id, frontId])
    expect(transfer.currentHop).toBe(0)
    expect(next.cellMap[donor.id].population).toBeLessThan(donor.population)
    expect(next.cellMap[donor.id].population).toBeGreaterThanOrEqual(SIMULATION.reinforcementMinDonorPopulation)
  })

  it('delivers reinforcements after travel time and increases frontline manpower', () => {
    const frontId = makeCellId(1, 0)
    const donor = makeCell(0, 0, 1, 72, [frontId])
    const front = makeCell(1, 0, 1, 10, [donor.id, makeCellId(2, 0)], {
      occupationRecovery: SIMULATION.occupationRecoverySeconds,
    })
    const enemy = makeCell(2, 0, 2, 20, [frontId])
    const world = makeWorld([donor, front, enemy])

    const dispatched = stepWorld(world, SIMULATION.reinforcementIntervalMs)
    const transfer = dispatched.reinforcements[0]
    const beforeArrivalPopulation = dispatched.cellMap[frontId].population

    const arrived = stepWorld(dispatched, transfer.durationMs)

    expect(arrived.reinforcements).toHaveLength(0)
    expect(arrived.cellMap[frontId].population).toBeGreaterThan(beforeArrivalPopulation)
  })

  it('moves distant reinforcements hop by hop through adjacent friendly tiles', () => {
    const midId = makeCellId(1, 0)
    const frontId = makeCellId(2, 0)
    const donor = makeCell(0, 0, 1, 84, [midId])
    const mid = makeCell(1, 0, 1, 26, [donor.id, frontId])
    const front = makeCell(2, 0, 1, 10, [midId, makeCellId(3, 0)])
    const enemy = makeCell(3, 0, 2, 22, [frontId])
    const world = makeWorld([donor, mid, front, enemy])

    const dispatched = stepWorld(world, SIMULATION.reinforcementIntervalMs)
    const transfer = dispatched.reinforcements[0]

    expect(transfer.pathCellIds).toEqual([donor.id, midId, frontId])
    expect(transfer.currentHop).toBe(0)

    const afterFirstHop = stepWorld(dispatched, transfer.durationMs)
    const continued = afterFirstHop.reinforcements[0]

    expect(afterFirstHop.reinforcements).toHaveLength(1)
    expect(continued.currentHop).toBe(1)
    expect(afterFirstHop.cellMap[frontId].population).toBeLessThanOrEqual(front.population + 1)

    const arrived = stepWorld(afterFirstHop, continued.durationMs)

    expect(arrived.reinforcements).toHaveLength(0)
    expect(arrived.cellMap[frontId].population).toBeGreaterThan(front.population)
  })

  it('keeps reinforcement visual travel progress continuous when a transfer enters the next hop', () => {
    expect(getReinforcementTravelProgress({
      pathCellIds: ['a', 'b', 'c'],
      currentHop: 0,
      elapsedMs: 100,
      durationMs: 100,
    })).toBeCloseTo(0.5)

    expect(getReinforcementTravelProgress({
      pathCellIds: ['a', 'b', 'c'],
      currentHop: 1,
      elapsedMs: 0,
      durationMs: 100,
    })).toBeCloseTo(0.5)

    expect(getReinforcementTravelProgress({
      pathCellIds: ['a', 'b', 'c', 'd'],
      currentHop: 1,
      elapsedMs: 50,
      durationMs: 100,
    })).toBeCloseTo(0.5)
  })

  it('does not keep topping up an already healthy frontline into a permanent stalemate band', () => {
    const donorId = makeCellId(0, 0)
    const frontId = makeCellId(1, 0)
    const donor = makeCell(0, 0, 1, 82, [frontId])
    const frontline = makeCell(1, 0, 1, 45, [donorId, makeCellId(2, 0)], {
      frontlinePressure: 0.42,
      recentConflict: 0.18,
    })
    const enemy = makeCell(2, 0, 2, 43, [frontId], {
      frontlinePressure: 0.42,
      recentConflict: 0.18,
    })
    const world = makeWorld([donor, frontline, enemy])

    const next = stepWorld(world, SIMULATION.reinforcementIntervalMs)

    expect(next.reinforcements).toHaveLength(0)
  })

  it('turns a meaningful frontline population advantage into sustained pressure instead of instant averaging', () => {
    const frontId = makeCellId(1, 0)
    const attacker = makeCell(0, 0, 1, 72, [frontId], {
      frontlinePressure: 0.42,
    })
    const defender = makeCell(1, 0, 2, 48, [attacker.id], {
      frontlinePressure: 0.42,
    })
    let world = makeWorld([attacker, defender])

    for (let step = 0; step < 6; step += 1) {
      world = stepWorld(world, SIMULATION.conquestIntervalMs)
    }

    const currentAttacker = world.cellMap[attacker.id]
    const currentDefender = world.cellMap[frontId]

    expect(
      currentDefender.ownerId !== 2
      || currentAttacker.population - currentDefender.population >= 6
      || currentAttacker.conflictProgress >= 0.32,
    ).toBe(true)
  })

  it('burns down total manpower during prolonged border combat instead of hovering near a flat stalemate band', () => {
    const frontId = makeCellId(1, 0)
    const attacker = makeCell(0, 0, 1, 72, [frontId], {
      frontlinePressure: 0.46,
      recentConflict: 0.18,
    })
    const defender = makeCell(1, 0, 2, 56, [attacker.id], {
      frontlinePressure: 0.46,
      recentConflict: 0.18,
    })
    let world = makeWorld([attacker, defender])
    const initialTotal = attacker.population + defender.population

    for (let step = 0; step < 3; step += 1) {
      world = stepWorld(world, SIMULATION.conquestIntervalMs)
    }

    const totalPopulation = world.cells.reduce((sum, cell) => sum + cell.population, 0)

    expect(initialTotal - totalPopulation).toBeGreaterThanOrEqual(18)
  })

  it('keeps core combat invariants stable during long autonomous simulation', () => {
    let world = createWorld()

    for (let step = 0; step < 320; step += 1) {
      world = stepWorld(world, 220)
    }

    for (const cell of world.cells) {
      if (cell.isLand && cell.ownerId !== null) {
        expect(cell.population).toBeGreaterThan(0)
      }

      if (cell.conflictTargetId) {
        const target = world.cellMap[cell.conflictTargetId]
        expect(target).toBeDefined()
        expect(cell.neighbors).toContain(cell.conflictTargetId)
        expect(target?.isLand).toBe(true)
        expect(target?.ownerId).not.toBe(cell.ownerId)
      }
    }

    for (const transfer of world.reinforcements) {
      const from = world.cellMap[transfer.pathCellIds[transfer.currentHop]]
      const to = world.cellMap[transfer.pathCellIds[transfer.currentHop + 1]]
      expect(from).toBeDefined()
      expect(to).toBeDefined()
      expect(from?.ownerId).toBe(transfer.factionId)
      expect(to?.ownerId).toBe(transfer.factionId)
      expect(from?.neighbors).toContain(to?.id)
      expect(transfer.amount).toBeGreaterThanOrEqual(SIMULATION.reinforcementMinBatch)
    }
  })
})
