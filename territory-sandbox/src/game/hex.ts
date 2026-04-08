const SQRT3 = Math.sqrt(3)

export const makeCellId = (q: number, r: number) => `${q},${r}`

export const axialToPixel = (q: number, r: number, size: number) => {
  const x = size * (SQRT3 * q + (SQRT3 / 2) * (r & 1))
  const y = size * (1.5 * r)
  return { x, y }
}

export const hexCorners = (centerX: number, centerY: number, size: number) => {
  const points: Array<[number, number]> = []
  for (let i = 0; i < 6; i += 1) {
    const angle = (Math.PI / 180) * (60 * i - 30)
    points.push([
      centerX + size * Math.cos(angle),
      centerY + size * Math.sin(angle),
    ])
  }
  return points
}

export const oddRNeighbors = (q: number, r: number) => {
  const isOdd = (r & 1) === 1
  const dirs = isOdd
    ? [
        [1, 0],
        [1, -1],
        [0, -1],
        [-1, 0],
        [0, 1],
        [1, 1],
      ]
    : [
        [1, 0],
        [0, -1],
        [-1, -1],
        [-1, 0],
        [-1, 1],
        [0, 1],
      ]

  return dirs.map(([dq, dr]) => ({ q: q + dq, r: r + dr }))
}

export const pointInHex = (
  px: number,
  py: number,
  centerX: number,
  centerY: number,
  size: number,
) => {
  const dx = Math.abs(px - centerX) / size
  const dy = Math.abs(py - centerY) / size
  return dy <= 0.866 && 0.57735 * dx + dy <= 1.1547
}
