import { WORLD_STYLE } from './constants'
import { hexCorners } from './hex'
import type { HexCell, World } from './types'

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

const drawFrontlineAura = (
  ctx: CanvasRenderingContext2D,
  cell: HexCell,
  size: number,
  timeMs: number,
) => {
  const intensity = Math.max(cell.frontlinePressure, cell.recentConflict)
  if (intensity < 0.08) return

  const pulse = 0.72 + Math.sin(timeMs * 0.006 + cell.wanderSeeds[0] * Math.PI * 2) * 0.28
  const auraSize = size * (0.78 + intensity * 0.08 + pulse * 0.02)

  ctx.save()
  drawHex(
    ctx,
    cell.x,
    cell.y,
    auraSize,
    `rgba(255, 246, 214, ${0.02 + intensity * 0.05})`,
    `rgba(255, 218, 168, ${0.08 + intensity * 0.22})`,
    1.1 + intensity * 1.4,
  )
  ctx.restore()

  if (cell.recentConflict < 0.18) return

  ctx.save()
  ctx.beginPath()
  ctx.arc(
    cell.x,
    cell.y - 6,
    6 + cell.recentConflict * 7 + pulse * 2,
    0,
    Math.PI * 2,
  )
  ctx.fillStyle = `rgba(255, 156, 98, ${0.05 + cell.recentConflict * 0.16})`
  ctx.fill()
  ctx.restore()
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

      const intensity = Math.max(
        cell.frontlinePressure,
        neighbor.frontlinePressure,
        cell.recentConflict,
        neighbor.recentConflict,
      )
      const [[startX, startY], [endX, endY]] = getSharedEdge(cell, neighbor, world.hexSize)
      const dashOffset = -(timeMs * (0.015 + intensity * 0.03))

      ctx.save()
      ctx.beginPath()
      ctx.moveTo(startX, startY)
      ctx.lineTo(endX, endY)
      ctx.lineCap = 'round'
      ctx.setLineDash([10, 8])
      ctx.lineDashOffset = dashOffset
      ctx.lineWidth = 2.2 + intensity * 3.6
      ctx.strokeStyle = `rgba(255, 134, 66, ${0.24 + intensity * 0.34})`
      ctx.shadowColor = `rgba(255, 134, 66, ${0.35 + intensity * 0.35})`
      ctx.shadowBlur = 10 + intensity * 18
      ctx.stroke()
      ctx.restore()

      ctx.save()
      ctx.beginPath()
      ctx.moveTo(startX, startY)
      ctx.lineTo(endX, endY)
      ctx.lineCap = 'round'
      ctx.lineWidth = 0.9 + intensity * 1.6
      ctx.strokeStyle = `rgba(255, 246, 219, ${0.32 + intensity * 0.34})`
      ctx.stroke()
      ctx.restore()
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
    const fill = !cell.isLand
      ? WORLD_STYLE.sea
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

    if (!cell.isLand) continue

    drawFrontlineAura(ctx, cell, world.hexSize, timeMs)

    ctx.fillStyle = 'rgba(255,255,255,0.9)'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(Math.floor(cell.population).toString(), cell.x, cell.y + 4)

    const dotCount = Math.min(8, Math.max(1, Math.floor(cell.population / 10)))
    const dotAlpha = 0.82 + cell.recentConflict * 0.18
    for (let i = 0; i < dotCount; i += 1) {
      const orbit = 6 + i * 2.4
      const angle = timeMs * 0.0012 + cell.wanderSeeds[i % cell.wanderSeeds.length] * Math.PI * 2 + i
      const dx = Math.cos(angle) * orbit
      const dy = Math.sin(angle * 1.2) * (orbit * 0.65)

      ctx.beginPath()
      ctx.arc(cell.x + dx, cell.y - 16 + dy, 1.8, 0, Math.PI * 2)
      ctx.fillStyle = cell.recentConflict > 0.18
        ? `rgba(255, 214, 170, ${dotAlpha})`
        : `rgba(255,255,255,${dotAlpha})`
      ctx.fill()
    }
  }

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
