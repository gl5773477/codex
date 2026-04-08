import { SIMULATION } from './constants'
import type { HexCell, ReinforcementTransfer, World } from './types'

const clamp01 = (value: number) => Math.max(0, Math.min(1, value))
const clampSigned = (value: number, limit = 1) => Math.max(-limit, Math.min(limit, value))

const recoveryRatio = (cell: HexCell) =>
  clamp01((cell.occupationRecovery ?? 0) / SIMULATION.occupationRecoverySeconds)

const frontlineReserve = (cell: HexCell) => {
  return Math.min(
    cell.maxPopulation * 0.62,
    Math.max(
      SIMULATION.minOccupationGarrison + 6 + (cell.terrain === 'pass' ? 3 : 0),
      SIMULATION.attackThreshold * 0.52 + recoveryRatio(cell) * 9,
    ),
  )
}

const cloneWorld = (world: World): World => {
  const cells = world.cells.map((cell) => ({ ...cell, wanderSeeds: [...cell.wanderSeeds] }))
  const cellMap = Object.fromEntries(cells.map((cell) => [cell.id, cell]))
  const reinforcements = (world.reinforcements ?? []).map((transfer) => ({ ...transfer }))
  return {
    ...world,
    cells,
    cellMap,
    reinforcements,
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

const attackableHostileNeighbors = (cell: HexCell, world: World) => {
  return hostileNeighbors(cell, world)
}

const safeDonorReserve = (cell: HexCell) => {
  return Math.max(
    SIMULATION.reinforcementMinDonorPopulation,
    SIMULATION.minOccupationGarrison + 4 + cell.frontlinePressure * 12 + cell.recentConflict * 8,
  )
}

const supportTargetPopulation = (cell: HexCell) => {
  const recoveryBonus = recoveryRatio(cell) * 14
  const frontlineBonus = cell.frontlinePressure * 6
  const conflictBonus = cell.recentConflict * 4
  return Math.min(
    cell.maxPopulation,
    Math.max(SIMULATION.minOccupationGarrison + 6, SIMULATION.attackThreshold - 6)
      + recoveryBonus
      + frontlineBonus
      + conflictBonus,
  )
}

const supportPriority = (
  cell: HexCell,
  world: World,
  incomingAmount: number,
) => {
  if (!cell.isLand || cell.ownerId === null) return 0

  const enemyContact = hostileNeighbors(cell, world).length
  const recovery = recoveryRatio(cell)
  const desiredPopulation = supportTargetPopulation(cell)
  const deficit = clamp01((desiredPopulation - (cell.population + incomingAmount)) / Math.max(12, desiredPopulation))

  if (enemyContact === 0 && cell.recentConflict < 0.08 && recovery < 0.08 && deficit < 0.4) {
    return 0
  }

  if (deficit < 0.16 && recovery < 0.2 && cell.population >= SIMULATION.attackThreshold - 2) {
    return 0
  }

  return (
    deficit * 1.18
    + recovery * 0.92
    + cell.recentConflict * 0.34
    + cell.frontlinePressure * 0.26
    + (enemyContact > 0 ? 0.12 : 0)
  )
}

const buildFriendlyRouteIndex = (target: HexCell, world: World) => {
  const steps = new Map<string, number>()
  const towardTarget = new Map<string, string>()
  if (!target.isLand || target.ownerId === null) return { steps, towardTarget }

  const queue = [target.id]
  steps.set(target.id, 0)

  for (let index = 0; index < queue.length; index += 1) {
    const current = world.cellMap[queue[index]]
    if (!current) continue
    const currentSteps = steps.get(current.id) ?? 0

    for (const neighborId of current.neighbors) {
      if (steps.has(neighborId)) continue
      const neighbor = world.cellMap[neighborId]
      if (!neighbor || !neighbor.isLand || neighbor.ownerId !== target.ownerId) continue

      steps.set(neighbor.id, currentSteps + 1)
      towardTarget.set(neighbor.id, current.id)
      queue.push(neighbor.id)
    }
  }

  return { steps, towardTarget }
}

const buildPathToTarget = (
  startId: string,
  targetId: string,
  towardTarget: Map<string, string>,
) => {
  const path = [startId]
  const visited = new Set(path)
  let cursor = startId

  while (cursor !== targetId) {
    const nextStep = towardTarget.get(cursor)
    if (!nextStep || visited.has(nextStep)) return null

    path.push(nextStep)
    visited.add(nextStep)
    cursor = nextStep
  }

  return path
}

const enqueueReinforcement = (
  world: World,
  factionId: number,
  pathCellIds: string[],
  amount: number,
) => {
  const transfer: ReinforcementTransfer = {
    id: `rf-${world.nextReinforcementId}`,
    factionId,
    fromCellId: pathCellIds[0],
    toCellId: pathCellIds[pathCellIds.length - 1],
    pathCellIds,
    currentHop: 0,
    amount,
    elapsedMs: 0,
    durationMs: SIMULATION.reinforcementTravelMsBase + SIMULATION.reinforcementTravelMsPerStep,
  }

  world.reinforcements.push(transfer)
  world.nextReinforcementId += 1
  return transfer
}

const buildReinforcementIndex = (world: World) => {
  const byTarget = new Map<string, { count: number; amount: number }>()
  const bySource = new Map<string, number>()

  for (const transfer of world.reinforcements ?? []) {
    const targetStats = byTarget.get(transfer.toCellId) ?? { count: 0, amount: 0 }
    targetStats.count += 1
    targetStats.amount += transfer.amount
    byTarget.set(transfer.toCellId, targetStats)

    bySource.set(transfer.fromCellId, (bySource.get(transfer.fromCellId) ?? 0) + 1)
  }

  return { byTarget, bySource }
}

const markTransferInIndex = (
  transferIndex: ReturnType<typeof buildReinforcementIndex>,
  transfer: ReinforcementTransfer,
) => {
  transferIndex.bySource.set(
    transfer.fromCellId,
    (transferIndex.bySource.get(transfer.fromCellId) ?? 0) + 1,
  )

  transferIndex.byTarget.set(transfer.toCellId, {
    count: (transferIndex.byTarget.get(transfer.toCellId)?.count ?? 0) + 1,
    amount: (transferIndex.byTarget.get(transfer.toCellId)?.amount ?? 0) + transfer.amount,
  })
}

const advanceReinforcements = (world: World, deltaMs: number) => {
  if (!world.reinforcements.length) return false

  const remaining: ReinforcementTransfer[] = []
  let delivered = false

  for (const transfer of world.reinforcements) {
    transfer.elapsedMs += deltaMs

    let completed = false
    while (transfer.elapsedMs >= transfer.durationMs) {
      transfer.elapsedMs -= transfer.durationMs
      transfer.currentHop += 1

      const currentCellId = transfer.pathCellIds[Math.min(transfer.currentHop, transfer.pathCellIds.length - 1)]
      const currentCell = currentCellId ? world.cellMap[currentCellId] : null

      if (transfer.currentHop >= transfer.pathCellIds.length - 1) {
        if (currentCell && currentCell.isLand && currentCell.ownerId === transfer.factionId) {
          currentCell.population = Math.min(currentCell.maxPopulation, currentCell.population + transfer.amount)
          delivered = true
        }
        completed = true
        break
      }

      const nextCellId = transfer.pathCellIds[transfer.currentHop + 1]
      const nextCell = nextCellId ? world.cellMap[nextCellId] : null
      if (
        !currentCell
        || !nextCell
        || !currentCell.isLand
        || !nextCell.isLand
        || currentCell.ownerId !== transfer.factionId
        || nextCell.ownerId !== transfer.factionId
        || !currentCell.neighbors.includes(nextCell.id)
      ) {
        if (currentCell && currentCell.isLand && currentCell.ownerId === transfer.factionId) {
          currentCell.population = Math.min(currentCell.maxPopulation, currentCell.population + transfer.amount)
          delivered = true
        }
        completed = true
        break
      }
    }

    if (!completed) {
      remaining.push(transfer)
    }
  }

  world.reinforcements = remaining
  return delivered
}

const dispatchOccupationRelief = (
  world: World,
  transferIndex: ReturnType<typeof buildReinforcementIndex>,
) => {
  let created = false

  const occupiedTargets = world.cells
    .filter(
      (cell) =>
        cell.isLand
        && cell.ownerId !== null
        && cell.occupationRecovery > 0.16
        && cell.occupationAnchorId,
    )
    .sort((a, b) => {
      const aPressure = a.occupationRecovery * 0.9 + a.recentConflict * 0.5 + a.frontlinePressure * 0.35
      const bPressure = b.occupationRecovery * 0.9 + b.recentConflict * 0.5 + b.frontlinePressure * 0.35
      return bPressure - aPressure
    })

  for (const target of occupiedTargets) {
    const incoming = transferIndex.byTarget.get(target.id)
    if ((incoming?.count ?? 0) >= SIMULATION.reinforcementMaxIncomingPerTarget) continue

    const anchor = target.occupationAnchorId ? world.cellMap[target.occupationAnchorId] : null
    if (
      !anchor
      || !anchor.isLand
      || anchor.ownerId !== target.ownerId
      || !anchor.neighbors.includes(target.id)
    ) {
      target.occupationAnchorId = null
      continue
    }

    if ((transferIndex.bySource.get(anchor.id) ?? 0) > 0) continue

    const desiredPopulation = Math.max(
      supportTargetPopulation(target),
      SIMULATION.minOccupationGarrison + 8 + target.recentConflict * 5,
    )
    const incomingAmount = incoming?.amount ?? 0
    const deficit = Math.max(0, desiredPopulation - (target.population + incomingAmount))
    const anchorReserve = Math.max(frontlineReserve(anchor), SIMULATION.minOccupationGarrison + 8)
    const surplus = Math.max(0, anchor.population - anchorReserve)
    const amount = Math.max(
      0,
      Math.min(
        SIMULATION.occupationSupportBatch,
        Math.round(deficit),
        Math.round(surplus),
      ),
    )

    if (amount < 4) continue

    anchor.population -= amount
    const transfer = enqueueReinforcement(world, target.ownerId as number, [anchor.id, target.id], amount)
    markTransferInIndex(transferIndex, transfer)
    created = true
  }

  return created
}

const dispatchReinforcements = (world: World) => {
  const reinforcementRounds = Math.floor(
    (world.reinforcementAccumulatorMs ?? 0) / SIMULATION.reinforcementIntervalMs,
  )
  if (reinforcementRounds < 1) return false

  world.reinforcementAccumulatorMs -= reinforcementRounds * SIMULATION.reinforcementIntervalMs
  let created = false

  for (let round = 0; round < reinforcementRounds; round += 1) {
    const transferIndex = buildReinforcementIndex(world)
    if (dispatchOccupationRelief(world, transferIndex)) {
      created = true
    }

    for (const faction of world.factions) {
      const targets = world.cells
        .filter((cell) => cell.ownerId === faction.id && cell.isLand)
        .map((cell) => ({
          cell,
          priority: supportPriority(cell, world, transferIndex.byTarget.get(cell.id)?.amount ?? 0),
        }))
        .filter((entry) => entry.priority >= 0.42)
        .sort((a, b) => b.priority - a.priority)
        .slice(0, 3)

      for (const { cell: target } of targets) {
        const incoming = transferIndex.byTarget.get(target.id)
        if ((incoming?.count ?? 0) >= SIMULATION.reinforcementMaxIncomingPerTarget) continue

        const routeIndex = buildFriendlyRouteIndex(target, world)
        const donors = [...routeIndex.steps.entries()]
          .map(([cellId, steps]) => ({ cell: world.cellMap[cellId], steps }))
          .filter(({ cell, steps }) => {
            if (!cell || cell.id === target.id || steps < 1) return false
            if (!cell.isLand || cell.ownerId !== target.ownerId) return false
            if ((transferIndex.bySource.get(cell.id) ?? 0) > 0) return false
            if (cell.frontlinePressure >= 0.18 || cell.recentConflict >= 0.14) return false
            if (recoveryRatio(cell) >= 0.12) return false
            return cell.population - safeDonorReserve(cell) >= SIMULATION.reinforcementMinBatch
          })
          .sort((a, b) => {
            const aSurplus = a.cell.population - safeDonorReserve(a.cell)
            const bSurplus = b.cell.population - safeDonorReserve(b.cell)
            const aScore = aSurplus * 0.72 - a.steps * 4.4 - a.cell.frontlinePressure * 8
            const bScore = bSurplus * 0.72 - b.steps * 4.4 - b.cell.frontlinePressure * 8
            return bScore - aScore
          })

        const donorEntry = donors[0]
        if (!donorEntry) continue
        const pathCellIds = buildPathToTarget(donorEntry.cell.id, target.id, routeIndex.towardTarget)
        if (!pathCellIds || pathCellIds.length < 2) continue

        const desiredPopulation = supportTargetPopulation(target)
        const incomingAmount = incoming?.amount ?? 0
        const deficit = Math.max(0, desiredPopulation - (target.population + incomingAmount))
        const surplus = Math.max(0, donorEntry.cell.population - safeDonorReserve(donorEntry.cell))
        if (deficit < SIMULATION.reinforcementMinBatch || surplus < SIMULATION.reinforcementMinBatch) continue

        const amount = Math.max(
          SIMULATION.reinforcementMinBatch,
          Math.min(
            SIMULATION.reinforcementMaxBatch,
            Math.round(Math.min(deficit, surplus * SIMULATION.reinforcementSendRatio)),
          ),
        )
        if (amount > surplus) continue

        donorEntry.cell.population -= amount

        const transfer = enqueueReinforcement(world, faction.id, pathCellIds, amount)
        markTransferInIndex(transferIndex, transfer)
        created = true
      }
    }
  }

  return created
}

const weakestEnemyNeighbor = (cell: HexCell, world: World) => {
  return attackableHostileNeighbors(cell, world)
    .sort((a, b) => a.population - b.population)[0]
}

const continuingEnemyNeighbor = (cell: HexCell, world: World) => {
  if (!cell.conflictTargetId) return null

  const target = world.cellMap[cell.conflictTargetId]
  if (
    target &&
    target.isLand &&
    target.ownerId !== null &&
    target.ownerId !== cell.ownerId &&
    cell.neighbors.includes(target.id)
  ) {
    return target
  }

  return null
}

const preferredEnemyNeighbor = (cell: HexCell, world: World) => {
  return continuingEnemyNeighbor(cell, world) ?? weakestEnemyNeighbor(cell, world)
}

const shouldHoldConflictLink = (cell: HexCell, world: World) => {
  if (!hasValidConflictTarget(cell, world)) return false

  return (
    cell.recentConflict >= 0.035
    || Math.abs(cell.conflictMomentum) >= 0.045
    || Math.abs(cell.conflictProgress) >= 0.045
  )
}

const hasValidConflictTarget = (cell: HexCell, world: World) => {
  if (!cell.conflictTargetId || cell.ownerId === null) return false

  const target = world.cellMap[cell.conflictTargetId]
  return Boolean(
    target &&
    target.isLand &&
    target.ownerId !== null &&
    target.ownerId !== cell.ownerId &&
    cell.neighbors.includes(target.id),
  )
}

const collapseCapture = (world: World) => {
  for (const cell of world.cells) {
    if (!cell.isLand || cell.ownerId === null || cell.population > 0) continue

    const contenders = hostileNeighbors(cell, world)
    if (contenders.length === 0) {
      cell.population = 1
      continue
    }

    const winner = contenders
      .slice()
      .sort((a, b) => {
        const aScore = a.population + (a.conflictTargetId === cell.id ? 18 : 0) + a.conflictProgress * 16
        const bScore = b.population + (b.conflictTargetId === cell.id ? 18 : 0) + b.conflictProgress * 16
        return bScore - aScore
      })[0]

    if (!winner || winner.ownerId === null) {
      cell.population = 1
      continue
    }

    const occupationForce = Math.max(
      SIMULATION.minOccupationGarrison,
      Math.min(14, Math.round(winner.population * 0.16)),
    )
    winner.population = Math.max(6, winner.population - occupationForce)
    winner.conflictTargetId = cell.id
    winner.recentConflict = Math.min(1, winner.recentConflict + 0.12)
    winner.conflictMomentum = clampSigned(winner.conflictMomentum + 0.1)
    winner.conflictProgress = clampSigned(winner.conflictProgress + 0.18)

    cell.ownerId = winner.ownerId
    cell.population = occupationForce
    cell.recentConflict = Math.min(1, cell.recentConflict + 0.28)
    cell.conflictTargetId = null
    cell.conflictMomentum = 0
    cell.conflictProgress = 0
    cell.occupationRecovery = SIMULATION.occupationRecoverySeconds
    cell.occupationAnchorId = winner.id
  }
}

const sanitizeConflictTargets = (world: World) => {
  for (const cell of world.cells) {
    if (!cell.conflictTargetId) continue
    if (hasValidConflictTarget(cell, world)) continue

    cell.conflictTargetId = null
    cell.conflictMomentum *= 0.25
    cell.conflictProgress *= 0.25
  }
}

const updateFrontlinePressure = (world: World) => {
  for (const cell of world.cells) {
    if (!cell.isLand || cell.ownerId === null) {
      cell.frontlinePressure = 0
      cell.recentConflict = 0
      cell.conflictTargetId = null
      cell.conflictMomentum = 0
      cell.conflictProgress = 0
      cell.occupationRecovery = 0
      cell.occupationAnchorId = null
      continue
    }

    const enemies = hostileNeighbors(cell, world)
    if (enemies.length === 0) {
      cell.frontlinePressure = 0
      if (cell.recentConflict < 0.08) {
        cell.conflictTargetId = null
        cell.conflictMomentum = 0
        cell.conflictProgress = 0
      }
      if (cell.occupationRecovery <= 0.08) {
        cell.occupationAnchorId = null
      }
      continue
    }

    const hostilePopulation = enemies.reduce((sum, enemy) => sum + enemy.population, 0)
    const readiness = clamp01(
      Math.max(0, cell.population - SIMULATION.attackThreshold)
        / Math.max(1, cell.maxPopulation - SIMULATION.attackThreshold),
    )
    const neighborFactor = Math.min(0.32, enemies.length * 0.09)
    const hostileFactor = Math.min(0.28, hostilePopulation / Math.max(1, cell.maxPopulation * 3.1))
    const readinessFactor = readiness * 0.18
    const conflictFactor = cell.recentConflict * 0.34
    const terrainFactor = cell.terrain === 'pass' ? SIMULATION.passPressureBonus : 0

    cell.frontlinePressure = clamp01(
      neighborFactor + hostileFactor + readinessFactor + conflictFactor + terrainFactor,
    )
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
  next.battleAccumulatorMs = (world.battleAccumulatorMs ?? 0) + deltaMs
  next.reinforcementAccumulatorMs = (world.reinforcementAccumulatorMs ?? 0) + deltaMs

  for (const cell of next.cells) {
    if (!cell.isLand || cell.ownerId === null) {
      cell.frontlinePressure = 0
      cell.recentConflict = 0
      cell.conflictTargetId = null
      cell.conflictMomentum = 0
      cell.conflictProgress = 0
      cell.occupationRecovery = 0
      cell.occupationAnchorId = null
      continue
    }

    cell.occupationRecovery = Math.max(0, (cell.occupationRecovery ?? 0) - dt)
    if (cell.occupationRecovery <= 0.08) {
      cell.occupationAnchorId = null
    }
    cell.recentConflict = Math.max(0, cell.recentConflict - dt * 0.22)
    if (cell.conflictMomentum > 0) {
      cell.conflictMomentum = Math.max(0, cell.conflictMomentum - dt * 0.26)
    } else {
      cell.conflictMomentum = Math.min(0, cell.conflictMomentum + dt * 0.26)
    }
    if (cell.conflictProgress > 0) {
      cell.conflictProgress = Math.max(0, cell.conflictProgress - dt * 0.12)
    } else {
      cell.conflictProgress = Math.min(0, cell.conflictProgress + dt * 0.12)
    }

    if (cell.conflictTargetId && !hasValidConflictTarget(cell, next)) {
      cell.conflictTargetId = null
      cell.conflictMomentum *= 0.25
      cell.conflictProgress *= 0.25
    }

    if (cell.conflictTargetId && !shouldHoldConflictLink(cell, next)) {
      cell.conflictTargetId = null
      if (Math.abs(cell.conflictMomentum) < 0.06) {
        cell.conflictMomentum = 0
      }
      if (Math.abs(cell.conflictProgress) < 0.06) {
        cell.conflictProgress = 0
      }
    }

    const growthModifier = 1 - recoveryRatio(cell) * SIMULATION.occupationGrowthPenalty
    const growth = cell.growthRate * SIMULATION.growthMultiplier * growthModifier * dt
    cell.population = Math.min(cell.maxPopulation, cell.population + growth)
  }

  const deliveredReinforcements = advanceReinforcements(next, deltaMs)

  const battleRounds = Math.floor(next.battleAccumulatorMs / SIMULATION.conquestIntervalMs)
  if (battleRounds < 1) {
    updateFrontlinePressure(next)
    const dispatched = dispatchReinforcements(next)
    if (deliveredReinforcements || dispatched) {
      updateFrontlinePressure(next)
    }
    return next
  }

  next.battleAccumulatorMs -= battleRounds * SIMULATION.conquestIntervalMs

  for (let round = 0; round < battleRounds; round += 1) {
    const attackers = next.cells
      .filter((cell) => cell.isLand && cell.ownerId !== null && cell.population >= SIMULATION.attackThreshold)
      .sort((a, b) => b.population - a.population)

    for (const attacker of attackers) {
      if (attacker.ownerId === null) continue
      if (attacker.population < SIMULATION.attackThreshold) continue

      const target = preferredEnemyNeighbor(attacker, next)
      if (!target) continue
      if (attacker.conflictTargetId && attacker.conflictTargetId !== target.id) {
        attacker.conflictProgress *= 0.35
      }
      if (target.conflictTargetId && target.conflictTargetId !== attacker.id) {
        target.conflictProgress *= 0.35
      }

      const terrainDefense = target.terrain === 'pass' ? SIMULATION.passDefenseBonus : 1
      const recoveryDefense = 1 + recoveryRatio(target) * SIMULATION.occupationDefenseBonus
      const totalDefense = terrainDefense * recoveryDefense
      const readiness = clamp01(
        Math.max(0, attacker.population - SIMULATION.attackThreshold)
          / Math.max(1, attacker.maxPopulation - SIMULATION.attackThreshold),
      )
      const attackerReserve = frontlineReserve(attacker)
      const deployableForce = Math.max(0, attacker.population - attackerReserve)
      const offensiveBias = Math.max(0, attacker.conflictProgress) * 0.06
      const committedForce = Math.floor(
        deployableForce
          * (0.18 + readiness * 0.14 + offensiveBias)
          * SIMULATION.battleCommitmentScale,
      )
      if (committedForce < 4) continue

      const defenderGuard = Math.max(
        4,
        Math.ceil(target.population * (0.2 + totalDefense * 0.09)),
      )
      const defenseLoss = Math.min(
        target.population,
        Math.max(
          1,
          Math.round(
            committedForce
              * (0.34 + readiness * 0.16)
              * SIMULATION.battleDefenseLossScale
              / totalDefense,
          ),
        ),
      )
      const attackerLoss = Math.min(
        Math.max(0, attacker.population - attackerReserve),
        Math.max(
          1,
          Math.round(
            (
              defenderGuard * (0.12 + totalDefense * 0.05)
              + committedForce * 0.08
            ) * SIMULATION.battleAttackerLossScale,
          ),
        ),
      )
      const clashIntensity = Math.min(
        1,
        (committedForce + defenderGuard) / Math.max(14, attacker.maxPopulation * 0.4),
      )

      attacker.population = Math.max(6, attacker.population - attackerLoss)
      target.population = Math.max(0, target.population - defenseLoss)
      attacker.recentConflict = Math.min(1, attacker.recentConflict + clashIntensity * 0.48)
      attacker.conflictTargetId = target.id
      target.recentConflict = Math.min(
        1,
        target.recentConflict + clashIntensity * 0.54 + (target.terrain === 'pass' ? 0.1 : 0),
      )
      target.conflictTargetId = attacker.id

      const rawMomentum = (defenseLoss - attackerLoss) / Math.max(6, defenseLoss + attackerLoss)
      const terrainDrag = totalDefense * (target.terrain === 'pass' ? 0.76 : 1)
      const momentumSwing = clampSigned(rawMomentum * terrainDrag, 0.68)
      attacker.conflictMomentum = clampSigned(attacker.conflictMomentum * 0.62 + momentumSwing)
      target.conflictMomentum = clampSigned(target.conflictMomentum * 0.62 - momentumSwing)

      const forceBalance = clampSigned(
        attacker.population / Math.max(12, attacker.maxPopulation)
          - target.population / Math.max(12, target.maxPopulation),
        0.8,
      )
      const progressSwing = clampSigned(
        rawMomentum * 0.2 * terrainDrag + forceBalance * 0.12 + attacker.conflictMomentum * 0.05,
        0.22,
      )
      attacker.conflictProgress = clampSigned(attacker.conflictProgress * 0.78 + progressSwing)
      target.conflictProgress = clampSigned(target.conflictProgress * 0.78 - progressSwing)

      const lineProgress = clamp01((attacker.conflictProgress + -target.conflictProgress) * 0.5)
      const canCapture = target.population <= 0
        || (
          target.population <= 6
        && lineProgress >= 0.56
        && committedForce > defenderGuard * 0.5
        )
      if (canCapture) {
        target.ownerId = attacker.ownerId
        target.population = Math.max(
          SIMULATION.minOccupationGarrison,
          Math.round(committedForce * 0.58),
        )
        target.recentConflict = Math.min(
          1,
          target.recentConflict + 0.22 + (target.terrain === 'pass' ? 0.08 : 0),
        )
        target.conflictMomentum = clampSigned(target.conflictMomentum - 0.16)
        target.conflictProgress = clampSigned(target.conflictProgress - 0.3)
        target.occupationRecovery = SIMULATION.occupationRecoverySeconds
        target.occupationAnchorId = attacker.id
      }
    }

    collapseCapture(next)
  }

  sanitizeConflictTargets(next)
  updateFrontlinePressure(next)
  const dispatched = dispatchReinforcements(next)
  if (deliveredReinforcements || dispatched) {
    updateFrontlinePressure(next)
  }
  return next
}
