/**
 * 손으로 그린 듯한 1.5px 스트로크 아이콘.
 * - viewBox 0 0 24 24, currentColor, fill none, round cap/join
 * - 완벽 대칭 금지: 원은 rx≠ry 타원, 선 끝점은 1~2px 어긋남, 직선은 살짝 휨
 * - 두 겹 선(굵고 옅은 밑선 + 얇고 진한 윗선)으로 펜 자국 느낌
 */
export type IconName =
  | 'receipt' | 'trend-down' | 'search' | 'flask' | 'tomb' | 'bandage' | 'flower'
  | 'scroll' | 'ghost' | 'comment' | 'upload' | 'clock' | 'pin' | 'x'

type Stroke = { d: string; w?: number }
type Ellipse = { cx: number; cy: number; rx: number; ry: number; w?: number }
type Glyph = { paths: Stroke[]; ellipses?: Ellipse[] }

const GLYPHS: Record<IconName, Glyph> = {
  receipt: {
    paths: [
      // 종이 몸통: 아래쪽 톱니가 살짝 불규칙
      { d: 'M6.3 3.6h11.5v16.9l-2.2-1.5-1.8 1.8-2-1.5-2.1 1.6-1.7-1.8-1.8 1.4z' },
      { d: 'M9.1 8.3h6.2', w: 1.3 },
      { d: 'M9.2 11.6h5', w: 1.3 },
      { d: 'M9 14.9h3.7', w: 1.3 },
    ],
  },
  'trend-down': {
    paths: [
      // 살짝 휜 하강선
      { d: 'M3.7 7.3c1.8 1.6 3.4 3.5 5 5.2l3.5-3.1c2.6 2.4 5.3 4.9 8.1 7.3' },
      { d: 'M20.5 12.5l-.3 4.3-4.1-.2', w: 1.4 },
    ],
  },
  search: {
    ellipses: [{ cx: 10.6, cy: 10.3, rx: 6.2, ry: 5.8 }],
    paths: [{ d: 'M15.4 15.2c1.6 1.7 3.2 3.5 4.9 5.1', w: 1.7 }],
  },
  flask: {
    paths: [
      { d: 'M9.5 3.5h5.2', w: 1.4 },
      { d: 'M10.4 3.7v5.7L5.6 18.2c-.6 1.2.2 2.4 1.5 2.4h10c1.3 0 2.1-1.3 1.4-2.5L13.7 9.6V3.6' },
      // 액체 표면: 물결
      { d: 'M8.1 15.5c1.9-.9 3.7.7 5.6-.2 1-.4 1.6-.4 2.3-.2', w: 1.2 },
    ],
  },
  tomb: {
    paths: [
      { d: 'M6.5 20.5V9.9c0-3.6 2.3-6.3 5.6-6.3 3.4 0 5.6 2.8 5.5 6.4v10.5' },
      { d: 'M4.3 20.6c5.3.2 10.4.1 15.6 0', w: 1.6 },
      { d: 'M12 8.5v5.3', w: 1.3 },
      { d: 'M9.9 10.9h4.3', w: 1.3 },
    ],
  },
  bandage: {
    paths: [
      { d: 'M5.7 10.5l4.8-4.9c1.1-1 2.7-1 3.7 0l4.3 4.3c1 1 1 2.6-.1 3.7l-4.9 4.7c-1 1-2.7 1-3.7-.1l-4.1-4.2c-1-1-1-2.5 0-3.5z' },
      { d: 'M8.8 12.6l3.5-3.6M11.6 15.3l3.6-3.6', w: 1.1 },
      { d: 'M11.1 11.3h.1M12.9 12.9h.1M11 12.9h.1M13 11.2h.1', w: 2 },
    ],
  },
  flower: {
    ellipses: [{ cx: 12, cy: 12, rx: 2.1, ry: 1.9 }],
    paths: [
      // 꽃잎 3장: 크기·기울기 다르게
      { d: 'M12 10.1c-2.1-1.5-2.4-4.5-.7-6.3 1.8 1.5 2.2 4.1.7 6.3z' },
      { d: 'M13.9 12c1.5-2.1 4.5-2.3 6.2-.6-1.6 1.8-4.2 2.1-6.2.6z' },
      { d: 'M10.1 11.9c-1.6-2-4.4-2.4-6.2-.8 1.4 1.9 4.1 2.3 6.2.8z' },
      // 줄기·잎
      { d: 'M12.2 14.1c.2 2.6-.1 4.6-.4 6.5', w: 1.3 },
      { d: 'M11.9 18.3c-1.6-.4-3-1.4-3.6-2.9 1.7-.1 3 .9 3.6 2.9z', w: 1.2 },
    ],
  },
  scroll: {
    paths: [
      { d: 'M7.4 5.2h10.3c1.2 0 2.1.9 2.1 2.1v1.2h-3.1' },
      { d: 'M7.3 5.2c-1.2 0-2 .9-2 2.1v10.6c0 1.6 1 2.8 2.4 2.8h9.9c1.2 0 2.2-1 2.2-2.4v-1.4H9.4' },
      { d: 'M9.2 10.1h6.1', w: 1.3 },
      { d: 'M9.3 13.4h4.4', w: 1.3 },
    ],
  },
  ghost: {
    paths: [
      { d: 'M6.2 20.4V11c0-3.5 2.5-6.4 5.9-6.4 3.3 0 5.7 2.9 5.7 6.5v9.2l-2-1.6-1.9 1.7-1.9-1.6-2 1.6-1.9-1.7z' },
      { d: 'M9.8 11.1h.1M14.2 10.9h.1', w: 2.3 },
      { d: 'M10.9 14.6c.7.5 1.5.4 2.3-.1', w: 1.2 },
    ],
  },
  comment: {
    paths: [
      { d: 'M5.2 6.4c0-1.1.9-2 2-2h9.9c1.1 0 2 .9 2 2v7.3c0 1.1-.9 2-2 2h-6.4l-3.6 3.1.2-3.1c-1.1 0-2.1-.9-2.1-2z' },
      { d: 'M8.6 8.6h6.9M8.7 11.4h4.3', w: 1.2 },
    ],
  },
  upload: {
    paths: [
      { d: 'M4.6 15.4v3c0 1 .8 1.8 1.8 1.8h11.3c1 0 1.8-.8 1.8-1.9v-2.8' },
      { d: 'M12.1 15.2c-.1-3.5 0-7.1-.1-10.6', w: 1.6 },
      { d: 'M8.3 8.2l3.8-3.7 3.6 3.9' },
    ],
  },
  clock: {
    ellipses: [{ cx: 12, cy: 12.2, rx: 8.2, ry: 7.9 }],
    paths: [{ d: 'M12.1 7.6v4.8l3.2 2.1', w: 1.6 }],
  },
  pin: {
    ellipses: [{ cx: 12, cy: 10, rx: 2.1, ry: 2, w: 1.3 }],
    paths: [{ d: 'M12 21.2s-6.1-6.3-6.1-11.1c0-3.5 2.7-6.1 6-6.1s6.2 2.6 6.2 6.2c0 4.7-6.1 11-6.1 11z' }],
  },
  x: {
    paths: [
      { d: 'M6.4 6.2c3.8 3.8 7.5 7.7 11.3 11.6', w: 1.6 },
      { d: 'M17.9 6.4C14 10.1 10.1 13.9 6.2 17.7' },
    ],
  },
}

export function Icon({ name, size = 16, className }: { name: IconName; size?: number; className?: string }) {
  const g = GLYPHS[name]
  const render = (scale: number, opacity: number) => (
    <g opacity={opacity}>
      {g.ellipses?.map((e, i) => (
        <ellipse key={'e' + i} cx={e.cx} cy={e.cy} rx={e.rx} ry={e.ry} strokeWidth={(e.w ?? 1.5) * scale} />
      ))}
      {g.paths.map((p, i) => (
        <path key={'p' + i} d={p.d} strokeWidth={(p.w ?? 1.5) * scale} />
      ))}
    </g>
  )
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      style={{ display: 'inline-block', verticalAlign: '-0.15em', flexShrink: 0 }}
    >
      {/* 밑선: 굵고 옅게 — 펜이 두 번 지나간 자국 */}
      {render(1.7, 0.18)}
      {/* 윗선: 얇고 진하게 */}
      {render(1, 1)}
    </svg>
  )
}

export default Icon
