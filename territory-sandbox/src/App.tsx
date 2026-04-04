import { useEffect, useMemo, useRef, useState } from 'react'
import { createWorld } from './game/world'
import { addPopulationToCell, selectCell, stepWorld } from './game/simulation'
import { renderWorld } from './game/render'
import { pointInHex } from './game/hex'
import { HEX_SIZE } from './game/constants'
import type { World } from './game/types'

const SPEEDS = [0, 1, 2, 4]

export default function App() {
  const [world, setWorld] = useState<World>(() => createWorld())
  const [speedIndex, setSpeedIndex] = useState(1)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const lastRef = useRef<number>(performance.now())

  const selectedCell = useMemo(
    () => (world.selectedCellId ? world.cellMap[world.selectedCellId] : null),
    [world],
  )

  useEffect(() => {
    let frame = 0

    const loop = (now: number) => {
      const elapsed = now - lastRef.current
      lastRef.current = now

      if (SPEEDS[speedIndex] > 0) {
        setWorld((current) => stepWorld(current, elapsed * SPEEDS[speedIndex]))
      }

      if (canvasRef.current) {
        renderWorld(canvasRef.current, world, now)
      }

      frame = window.requestAnimationFrame(loop)
    }

    frame = window.requestAnimationFrame(loop)
    return () => window.cancelAnimationFrame(frame)
  }, [speedIndex, world])

  useEffect(() => {
    if (canvasRef.current) {
      renderWorld(canvasRef.current, world, performance.now())
    }
  }, [world])

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top

    const hit = world.cells.find(
      (cell) =>
        pointInHex(x, y, cell.x, cell.y, HEX_SIZE) &&
        Math.abs(x - cell.x) < HEX_SIZE * 1.1 &&
        Math.abs(y - cell.y) < HEX_SIZE,
    )

    setWorld((current) => selectCell(current, hit?.id ?? null))
  }

  const selectedFaction = selectedCell
    ? world.factions.find((faction) => faction.id === selectedCell.ownerId)
    : null

  const landCount = world.cells.filter((cell) => cell.isLand).length
  const factionStats = world.factions
    .map((faction) => {
      const cells = world.cells.filter((cell) => cell.ownerId === faction.id)
      const population = cells.reduce((sum, cell) => sum + cell.population, 0)
      return {
        faction,
        territory: cells.length,
        population: Math.floor(population),
      }
    })
    .sort((a, b) => b.territory - a.territory)

  return (
    <div className="app-shell">
      <aside className="side-panel">
        <h1>大陆演化沙盘</h1>
        <p>上帝视角观察国家扩张，也可以对选中领地施加神力。</p>

        <div className="toolbar">
          {SPEEDS.map((speed, index) => (
            <button
              key={speed}
              className={index === speedIndex ? 'active' : ''}
              onClick={() => setSpeedIndex(index)}
            >
              {speed === 0 ? '暂停' : `${speed}x`}
            </button>
          ))}
        </div>

        <button
          className="god-button"
          disabled={!selectedCell || !selectedCell.isLand}
          onClick={() => {
            if (!selectedCell) return
            setWorld((current) => addPopulationToCell(current, selectedCell.id, 20))
          }}
        >
          神赐人口 +20
        </button>

        <section className="panel-block">
          <h2>世界概况</h2>
          <div className="stat-row"><span>陆地格数</span><strong>{landCount}</strong></div>
          <div className="stat-row"><span>国家数量</span><strong>{world.factions.length}</strong></div>
        </section>

        <section className="panel-block">
          <h2>领地详情</h2>
          {selectedCell ? (
            <>
              <div className="stat-row"><span>坐标</span><strong>{selectedCell.q}, {selectedCell.r}</strong></div>
              <div className="stat-row"><span>归属</span><strong>{selectedFaction?.name ?? '海洋'}</strong></div>
              <div className="stat-row"><span>人口</span><strong>{Math.floor(selectedCell.population)}</strong></div>
              <div className="stat-row"><span>增长</span><strong>{selectedCell.growthRate.toFixed(1)}/s</strong></div>
              <div className="stat-row"><span>上限</span><strong>{selectedCell.maxPopulation}</strong></div>
            </>
          ) : (
            <p className="muted">点击地图上的任意格子查看详情。</p>
          )}
        </section>

        <section className="panel-block">
          <h2>势力排名</h2>
          <div className="leaderboard">
            {factionStats.map(({ faction, territory, population }) => (
              <div key={faction.id} className="leader-item">
                <span className="swatch" style={{ background: faction.color }} />
                <span>{faction.name}</span>
                <strong>{territory} 地 / {population} 人</strong>
              </div>
            ))}
          </div>
        </section>
      </aside>

      <main className="canvas-wrap">
        <canvas ref={canvasRef} width={980} height={720} onClick={handleCanvasClick} />
      </main>
    </div>
  )
}
