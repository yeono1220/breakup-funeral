/** 장례 의식 진행표. 조문(진단서) → 입관(매장) → 부적·헌화 → 발인(공동묘지). 지난 단계는 눌러서 되돌아갈 수 있다. */
export const RITUAL_STEPS = [
  { key: 'diagnosis', label: '조문', sub: '진단서' },
  { key: 'burial', label: '입관', sub: '매장' },
  { key: 'tribute', label: '부적·헌화', sub: '인사' },
  { key: 'cemetery', label: '발인', sub: '공동묘지' },
] as const

export function RitualBar({ current, onGo }: { current: number; onGo?: (i: number) => void }) {
  return (
    <div className="ritual-bar reveal" style={{ ['--i' as any]: 0 }} role="list" aria-label="장례 순서">
      {RITUAL_STEPS.map((s, i) => {
        const state = i < current ? 'done' : i === current ? 'on' : ''
        const clickable = !!onGo && i < current
        return (
          <div key={s.key} style={{ display: 'contents' }}>
            <span role="listitem" className={'ritual-step ' + state + (clickable ? ' link' : '')} onClick={clickable ? () => onGo!(i) : undefined} title={s.sub}>
              <span className="rs-n">{i < current ? '✓' : i + 1}</span>{s.label}
            </span>
            {i < RITUAL_STEPS.length - 1 && <span className={'ritual-line' + (i < current ? ' done' : '')} aria-hidden />}
          </div>
        )
      })}
    </div>
  )
}
