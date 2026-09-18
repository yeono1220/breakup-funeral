/** 공동묘지 메인 씬: 잔디 언덕 3겹 위에 묘비를 세 줄로 세운다. 묘비를 누르면 비문·헌화·방명록 카드가 뜬다.
 *  자리 배정: 내 묘비 → 헌화 많은 순으로 앞줄부터. 씬에 못 들어간 나머지는 아래 목록에서. */
import { useMemo } from 'react'
import type { Tomb } from '../api'
import { GrassField } from './GrassField'
import { Icon } from './Icons'

const ROWS = [
  { y: 236, scale: 0.62, xs: [70, 160, 250, 345, 440, 535, 630, 725] },   // 먼 언덕
  { y: 296, scale: 0.8, xs: [110, 215, 320, 425, 530, 635, 730] },         // 중간 언덕
  { y: 356, scale: 1.0, xs: [95, 225, 355, 485, 615, 735] },               // 앞 언덕
]
export const SCENE_CAP = ROWS.reduce((n, r) => n + r.xs.length, 0)

const jit = (id: number, k: number) => (((id * 9301 + k * 49297) % 233280) / 233280 - 0.5)

export function placeTombs(tombs: Tomb[]) {
  const order = [...tombs].sort((a, b) => Number(b.mine) - Number(a.mine) || b.flowers - a.flowers)
  const slots: { x: number; y: number; s: number }[] = []
  for (const r of [...ROWS].reverse()) for (const x of r.xs) slots.push({ x, y: r.y, s: r.scale })   // 앞줄부터
  if (order[0]?.mine) {   // 내 묘비는 앞줄 가운데
    const mid = Math.floor(ROWS[2].xs.length / 2)
    ;[slots[0], slots[mid]] = [slots[mid], slots[0]]
  }
  return order.slice(0, slots.length).map((t, i) => ({ t, x: slots[i].x + jit(t.id, 1) * 26, y: slots[i].y + jit(t.id, 2) * 8, s: slots[i].s }))
}

export function CemeteryScene({ tombs, selected, onSelect, onFlower, onGuest }: {
  tombs: Tomb[]; selected: Tomb | null; onSelect: (t: Tomb | null) => void; onFlower: (t: Tomb) => void; onGuest: (t: Tomb) => void
}) {
  const placed = useMemo(() => placeTombs(tombs), [tombs])
  // 뒤에 있는(작은) 묘비가 앞 묘비에 가리도록 y 오름차순으로 그린다
  const drawn = [...placed].sort((a, b) => a.y - b.y)
  const sel = selected && placed.find(p => p.t.id === selected.id)
  return (
    <div className="cem-scene">
      <GrassField />
      <svg className="cem-svg" viewBox="0 0 800 450" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg" onClick={() => onSelect(null)}>
        {drawn.map(({ t, x, y, s }) => {
          const on = selected?.id === t.id
          return (
            <g key={t.id} className={'ts' + (on ? ' on' : '') + (t.mine ? ' mine' : '')} transform={`translate(${x} ${y}) scale(${s * (on ? 1.08 : 1)})`}
               onClick={e => { e.stopPropagation(); onSelect(on ? null : t) }} role="button" tabIndex={0} aria-label={t.epitaph}
               onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(on ? null : t) } }}>
              <title>{t.epitaph}</title>
              <ellipse cx="0" cy="2" rx="26" ry="6" fill="#1f3a0c" opacity=".18" />
              {/* 비석: 둥근 머리 + 받침. 손그림 결이라 살짝 비뚤게 */}
              <path d="M-24 4 H24 V-2 H-24 Z" fill="#B9B2A5" stroke="#6E675C" strokeWidth="2" strokeLinejoin="round" />
              <path d="M-19 -2 V-38 Q-19 -56 0 -56 Q19 -56 19 -38 V-2 Z" fill={t.mine ? '#F3E9C8' : t.kind === 'curse' ? '#D9CFC4' : '#E4DED3'} stroke={on ? 'var(--rose-deep)' : '#6E675C'} strokeWidth={on ? 3 : 2} strokeLinejoin="round" transform={`rotate(${jit(t.id, 3) * 5})`} />
              <path d="M-13 -44 Q0 -49 13 -44" fill="none" stroke="#6E675C" strokeWidth="1.2" opacity=".5" />
              <text y="-22" textAnchor="middle" fontSize="11" fill="#5C554B" fontFamily="'Gowun Dodum',sans-serif">#{t.id}</text>
              {t.mine && <text y="-8" textAnchor="middle" fontSize="9" fill="var(--rose-deep)" fontFamily="'Gowun Dodum',sans-serif">내 관계</text>}
              {t.kind === 'curse' && (   // 저주봉인: 부적 한 장 붙어 있음
                <g transform="translate(9 -40) rotate(8)">
                  <rect x="-6" y="0" width="12" height="26" fill="#F6DE8C" stroke="#B23A2E" strokeWidth="1.2" />
                  <text x="0" y="17" textAnchor="middle" fontSize="9" fill="#B23A2E" fontFamily="'Nanum Pen Script',cursive">符</text>
                </g>
              )}
              {t.flowers > 0 && <text x="-16" y="4" fontSize={t.flowers > 500 ? 18 : 13} textAnchor="middle">💐</text>}
              {t.flowers > 50 && <text x="14" y="5" fontSize="12" textAnchor="middle">💐</text>}
            </g>
          )
        })}
      </svg>
      {tombs.length === 0 && <div className="cem-empty">아직 아무도 잠들지 않았어. 첫 묘비를 세워줘</div>}
      {sel && (
        <div className="cem-card fade-in" style={{ left: `${Math.min(78, Math.max(22, sel.x / 8))}%` }}>
          <div className="cc-meta">묘비 #{sel.t.id}{sel.t.mine ? ' · 내 관계' : ''}{sel.t.days ? ` · 향년 ${sel.t.days}일` : ''} · {sel.t.kind === 'curse' ? '저주봉인' : '헌화'}{sel.t.hanja && <span className="legend-amulet">符 {sel.t.hanja}</span>}</div>
          <div className="tomb-epitaph" style={{ minHeight: 0, marginBottom: 8 }}>{sel.t.epitaph}</div>
          <div className="tomb-meta">
            <span className={sel.t.flowered ? 'hit' : ''} onClick={() => onFlower(sel.t)}>💐 <b className="num">{sel.t.flowers.toLocaleString()}</b> 헌화</span>
            <span onClick={() => onGuest(sel.t)}><Icon name="comment" size={14} /><span className="num" style={{ fontWeight: 400 }}>{sel.t.comments}</span> 방명록</span>
            <span style={{ marginLeft: 'auto', color: 'var(--text-faint)' }} onClick={() => onSelect(null)}>닫기</span>
          </div>
        </div>
      )}
      {!sel && tombs.length > 0 && <div className="cem-hint">묘비를 누르면 사연이 보여</div>}
    </div>
  )
}
