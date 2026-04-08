import { WORLD_STYLE } from './constants'
import { hexCorners } from './hex'
import type { HexCell, ReinforcementTransfer, World } from './types'

type RenderPoint = {
  x: number
  y: number
}

type PolylineMetrics = {
  segmentLengths: number[]
  totalLength: number
}

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value))

const withAlpha = (hex: string, alpha: number) => {
  const value = hex.replace('#', '')
  const normalized = value.length === 3
    ? value.split('').map((part) => part + part).join('')
    : value

  const red = Number.parseInt(normalized.slice(0, 2), 16)
  const green = Number.parseInt(normalized.slice(2, 4), 16)
  const blue = Number.parseInt(normalized.slice(4, 6), 16)

  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}

const getHexBoundaryRadius = (size: number, angle: number) => {
  const inRadius = size * Math.cos(Math.PI / 6)
  const sector = ((angle + Math.PI / 6) % (Math.PI / 3) + Math.PI / 3) % (Math.PI / 3) - Math.PI / 6
  return inRadius / Math.cos(sector)
}

const getPopulationDotOffset = (
  cell: HexCell,
  dotIndex: number,
  timeMs: number,
  size: number,
) => {
  const seedA = cell.wanderSeeds[dotIndex % cell.wanderSeeds.length] + dotIndex * 0.173
  const seedB = cell.wanderSeeds[(dotIndex + 1) % cell.wanderSeeds.length] + dotIndex * 0.291
  const seedC = cell.wanderSeeds[(dotIndex + 2) % cell.wanderSeeds.length] + dotIndex * 0.419
  const drift = timeMs * (0.00011 + seedA * 0.00004)
  const angle = seedA * Math.PI * 2
    + drift * (1.35 + seedB * 1.15)
    + Math.sin(drift * 0.72 + seedC * Math.PI * 2) * 1.18
  const radialMix = 0.2 + 0.72 * (
    0.5
    + 0.5 * Math.sin(
      timeMs * (0.00027 + seedB * 0.00006)
        + seedC * 5.8
        + Math.cos(drift * 1.06),
    )
  )
  const boundary = getHexBoundaryRadius(size * 0.82, angle)
  const radius = boundary * radialMix

  return {
    dx: Math.cos(angle) * radius,
    dy: Math.sin(angle) * radius,
  }
}

const getConflictVisualIntensity = (cell: HexCell) => {
  return clamp(
    Math.max(
      cell.recentConflict,
      cell.conflictTargetId ? 0.11 : 0,
      Math.abs(cell.conflictMomentum) * 0.5,
      Math.abs(cell.conflictProgress) * 0.58,
    ),
    0,
    1,
  )
}

const drawHex = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  fill: string,
  stroke: string,
  lineWidth = 1,
) => {
  const corners = hexCorners(x, y, size)
  ctx.beginPath()
  ctx.moveTo(corners[0][0], corners[0][1])
  corners.slice(1).forEach(([cx, cy]) => ctx.lineTo(cx, cy))
  ctx.closePath()
  ctx.fillStyle = fill
  ctx.fill()
  ctx.strokeStyle = stroke
  ctx.lineWidth = lineWidth
  ctx.stroke()
}

const getSharedEdge = (cell: HexCell, neighbor: HexCell, size: number) => {
  const corners = hexCorners(cell.x, cell.y, size)
  let bestEdge: [[number, number], [number, number]] = [corners[0], corners[1]]
  let bestDistance = Number.POSITIVE_INFINITY

  for (let i = 0; i < corners.length; i += 1) {
    const start = corners[i]
    const end = corners[(i + 1) % corners.length]
    const midX = (start[0] + end[0]) / 2
    const midY = (start[1] + end[1]) / 2
    const distance = (midX - neighbor.x) ** 2 + (midY - neighbor.y) ** 2

    if (distance < bestDistance) {
      bestDistance = distance
      bestEdge = [start, end]
    }
  }

  return bestEdge
}

const drawRidgeAccent = (
  ctx: CanvasRenderingContext2D,
  cell: HexCell,
  size: number,
) => {
  ctx.save()
  ctx.strokeStyle = 'rgba(226, 232, 240, 0.2)'
  ctx.lineWidth = 1.5
  for (let i = -1; i <= 1; i += 1) {
    ctx.beginPath()
    ctx.moveTo(cell.x - size * 0.4 + i * 7, cell.y + size * 0.1)
    ctx.lineTo(cell.x - size * 0.1 + i * 7, cell.y - size * 0.35)
    ctx.lineTo(cell.x + size * 0.22 + i * 7, cell.y + size * 0.04)
    ctx.stroke()
  }
  ctx.restore()
}

const drawPassAccent = (
  ctx: CanvasRenderingContext2D,
  cell: HexCell,
  size: number,
) => {
  ctx.save()
  ctx.fillStyle = 'rgba(33, 41, 55, 0.5)'
  ctx.fillRect(cell.x - size * 0.48, cell.y - size * 0.32, size * 0.18, size * 0.64)
  ctx.fillRect(cell.x + size * 0.3, cell.y - size * 0.32, size * 0.18, size * 0.64)
  ctx.fillStyle = 'rgba(250, 222, 166, 0.45)'
  ctx.fillRect(cell.x - size * 0.08, cell.y - size * 0.24, size * 0.16, size * 0.48)
  ctx.restore()
}

const drawCellInnerHex = (
  ctx: CanvasRenderingContext2D,
  cell: HexCell,
  size: number,
) => {
  const pressureIntensity = cell.frontlinePressure
  const conflictIntensity = getConflictVisualIntensity(cell)
  if (pressureIntensity < 0.1 && conflictIntensity < 0.08) return

  if (pressureIntensity >= 0.1) {
    ctx.save()
    drawHex(
      ctx,
      cell.x,
      cell.y,
      size * (0.8 + pressureIntensity * 0.04),
      `rgba(255, 196, 112, ${0.02 + pressureIntensity * 0.07})`,
      `rgba(255, 156, 82, ${0.06 + pressureIntensity * 0.14})`,
      0.8 + pressureIntensity * 1.1,
    )
    ctx.restore()
  }

  if (conflictIntensity < 0.08) return

  ctx.save()
  drawHex(
    ctx,
    cell.x,
    cell.y,
    size * (0.58 + conflictIntensity * 0.08),
    `rgba(255, 112, 56, ${0.06 + conflictIntensity * 0.14})`,
    `rgba(255, 232, 204, ${0.12 + conflictIntensity * 0.22})`,
    1.1 + conflictIntensity * 1.6,
  )
  ctx.restore()

  ctx.save()
  drawHex(
    ctx,
    cell.x,
    cell.y,
    size * (0.34 + conflictIntensity * 0.05),
    `rgba(255, 242, 226, ${0.05 + conflictIntensity * 0.08})`,
    `rgba(255, 248, 236, ${0.1 + conflictIntensity * 0.14})`,
    0.7 + conflictIntensity,
  )
  ctx.restore()
}

const drawBattleMarker = (
  ctx: CanvasRenderingContext2D,
  midX: number,
  midY: number,
  conflictIntensity: number,
) => {
  ctx.save()
  ctx.translate(midX, midY)
  ctx.font = `${7 + conflictIntensity * 1.6}px "Segoe UI Symbol", "Noto Sans Symbols 2", "Apple Symbols", sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = `rgba(255, 243, 224, ${0.74 + conflictIntensity * 0.18})`
  ctx.shadowColor = 'rgba(24, 28, 34, 0.22)'
  ctx.shadowBlur = 1
  ctx.fillText('⚔', 0, 0)
  ctx.restore()
}

const drawArrowHead = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  angle: number,
  size: number,
  color: string,
) => {
  ctx.save()
  ctx.translate(x, y)
  ctx.rotate(angle)
  ctx.beginPath()
  ctx.moveTo(size, 0)
  ctx.lineTo(-size * 0.65, size * 0.48)
  ctx.lineTo(-size * 0.65, -size * 0.48)
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
  ctx.restore()
}

const drawTrendArrow = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  angle: number,
  size: number,
  alpha: number,
) => {
  drawArrowHead(ctx, x, y, angle, size, `rgba(255,255,255,${alpha})`)
  drawArrowHead(
    ctx,
    x - Math.cos(angle) * size * 1.05,
    y - Math.sin(angle) * size * 1.05,
    angle,
    size * 0.82,
    `rgba(255,255,255,${alpha * 0.68})`,
  )
}

const buildPolylineMetrics = (points: RenderPoint[]): PolylineMetrics => {
  const segmentLengths: number[] = []
  let totalLength = 0

  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index]
    const to = points[index + 1]
    const length = Math.hypot(to.x - from.x, to.y - from.y)
    segmentLengths.push(length)
    totalLength += length
  }

  return { segmentLengths, totalLength }
}

export const getReinforcementTravelProgress = (
  transfer: Pick<ReinforcementTransfer, 'currentHop' | 'elapsedMs' | 'durationMs' | 'pathCellIds'>,
) => {
  const hopCount = Math.max(1, transfer.pathCellIds.length - 1)
  const hopProgress = clamp(transfer.elapsedMs / Math.max(1, transfer.durationMs), 0, 1)
  return clamp((transfer.currentHop + hopProgress) / hopCount, 0, 1)
}

const samplePolylineAtDistance = (
  points: RenderPoint[],
  metrics: PolylineMetrics,
  distance: number,
) => {
  if (points.length < 2 || metrics.totalLength <= 0) {
    return {
      x: points[0]?.x ?? 0,
      y: points[0]?.y ?? 0,
      angle: 0,
    }
  }

  let remaining = clamp(distance, 0, metrics.totalLength)

  for (let index = 0; index < metrics.segmentLengths.length; index += 1) {
    const segmentLength = metrics.segmentLengths[index]
    const from = points[index]
    const to = points[index + 1]
    const dx = to.x - from.x
    const dy = to.y - from.y

    if (remaining <= segmentLength || index === metrics.segmentLengths.length - 1) {
      const t = segmentLength <= 0 ? 1 : clamp(remaining / segmentLength, 0, 1)
      return {
        x: from.x + dx * t,
        y: from.y + dy * t,
        angle: Math.atan2(dy, dx),
      }
    }

    remaining -= segmentLength
  }

  const from = points[points.length - 2]
  const to = points[points.length - 1]
  return {
    x: to.x,
    y: to.y,
    angle: Math.atan2(to.y - from.y, to.x - from.x),
  }
}

const slicePolyline = (
  points: RenderPoint[],
  metrics: PolylineMetrics,
  startDistance: number,
  endDistance: number,
) => {
  const clampedStart = clamp(startDistance, 0, metrics.totalLength)
  const clampedEnd = clamp(endDistance, 0, metrics.totalLength)
  const start = samplePolylineAtDistance(points, metrics, clampedStart)
  const end = samplePolylineAtDistance(points, metrics, clampedEnd)

  if (clampedEnd <= clampedStart) {
    return [{ x: start.x, y: start.y }]
  }

  const sliced = [{ x: start.x, y: start.y }]
  let traversed = 0

  for (let index = 1; index < points.length - 1; index += 1) {
    traversed += metrics.segmentLengths[index - 1] ?? 0
    if (traversed > clampedStart && traversed < clampedEnd) {
      sliced.push(points[index])
    }
  }

  sliced.push({ x: end.x, y: end.y })
  return sliced
}

const buildReinforcementRoutePoints = (
  transfer: ReinforcementTransfer,
  world: World,
) => {
  const points: RenderPoint[] = []

  for (const cellId of transfer.pathCellIds) {
    const cell = world.cellMap[cellId]
    if (!cell || !cell.isLand) return null
    points.push({ x: cell.x, y: cell.y })
  }

  return points.length >= 2 ? points : null
}

const drawReinforcements = (
  ctx: CanvasRenderingContext2D,
  world: World,
) => {
  if (!world.reinforcements.length) return

  for (const transfer of world.reinforcements) {
    const faction = world.factions.find((entry) => entry.id === transfer.factionId)
    const routePoints = buildReinforcementRoutePoints(transfer, world)
    if (!faction || !routePoints) continue

    const metrics = buildPolylineMetrics(routePoints)
    if (metrics.totalLength <= 0) continue

    const travelDistance = metrics.totalLength * getReinforcementTravelProgress(transfer)
    const trailLength = clamp(
      world.hexSize * (0.72 + transfer.amount * 0.045),
      world.hexSize * 0.58,
      world.hexSize * 1.6,
    )
    const head = samplePolylineAtDistance(routePoints, metrics, travelDistance)
    const activePath = slicePolyline(
      routePoints,
      metrics,
      Math.max(0, travelDistance - trailLength),
      travelDistance,
    )

    ctx.save()
    ctx.beginPath()
    ctx.moveTo(routePoints[0].x, routePoints[0].y)
    for (const point of routePoints.slice(1)) {
      ctx.lineTo(point.x, point.y)
    }
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.lineWidth = 1.15 + transfer.amount * 0.035
    ctx.strokeStyle = 'rgba(255,255,255,0.18)'
    ctx.shadowColor = 'rgba(255,255,255,0.08)'
    ctx.shadowBlur = 6
    ctx.stroke()
    ctx.restore()

    ctx.save()
    ctx.beginPath()
    ctx.moveTo(activePath[0].x, activePath[0].y)
    for (const point of activePath.slice(1)) {
      ctx.lineTo(point.x, point.y)
    }
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.lineWidth = 1.55 + transfer.amount * 0.04
    ctx.strokeStyle = 'rgba(255,255,255,0.68)'
    ctx.shadowColor = 'rgba(255,255,255,0.22)'
    ctx.shadowBlur = 8
    ctx.stroke()
    ctx.restore()

    ctx.save()
    ctx.shadowColor = 'rgba(255,255,255,0.28)'
    ctx.shadowBlur = 10
    drawTrendArrow(ctx, head.x, head.y, head.angle, 4.9 + transfer.amount * 0.06, 0.74)
    ctx.restore()
  }
}

const drawFrontlineBorders = (
  ctx: CanvasRenderingContext2D,
  world: World,
  timeMs: number,
) => {
  const visited = new Set<string>()

  for (const cell of world.cells) {
    if (!cell.isLand || cell.ownerId === null) continue

    for (const neighborId of cell.neighbors) {
      const neighbor = world.cellMap[neighborId]
      if (!neighbor || !neighbor.isLand || neighbor.ownerId === null || neighbor.ownerId === cell.ownerId) {
        continue
      }

      const edgeKey = [cell.id, neighbor.id].sort().join('|')
      if (visited.has(edgeKey)) continue
      visited.add(edgeKey)

      const pressureIntensity = Math.max(cell.frontlinePressure, neighbor.frontlinePressure)
      const conflictIntensity = Math.max(
        getConflictVisualIntensity(cell),
        getConflictVisualIntensity(neighbor),
      )
      const hasConflictLink = cell.conflictTargetId === neighbor.id || neighbor.conflictTargetId === cell.id
      if (pressureIntensity < 0.1 && (!hasConflictLink || conflictIntensity < 0.06)) continue

      const [[startX, startY], [endX, endY]] = getSharedEdge(cell, neighbor, world.hexSize)

      if (pressureIntensity >= 0.1) {
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(startX, startY)
        ctx.lineTo(endX, endY)
        ctx.lineCap = 'round'
        ctx.lineWidth = 1.2 + pressureIntensity * 1.5
        ctx.strokeStyle = `rgba(255, 150, 86, ${0.08 + pressureIntensity * 0.16})`
        ctx.shadowColor = `rgba(255, 144, 74, ${0.12 + pressureIntensity * 0.2})`
        ctx.shadowBlur = 4 + pressureIntensity * 8
        ctx.stroke()
        ctx.restore()
      }

      if (conflictIntensity >= 0.06 && hasConflictLink) {
        const dx = neighbor.x - cell.x
        const dy = neighbor.y - cell.y
        const distance = Math.hypot(dx, dy) || 1
        const inset = world.hexSize * 0.45
        const startX = cell.x + (dx / distance) * inset
        const startY = cell.y + (dy / distance) * inset
        const endX = neighbor.x - (dx / distance) * inset
        const endY = neighbor.y - (dy / distance) * inset
        const sourcePush = cell.conflictTargetId === neighbor.id ? cell.conflictMomentum : 0
        const opposingPush = neighbor.conflictTargetId === cell.id ? -neighbor.conflictMomentum : 0
        const activePushes = Number(cell.conflictTargetId === neighbor.id) + Number(neighbor.conflictTargetId === cell.id)
        const advantage = clamp((sourcePush + opposingPush) / activePushes, -0.92, 0.92)
        const sourceProgress = cell.conflictTargetId === neighbor.id ? cell.conflictProgress : 0
        const opposingProgress = neighbor.conflictTargetId === cell.id ? -neighbor.conflictProgress : 0
        const progress = clamp((sourceProgress + opposingProgress) / activePushes, -0.96, 0.96)
        const centerShift = distance * 0.22 * progress
        const midX = (startX + endX) / 2 + (dx / distance) * centerShift
        const midY = (startY + endY) / 2 + (dy / distance) * centerShift

        ctx.save()
        ctx.beginPath()
        ctx.moveTo(startX, startY)
        ctx.lineTo(endX, endY)
        ctx.lineCap = 'round'
        ctx.lineWidth = 1.1 + conflictIntensity * 2.2
        ctx.strokeStyle = `rgba(255, 198, 132, ${0.22 + conflictIntensity * 0.32})`
        ctx.shadowColor = `rgba(255, 96, 42, ${0.24 + conflictIntensity * 0.34})`
        ctx.shadowBlur = 8 + conflictIntensity * 14
        ctx.stroke()
        ctx.restore()

        if (Math.abs(progress) >= 0.05) {
          const dominantLength = clamp(distance * (0.1 + Math.abs(progress) * 0.18), 5, 16)
          const dominantX = midX + (dx / distance) * Math.sign(progress) * dominantLength
          const dominantY = midY + (dy / distance) * Math.sign(progress) * dominantLength

          ctx.save()
          ctx.beginPath()
          ctx.moveTo(midX, midY)
          ctx.lineTo(dominantX, dominantY)
          ctx.lineCap = 'round'
          ctx.lineWidth = 1.4 + conflictIntensity * 1.4 + Math.abs(progress) * 1.1
          ctx.strokeStyle = `rgba(255, 248, 232, ${0.24 + conflictIntensity * 0.22 + Math.abs(progress) * 0.22})`
          ctx.shadowColor = `rgba(255, 188, 120, ${0.14 + Math.abs(progress) * 0.24})`
          ctx.shadowBlur = 4 + conflictIntensity * 8
          ctx.stroke()
          ctx.restore()
        }

        if (Math.abs(advantage) >= 0.08) {
          const surgeX = midX + (dx / distance) * clamp(distance * 0.08 * advantage, -8, 8)
          const surgeY = midY + (dy / distance) * clamp(distance * 0.08 * advantage, -8, 8)

          ctx.save()
          ctx.beginPath()
          ctx.moveTo(midX, midY)
          ctx.lineTo(surgeX, surgeY)
          ctx.lineCap = 'round'
          ctx.lineWidth = 0.9 + conflictIntensity * 0.9 + Math.abs(advantage) * 0.6
          ctx.strokeStyle = `rgba(255, 229, 196, ${0.16 + Math.abs(advantage) * 0.18})`
          ctx.stroke()
          ctx.restore()
        }

        drawBattleMarker(
          ctx,
          midX,
          midY,
          conflictIntensity,
        )
      }
    }
  }
}

export const renderWorld = (
  canvas: HTMLCanvasElement,
  world: World,
  timeMs: number,
) => {
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = WORLD_STYLE.background
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  for (const cell of world.cells) {
    const faction = world.factions.find((entry) => entry.id === cell.ownerId)
    const fill = cell.terrain === 'ridge'
      ? WORLD_STYLE.ridge
      : cell.terrain === 'sea'
        ? WORLD_STYLE.sea
        : cell.terrain === 'pass'
          ? faction?.color ?? WORLD_STYLE.pass
          : faction?.color ?? WORLD_STYLE.neutralLand

    drawHex(
      ctx,
      cell.x,
      cell.y,
      world.hexSize,
      fill,
      cell.id === world.selectedCellId ? WORLD_STYLE.selected : WORLD_STYLE.outline,
      cell.id === world.selectedCellId ? 2.5 : 1,
    )

    if (cell.terrain === 'ridge') {
      drawRidgeAccent(ctx, cell, world.hexSize)
      continue
    }

    if (cell.terrain === 'pass') {
      drawPassAccent(ctx, cell, world.hexSize)
    }

    if (!cell.isLand) continue

    drawCellInnerHex(ctx, cell, world.hexSize)

    ctx.fillStyle = 'rgba(255,255,255,0.9)'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(Math.floor(cell.population).toString(), cell.x, cell.y + 4)

    const dotCount = Math.min(8, Math.max(1, Math.floor(cell.population / 10)))
    const dotAlpha = 0.82 + cell.recentConflict * 0.18
    for (let i = 0; i < dotCount; i += 1) {
      const { dx, dy } = getPopulationDotOffset(cell, i, timeMs, world.hexSize)

      ctx.beginPath()
      ctx.arc(cell.x + dx, cell.y + dy, 1.8, 0, Math.PI * 2)
      ctx.fillStyle = cell.recentConflict > 0.18
        ? `rgba(255, 214, 170, ${dotAlpha})`
        : `rgba(255,255,255,${dotAlpha})`
      ctx.fill()
    }
  }

  drawReinforcements(ctx, world)
  drawFrontlineBorders(ctx, world, timeMs)

  if (world.selectedCellId) {
    const selectedCell = world.cellMap[world.selectedCellId]
    if (selectedCell) {
      drawHex(
        ctx,
        selectedCell.x,
        selectedCell.y,
        world.hexSize,
        'rgba(255,255,255,0)',
        WORLD_STYLE.selected,
        2.5,
      )
    }
  }
}
