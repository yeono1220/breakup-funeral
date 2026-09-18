/** X의 얼굴: 사용자가 그린/올린 초상화. 없으면 '빈 종이 위에 손글씨 ? 와 연필 선 두 줄' 실루엣. */
export function Portrait({ src, size = 150, gray = true, rounded = false }: { src?: string | null; size?: number; gray?: boolean; rounded?: boolean }) {
  if (src) {
    return <img src={src} width={size} height={size} alt="" draggable={false}
      style={{ display: 'block', objectFit: 'cover', borderRadius: rounded ? '50%' : 6, filter: gray ? 'grayscale(1) contrast(1.05)' : undefined, background: '#fff' }} />
  }
  const bg = gray ? '#B8C0C8' : '#E8EDF2'
  const paper = gray ? '#DDE2E8' : '#FFFDF8'
  const paperLine = gray ? '#9AA3AD' : '#D6CCBE'
  const ink = gray ? '#5F6873' : '#3E4650'
  const pencil = gray ? '#8E98A3' : '#A39A90'
  return (
    <svg width={size} height={size} viewBox="0 0 150 150" aria-hidden style={{ display: 'block' }}>
      <rect width="150" height="150" rx={rounded ? 75 : 6} fill={bg} />
      {/* 빈 종이: 살짝 기울고 모서리가 제각각 */}
      <path d="M 34 27 L 116 24 Q 120 24 120 28 L 119 123 Q 119 127 115 127 L 35 126 Q 31 126 31 122 Z"
        fill={paper} stroke={paperLine} strokeWidth="1.5" strokeLinejoin="round" transform="rotate(-2.5 75 75)" />
      {/* 손글씨 ? : 굵은 반투명 + 얇은 진한 두 겹 */}
      <path d="M 60 60 C 58 44, 90 41, 89 58 C 88 69, 75 68, 76 84" fill="none" stroke={ink} strokeWidth="6" strokeLinecap="round" opacity=".25" transform="rotate(-2.5 75 75)" />
      <path d="M 60 60 C 58 44, 90 41, 89 58 C 88 69, 75 68, 76 84 M 76 96 q 1 1 0 2" fill="none" stroke={ink} strokeWidth="3.5" strokeLinecap="round" transform="rotate(-2.5 75 75)" />
      {/* 연필 선 두 줄: 길이·굵기 다르게 */}
      <path d="M 46 108 Q 74 104, 104 108 M 50 116 Q 70 118.5, 91 115" fill="none" stroke={pencil} strokeWidth="1.8" strokeLinecap="round" opacity=".85" transform="rotate(-2.5 75 75)" />
    </svg>
  )
}
