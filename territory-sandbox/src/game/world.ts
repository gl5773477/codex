import { FACTIONS, HEX_COLUMNS, HEX_ROWS, HEX_SIZE } from './constants'
import { axialToPixel, makeCellId, oddRNeighbors } from './hex'
import type { HexCell, World } from './types'

const rand = (seed: number) => {
  const x = Math.sin(seed * 999.91) * 43758.5453
  return x - Math.floor(x)
}

const isLandCell = (q: number, r: number, width: number, height: number) => {
  const marginX = q > 1 && q < width - 2
  const marginY = r > 1 && r < height - 2
  if (!marginX || !marginY) return false

  const centerX = width / 2
  const centerY = height / 2
  const dx = (q - centerX) / (width / 2.4)
  const dy = (r - centerY) / (height / 2.3)
  const ellipse = dx * dx + dy * dy
  const wobble = rand(q * 13.1 + r * 7.7)

  return ellipse < 1.08 + wobble * 0.12
}

const chooseCapitals = (landCells: HexCell[]) => {
  const picks: HexCell[] = []
  const minDistance = 4

  for (const faction of FACTIONS) {
    const candidate = landCells.find((cell) => {
      if (cell.ownerId !== null) return false
      return picks.every(
        (picked) =>
          Math.abs(picked.q - cell.q) + Math.abs(picked.r - cell.r) > minDistance,
      )
    })

    if (candidate) {
      candidate.ownerId = faction.id
      candidate.population = 28 + faction.id * 2
      picks.push(candidate)
    }
  }

  return picks
}

const floodOwnership = (cells: HexCell[]) => {
  let changed = true
  while (changed) {
    changed = false
    for (const cell of cells) {
      if (!cell.isLand || cell.ownerId !== null) continue
      const neighborOwners = cell.neighbors
        .map((id) => cells.find((entry) => entry.id === id))
        .filter((entry): entry is HexCell => Boolean(entry && entry.ownerId !== null))
        .map((entry) => entry.ownerId as number)

      if (neighborOwners.length > 0) {
        cell.ownerId = neighborOwners[Math.floor(rand(cell.q * 7 + cell.r * 9) * neighborOwners.length)]
        cell.population = 12 + Math.floor(rand(cell.q * 2.1 + cell.r * 5.4) * 10)
        changed = true
      }
    }
  }

  for (const cell of cells) {
    if (cell.isLand && cell.ownerId === null) {
      const fallback = FACTIONS[(cell.q + cell.r) % FACTIONS.length]
      cell.ownerId = fallback.id
      cell.population = 15
    }
  }
}

export const createWorld = (): World => {
  const cells: HexCell[] = []

  for (let r = 0; r < HEX_ROWS; r += 1) {
    for (let q = 0; q < HEX_COLUMNS; q += 1) {
      const id = makeCellId(q, r)
      const { x, y } = axialToPixel(q, r, HEX_SIZE)
      const isLand = isLandCell(q, r, HEX_COLUMNS, HEX_ROWS)

      const cell: HexCell = {
        id,
        q,
        r,
        x: x + 70,
        y: y + 80,
        isLand,
        ownerId: null,
        population: 0,
        growthRate: isLand ? 2.2 + rand(q * 10 + r) * 1.2 : 0,
        maxPopulation: isLand ? 70 + Math.floor(rand(q * 11 + r * 3) * 25) : 0,
        neighbors: oddRNeighbors(q, r)
          .filter((entry) => entry.q >= 0 && entry.q < HEX_COLUMNS && entry.r >= 0 && entry.r < HEX_ROWS)
          .map((entry) => makeCellId(entry.q, entry.r)),
        wanderSeeds: [rand(q * 3.7 + r), rand(q * 8.4 + r), rand(q * 9.9 + r)],
      }

      cells.push(cell)
    }
  }

  const landCells = cells.filter((cell) => cell.isLand)
  chooseCapitals(landCells)
  floodOwnership(cells)

  const cellMap = Object.fromEntries(cells.map((cell) => [cell.id, cell]))

  return {
    width: HEX_COLUMNS,
    height: HEX_ROWS,
    hexSize: HEX_SIZE,
    cells,
    cellMap,
    factions: FACTIONS,
    selectedCellId: null,
    tick: 0,
  }
}
