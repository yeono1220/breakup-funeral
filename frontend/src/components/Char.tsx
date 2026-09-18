/** 앱 공용 마스코트: 테루테루보즈 (사용자 제공 SVG 기반). 한 원본에서 표정/자세만 파생.
 *  mood: smile(기본) | sad(눈물·울상) | peace(눈 감고 평온, 매장용) | memorial(영정: 흑백, 눈 감음) | dark(X눈)
 *  lying: 옆으로 누운 자세 (구덩이 안). drops: 주위 빗방울 표시 여부.
 *  손맛: 머리는 살짝 찌그러진 타원에 2.5° 기울임, 좌우 비대칭(볼·리본·치맛단), 선 굵기 변주, 두 겹 펜 자국.
 */
type Mood = 'smile' | 'sad' | 'peace' | 'memorial' | 'dark'

export function Mascot({ mood = 'smile', size = 150, lying = false, drops, className }: { mood?: Mood; size?: number; lying?: boolean; drops?: boolean; className?: string }) {
  const gray = mood === 'memorial'
  const showDrops = drops ?? (!lying && !gray)
  const body = gray ? '#DDE1E6' : '#f0f4f8'
  const shade = gray ? '#C5CBD3' : '#e2e8f0'
  const outline = gray ? '#B9BEC6' : '#D3DBE3'
  const ink = '#334155'
  const ribbon = gray ? '#8B8F96' : '#f87171'
  const ribbonDeep = gray ? '#767A82' : '#e05a5a'
  const blush = gray ? '#B9BEC6' : '#f87171'
  const w = lying ? size * 1.25 : size * 0.8
  const h = size
  const gid = `dropGrad-${mood}${lying ? '-l' : ''}`
  const headTilt = 'rotate(2.5 200 130)'
  return (
    <svg width={w} height={h} viewBox={lying ? '0 0 500 400' : '0 0 400 500'} className={className} aria-hidden>
      <defs>
        <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#bde3ff" /><stop offset="100%" stopColor="#70bbfd" />
        </linearGradient>
        <clipPath id={`${gid}-head`}><ellipse cx="200" cy="130" rx="86" ry="83" /></clipPath>
      </defs>
      {lying && <ellipse cx="253" cy="372" rx="200" ry="14" fill="#000" opacity=".12" />}
      <g transform={lying ? 'translate(500 0) rotate(90)' : undefined}>
        {/* 매달린 실: 살짝 휜 곡선 */}
        {!lying && !gray && <path d="M 200 0 Q 193 26, 201 50" fill="none" stroke="#4a5568" strokeWidth="3" strokeDasharray="4 2" strokeLinecap="round" />}

        {/* 주위 빗방울: 크기·기울기 제각각. 위치 g 와 애니메이션 g 를 분리(.drop 의 transform 애니가 위치를 덮지 않도록) */}
        {showDrops && (
          <>
            <g transform="translate(30 200) rotate(-8)">
              <g className="drop" style={{ animationDuration: '3.2s' }}>
                <path d="M 30 0 C 30 0 0 50 0 75 A 30 30 0 0 0 60 75 C 60 50 30 0 30 0 Z" fill={`url(#${gid})`} />
                <path d="M 20 50 A 15 15 0 0 1 35 35" fill="none" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
              </g>
            </g>
            <g transform="translate(322 28) rotate(6)">
              <g className="drop" style={{ animationDuration: '2.6s', animationDelay: '.8s' }}>
                <path d="M 23 0 C 23 0 0 38 0 56 A 23 23 0 0 0 46 56 C 46 38 23 0 23 0 Z" fill={`url(#${gid})`} />
                <path d="M 16 38 A 11 11 0 0 1 28 26" fill="none" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" opacity="0.7" />
              </g>
            </g>
            <g transform="translate(288 172)">
              <g className="drop" style={{ animationDuration: '3.6s', animationDelay: '1.5s' }}>
                <path d="M 36 0 C 36 0 0 62 0 88 A 36 36 0 0 0 72 88 C 72 62 36 0 36 0 Z" fill={`url(#${gid})`} />
                <path d="M 24 60 A 18 18 0 0 1 41 41" fill="none" stroke="#ffffff" strokeWidth="4.5" strokeLinecap="round" opacity="0.7" />
              </g>
            </g>
          </>
        )}

        {/* 몸통 (치마): 밑단 물결 좌우 비대칭, 윤곽 3 + 두 겹 펜 자국 */}
        <path d="M 140 220 C 118 282, 78 408, 82 432 Q 106 418, 134 442 Q 168 458, 196 436 Q 232 418, 264 448 Q 292 452, 318 428 C 322 408, 282 280, 260 220 Z" fill={body} stroke={outline} strokeWidth="3" strokeLinejoin="round" />
        <path d="M 84 430 Q 108 420, 136 440 Q 169 456, 197 435" fill="none" stroke={outline} strokeWidth="5.5" strokeLinecap="round" opacity=".28" />
        {/* 주름 두 줄: 굵기 3 / 4.5 */}
        <path d="M 178 242 Q 168 340, 152 436" fill="none" stroke={shade} strokeWidth="3" strokeLinecap="round" opacity="0.6" />
        <path d="M 222 240 Q 234 345, 254 438" fill="none" stroke={shade} strokeWidth="4.5" strokeLinecap="round" opacity="0.6" />

        {/* 머리: 찌그러진 타원(86×83) 을 2.5° 기울임 */}
        <g transform={headTilt}>
          <ellipse cx="201" cy="131" rx="86" ry="83" fill="none" stroke={outline} strokeWidth="6.5" opacity=".3" />
          <ellipse cx="200" cy="130" rx="86" ry="83" fill={body} stroke={outline} strokeWidth="3.5" />
          <circle cx="170" cy="100" r="70" fill="#ffffff" opacity={gray ? 0.3 : 0.5} clipPath={`url(#${gid}-head)`} />
        </g>

        {/* 볼터치: 왼볼이 1.15배 크다 */}
        <ellipse cx="134" cy="146" rx="18.4" ry="13.8" fill={blush} opacity={gray ? 0.5 : 0.8} />
        <ellipse cx="265" cy="144" rx="16" ry="12" fill={blush} opacity={gray ? 0.5 : 0.8} />

        {/* 표정: 눈 y 2px 어긋남, 하이라이트 점 */}
        {(mood === 'smile' || mood === 'sad') && (
          <>
            <circle cx="160" cy="119" r="9" fill={ink} /><circle cx="240" cy="121" r="8.5" fill={ink} />
            <circle cx="157" cy="116" r="2.8" fill="#ffffff" opacity=".9" /><circle cx="237.5" cy="118" r="2.4" fill="#ffffff" opacity=".9" />
          </>
        )}
        {mood === 'smile' && (
          <path d="M 181 150 Q 201 171, 219 149" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
        )}
        {mood === 'sad' && (
          <>
            <path d="M 148 103 Q 160 97, 172 104 M 229 105 Q 240 98, 252 103" fill="none" stroke={ink} strokeWidth="2.5" strokeLinecap="round" opacity=".6" />
            <path d="M 181 161 Q 200 145, 219 159" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
            {/* 눈물: 왼쪽 한 방울만, 살짝 비스듬히 */}
            <g transform="rotate(-10 150 134)">
              <path className="drop" d="M 150 132 q -6 12 0 19 q 7 -5 0 -19" fill="#70bbfd" />
            </g>
          </>
        )}
        {mood === 'peace' && (
          <>
            <path d="M 148 121 Q 160 132, 172 121" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
            <path d="M 228 123 Q 240 133, 252 123" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
            <path d="M 186 152 Q 200 163, 214 151" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
          </>
        )}
        {mood === 'memorial' && (
          <>
            <path d="M 148 120 Q 160 122, 172 119" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
            <path d="M 228 121 Q 240 123, 252 120" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
            <path d="M 186 156 Q 200 157, 214 155" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" />
          </>
        )}
        {mood === 'dark' && (
          <>
            <path d="M 149 109 L 171 131 M 170 109 L 150 130" fill="none" stroke={ink} strokeWidth="5" strokeLinecap="round" />
            <path d="M 231 112 L 251 132 M 250 111 L 231 131" fill="none" stroke={ink} strokeWidth="4.5" strokeLinecap="round" />
            <path d="M 182 162 Q 200 148, 218 161" fill="none" stroke={ink} strokeWidth="4" strokeLinecap="round" />
          </>
        )}

        {/* 목 리본: 매듭 살짝 왼쪽, 왼쪽 끈이 오른쪽보다 15% 길다 */}
        <path d="M 130 210 Q 195 236, 270 210 Q 196 199, 130 210 Z" fill={ribbon} />
        <path d="M 176 215 C 154 242, 132 286, 144 302 C 160 302, 182 262, 192 220 Z" fill={ribbon} />
        <path d="M 218 215 C 236 238, 254 272, 246 286 C 232 286, 214 256, 204 220 Z" fill={ribbon} />
        <ellipse cx="195" cy="215" rx="10" ry="7" fill={ribbonDeep} transform="rotate(-6 195 215)" />
      </g>
      {!lying && <ellipse cx="203" cy="462" rx="110" ry="10" fill="#000" opacity=".12" />}
    </svg>
  )
}

/* 기존 호출부 호환용 별칭 */
export const Char = ({ mood = 'sad', size = 150 }: { mood?: 'sad' | 'dark' | 'smile'; size?: number }) => <Mascot mood={mood} size={size} />
export const LyingChar = ({ width = 160 }: { width?: number }) => <Mascot mood="peace" lying size={width / 1.25} />
export const MemorialChar = ({ size = 150 }: { size?: number }) => <Mascot mood="memorial" size={size} />
