import { WORLD_STYLE } from './constants'
import { hexCorners } from './hex'
import type { World } from './types'

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

    ctx.fillStyle = 'rgba(255,255,255,0.9)'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(Math.floor(cell.population).toString(), cell.x, cell.y + 4)

    const dotCount = Math.min(8, Math.max(1, Math.floor(cell.population / 10)))
    for (let i = 0; i < dotCount; i += 1) {
      const orbit = 6 + i * 2.4
      const angle = timeMs * 0.0012 + cell.wanderSeeds[i % cell.wanderSeeds.length] * Math.PI * 2 + i
      const dx = Math.cos(angle) * orbit
      const dy = Math.sin(angle * 1.2) * (orbit * 0.65)

      ctx.beginPath()
      ctx.arc(cell.x + dx, cell.y - 16 + dy, 1.8, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(255,255,255,0.95)'
      ctx.fill()
    }
  }
}
