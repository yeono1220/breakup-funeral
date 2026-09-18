/** 앱 공용 마스코트: 테루테루보즈 (사용자 제공 SVG 기반). 한 원본에서 표정/자세만 파생.
 *  mood: smile(기본) | sad(눈물·울상) | peace(눈 감고 평온, 매장용) | memorial(영정: 흑백, 눈 감음) | dark(X눈)
 *  lying: 옆으로 누운 자세 (구덩이 안). drops: 주위 빗방울 표시 여부.
 */
type Mood = 'smile' | 'sad' | 'peace' | 'memorial' | 'dark'

export function Mascot({ mood = 'smile', size = 150, lying = false, drops, className }: { mood?: Mood; size?: number; lying?: boolean; drops?: boolean; className?: string }) {
  const gray = mood === 'memorial'
  const showDrops = drops ?? (!lying && !gray)
  const body = gray ? '#DDE1E6' : '#f0f4f8'
  const shade = gray ? '#C5CBD3' : '#e2e8f0'
  const ink = '#334155'
  const ribbon = gray ? '#8B8F96' : '#f87171'
  const blush = gray ? '#B9BEC6' : '#f87171'
  const w = lying ? size * 1.25 : size * 0.8
  const h = size
  const gid = `dropGrad-${mood}${lying ? '-l' : ''}`
  return (
    <svg width={w} height={h} viewBox={lying ? '0 0 500 400' : '0 0 400 500'} className={className} aria-hidden>
      <defs>
        <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#bde3ff" /><stop offset="100%" stopColor="#70bbfd" />
        </linearGradient>
        <clipPath id={`${gid}-head`}><circle cx="200" cy="130" r="85" /></clipPath>
      </defs>
      {lying && <ellipse cx="250" cy="372" rx="200" ry="14" fill="#000" opacity=".12" />}
      <g transform={lying ? 'translate(500 0) rotate(90)' : undefined}>
        {/* 매달린 실 */}
        {!lying && !gray && <line x1="200" y1="0" x2="200" y2="50" stroke="#4a5568" strokeWidth="3" strokeDasharray="4 2" />}

        {/* 주위 빗방울 */}
        {showDrops && (
          <>
            <g transform="translate(30, 200)" className="drop" style={{ animationDuration: '3.2s' }}>
              <path d="M 30 0 C 30 0 0 50 0 75 A 30 30 0 0 0 60 75 C 60 50 30 0 30 0 Z" fill={`url(#${gid})`} />
              <path d="M 20 50 A 15 15 0 0 1 35 35" fill="none" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
            </g>
            <g transform="translate(320, 30)" className="drop" style={{ animationDuration: '2.6s', animationDelay: '.8s' }}>
              <path d="M 25 0 C 25 0 0 40 0 60 A 25 25 0 0 0 50 60 C 50 40 25 0 25 0 Z" fill={`url(#${gid})`} />
              <path d="M 17 40 A 12 12 0 0 1 30 28" fill="none" stroke="#ffffff" strokeWidth="3.5" strokeLinecap="round" opacity="0.7" />
            </g>
            <g transform="translate(290, 170)" className="drop" style={{ animationDuration: '3.6s', animationDelay: '1.5s' }}>
              <path d="M 35 0 C 35 0 0 60 0 85 A 35 35 0 0 0 70 85 C 70 60 35 0 35 0 Z" fill={`url(#${gid})`} />
              <path d="M 23 58 A 18 18 0 0 1 40 40" fill="none" stroke="#ffffff" strokeWidth="4.5" strokeLinecap="round" opacity="0.7" />
            </g>
          </>
        )}

        {/* 몸통 (치마) */}
        <path d="M 140 220 C 120 280, 80 410, 80 430 Q 110 420, 140 440 Q 170 455, 200 435 Q 230 420, 260 445 Q 290 455, 320 430 C 320 410, 280 280, 260 220 Z" fill={body} stroke={gray ? '#B9BEC6' : '#D3DBE3'} strokeWidth="3" strokeLinejoin="round" />
        <path d="M 180 240 Q 170 340, 150 435" fill="none" stroke={shade} strokeWidth="4" opacity="0.6" />
        <path d="M 220 240 Q 230 340, 250 435" fill="none" stroke={shade} strokeWidth="4" opacity="0.6" />

        {/* 머리 */}
        <circle cx="200" cy="130" r="85" fill={body} stroke={gray ? '#B9BEC6' : '#D3DBE3'} strokeWidth="3" />
        <circle cx="170" cy="100" r="70" fill="#ffffff" opacity={gray ? 0.3 : 0.5} clipPath={`url(#${gid}-head)`} />

        {/* 볼터치 */}
        <ellipse cx="135" cy="145" rx="16" ry="12" fill={blush} opacity={gray ? 0.5 : 0.8} />
        <ellipse cx="265" cy="145" rx="16" ry="12" fill={blush} opacity={gray ? 0.5 : 0.8} />

        {/* 표정 */}
        {mood === 'smile' && (
          <>
            <circle cx="160" cy="120" r="9" fill={ink} /><circle cx="240" cy="120" r="9" fill={ink} />
            <path d="M 180 150 Q 200 170, 220 150" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
          </>
        )}
        {mood === 'sad' && (
          <>
            <circle cx="160" cy="120" r="9" fill={ink} /><circle cx="240" cy="120" r="9" fill={ink} />
            <path d="M 148 104 Q 160 98, 172 104 M 228 104 Q 240 98, 252 104" fill="none" stroke={ink} strokeWidth="3" strokeLinecap="round" opacity=".6" />
            <path d="M 180 160 Q 200 145, 220 160" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
            <path className="drop" d="M 250 132 q -6 12 0 18 q 6 -5 0 -18" fill="#70bbfd" />
          </>
        )}
        {mood === 'peace' && (
          <>
            <path d="M 148 122 Q 160 132, 172 122 M 228 122 Q 240 132, 252 122" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
            <path d="M 186 152 Q 200 162, 214 152" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
          </>
        )}
        {mood === 'memorial' && (
          <>
            <path d="M 148 120 L 172 120 M 228 120 L 252 120" stroke={ink} strokeWidth="4" strokeLinecap="round" />
            <path d="M 186 156 L 214 156" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
          </>
        )}
        {mood === 'dark' && (
          <>
            <path d="M 150 110 L 170 130 M 170 110 L 150 130 M 230 110 L 250 130 M 250 110 L 230 130" stroke={ink} strokeWidth="5" strokeLinecap="round" />
            <path d="M 182 162 Q 200 148, 218 162" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
          </>
        )}

        {/* 목 리본 */}
        <path d="M 130 210 Q 200 235, 270 210 Q 200 200, 130 210 Z" fill={ribbon} />
        <path d="M 180 215 C 160 240, 140 280, 150 295 C 165 295, 185 260, 195 220 Z" fill={ribbon} />
        <path d="M 220 215 C 240 240, 260 280, 250 295 C 235 295, 215 260, 205 220 Z" fill={ribbon} />
      </g>
      {!lying && <ellipse cx="200" cy="462" rx="110" ry="10" fill="#000" opacity=".12" />}
    </svg>
  )
}

/* 기존 호출부 호환용 별칭 */
export const Char = ({ mood = 'sad', size = 150 }: { mood?: 'sad' | 'dark' | 'smile'; size?: number }) => <Mascot mood={mood} size={size} />
export const LyingChar = ({ width = 160 }: { width?: number }) => <Mascot mood="peace" lying size={width / 1.25} />
export const MemorialChar = ({ size = 150 }: { size?: number }) => <Mascot mood="memorial" size={size} />
