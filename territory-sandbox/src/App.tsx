import { useEffect, useMemo, useRef, useState } from 'react'
import { createWorld } from './game/world'
import { addPopulationToCell, selectCell, stepWorld } from './game/simulation'
import { renderWorld } from './game/render'
import { pointInHex } from './game/hex'
import { HEX_SIZE } from './game/constants'
import type { World } from './game/types'

const SPEEDS = [0, 1, 2, 4]

const describeFrontline = (pressure: number, conflict: number) => {
  if (conflict >= 0.52) return '激烈交战'
  if (conflict >= 0.24) return '战线爆燃'
  if (pressure >= 0.48) return '高压对峙'
  if (pressure >= 0.22) return '边境接触'
  return '腹地平静'
}

const describeMomentum = (progress: number, momentum: number, conflict: number) => {
  if (conflict < 0.1) return '尚未接战'
  if (progress >= 0.62) return '逼近崩口'
  if (progress <= -0.62) return '防线濒危'
  if (momentum >= 0.22) return '正在推进'
  if (momentum <= -0.22) return '承受反扑'
  return '前线拉锯'
}

const describeTerrain = (terrain: World['cells'][number]['terrain']) => {
  if (terrain === 'pass') return '隘口'
  if (terrain === 'ridge') return '山脊'
  if (terrain === 'sea') return '海洋'
  return '平原'
}

export default function App() {
  const [world, setWorld] = useState<World>(() => createWorld())
  const [speedIndex, setSpeedIndex] = useState(1)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const worldRef = useRef(world)
  const speedRef = useRef(SPEEDS[speedIndex])
  const lastRef = useRef<number | null>(null)

  const selectedCell = useMemo(
    () => (world.selectedCellId ? world.cellMap[world.selectedCellId] : null),
    [world],
  )
  const reinforcementStats = useMemo(() => {
    const incoming = new Map<string, { count: number; amount: number }>()
    const outgoing = new Map<string, { count: number; amount: number }>()

    for (const transfer of world.reinforcements) {
      const target = incoming.get(transfer.toCellId) ?? { count: 0, amount: 0 }
      target.count += 1
      target.amount += transfer.amount
      incoming.set(transfer.toCellId, target)

      const source = outgoing.get(transfer.fromCellId) ?? { count: 0, amount: 0 }
      source.count += 1
      source.amount += transfer.amount
      outgoing.set(transfer.fromCellId, source)
    }

    return { incoming, outgoing }
  }, [world.reinforcements])

  useEffect(() => {
    worldRef.current = world
  }, [world])

  useEffect(() => {
    speedRef.current = SPEEDS[speedIndex]
  }, [speedIndex])

  useEffect(() => {
    let frame = 0

    const loop = (now: number) => {
      const previous = lastRef.current ?? now
      const elapsed = Math.min(now - previous, 80)
      lastRef.current = now
      let nextWorld = worldRef.current

      if (speedRef.current > 0) {
        nextWorld = stepWorld(nextWorld, elapsed * speedRef.current)
        worldRef.current = nextWorld
        setWorld(nextWorld)
      }

      if (canvasRef.current) {
        renderWorld(canvasRef.current, nextWorld, now)
      }

      frame = window.requestAnimationFrame(loop)
    }

    frame = window.requestAnimationFrame(loop)
    return () => {
      window.cancelAnimationFrame(frame)
      lastRef.current = null
    }
  }, [])

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

    const latestHit = worldRef.current.cells.find(
      (cell) =>
        pointInHex(x, y, cell.x, cell.y, HEX_SIZE) &&
        Math.abs(x - cell.x) < HEX_SIZE * 1.1 &&
        Math.abs(y - cell.y) < HEX_SIZE,
    )

    setWorld((current) => {
      const next = selectCell(current, latestHit?.id ?? null)
      worldRef.current = next
      return next
    })
  }

  const selectedFaction = selectedCell
    ? world.factions.find((faction) => faction.id === selectedCell.ownerId)
    : null

  const currentSpeed = SPEEDS[speedIndex]
  const landCount = world.cells.filter((cell) => cell.isLand).length
  const passCount = world.cells.filter((cell) => cell.terrain === 'pass').length
  const frontlineCount = world.cells.filter(
    (cell) => cell.frontlinePressure >= 0.34 || cell.recentConflict >= 0.16,
  ).length
  const conflictHotspots = world.cells.filter((cell) => cell.recentConflict >= 0.24).length
  const activeReinforcements = world.reinforcements.length
  const activeBattleLines = new Set(
    world.cells
      .filter((cell) => {
        if (cell.recentConflict < 0.12 || !cell.conflictTargetId || cell.ownerId === null) return false
        const opponent = world.cellMap[cell.conflictTargetId]
        return Boolean(opponent && opponent.ownerId !== null && opponent.ownerId !== cell.ownerId)
      })
      .map((cell) => [cell.id, cell.conflictTargetId].sort().join('|')),
  ).size
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
  const selectedIncoming = selectedCell ? reinforcementStats.incoming.get(selectedCell.id) : null
  const selectedOutgoing = selectedCell ? reinforcementStats.outgoing.get(selectedCell.id) : null

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
            setWorld((current) => {
              const next = addPopulationToCell(current, selectedCell.id, 20)
              worldRef.current = next
              return next
            })
          }}
        >
          神赐人口 +20
        </button>

        <section className="panel-block">
          <h2>世界概况</h2>
          <div className="stat-row"><span>陆地格数</span><strong>{landCount}</strong></div>
          <div className="stat-row"><span>国家数量</span><strong>{world.factions.length}</strong></div>
          <div className="stat-row"><span>当前速度</span><strong>{currentSpeed === 0 ? '暂停' : `${currentSpeed}x`}</strong></div>
          <div className="stat-row"><span>隘口格数</span><strong>{passCount}</strong></div>
          <div className="stat-row"><span>前线格数</span><strong>{frontlineCount}</strong></div>
          <div className="stat-row"><span>对抗连线</span><strong>{activeBattleLines}</strong></div>
          <div className="stat-row"><span>战火热点</span><strong>{conflictHotspots}</strong></div>
          <div className="stat-row"><span>在途增援</span><strong>{activeReinforcements}</strong></div>
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

      <aside className="detail-dock">
        <section
          className={[
            'detail-card',
            selectedCell?.isLand ? 'is-active' : '',
            selectedCell?.recentConflict && selectedCell.recentConflict >= 0.24 ? 'is-hot' : '',
          ].filter(Boolean).join(' ')}
        >
          <div className="detail-header">
            <div>
              <p className="detail-kicker">观察焦点</p>
              <h2>领地详情</h2>
            </div>
            <span
              className="detail-faction"
              style={{ background: selectedFaction?.color ?? 'rgba(148, 163, 184, 0.65)' }}
            />
          </div>

          {selectedCell ? (
            <>
              <div className="detail-status">
                <span>{selectedCell.isLand ? (selectedFaction?.name ?? '无主领地') : describeTerrain(selectedCell.terrain)}</span>
                <strong>
                  {selectedCell.isLand
                    ? describeFrontline(selectedCell.frontlinePressure, selectedCell.recentConflict)
                    : selectedCell.terrain === 'ridge' ? '地形阻断' : '不可扩张'}
                </strong>
              </div>

              <div className="detail-grid">
                <div className="detail-row"><span>坐标</span><strong>{selectedCell.q}, {selectedCell.r}</strong></div>
                <div className="detail-row"><span>地形</span><strong>{describeTerrain(selectedCell.terrain)}</strong></div>
                <div className="detail-row"><span>人口</span><strong>{Math.floor(selectedCell.population)}</strong></div>
                <div className="detail-row"><span>增长</span><strong>{selectedCell.growthRate.toFixed(1)}/s</strong></div>
                <div className="detail-row"><span>上限</span><strong>{selectedCell.maxPopulation}</strong></div>
                <div className="detail-row"><span>前线压力</span><strong>{Math.round(selectedCell.frontlinePressure * 100)}%</strong></div>
                <div className="detail-row"><span>战线态势</span><strong>{describeMomentum(selectedCell.conflictProgress, selectedCell.conflictMomentum, selectedCell.recentConflict)}</strong></div>
                <div className="detail-row"><span>战线位移</span><strong>{Math.round(selectedCell.conflictProgress * 100)}%</strong></div>
                <div className="detail-row"><span>战火余温</span><strong>{Math.round(selectedCell.recentConflict * 100)}%</strong></div>
                <div className="detail-row"><span>在途补兵</span><strong>{selectedIncoming ? `${selectedIncoming.amount}（${selectedIncoming.count}股）` : '无'}</strong></div>
                <div className="detail-row"><span>后方调出</span><strong>{selectedOutgoing ? `${selectedOutgoing.amount}（${selectedOutgoing.count}股）` : '无'}</strong></div>
              </div>
            </>
          ) : (
            <div className="detail-empty">
              <strong>尚未选中领地</strong>
              <p>点击地图上的任意六边形，右上角独立栏会持续显示它的归属、人口与前线状态。</p>
            </div>
          )}
        </section>
      </aside>
    </div>
  )
}
