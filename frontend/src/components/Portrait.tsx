/** X의 얼굴: 사용자가 그린/올린 초상화. 없으면 익명 실루엣. */
export function Portrait({ src, size = 150, gray = true, rounded = false }: { src?: string | null; size?: number; gray?: boolean; rounded?: boolean }) {
  if (src) {
    return <img src={src} width={size} height={size} alt="" draggable={false}
      style={{ display: 'block', objectFit: 'cover', borderRadius: rounded ? '50%' : 6, filter: gray ? 'grayscale(1) contrast(1.05)' : undefined, background: '#fff' }} />
  }
  return (
    <svg width={size} height={size} viewBox="0 0 150 150" aria-hidden style={{ display: 'block' }}>
      <rect width="150" height="150" rx={rounded ? 75 : 6} fill={gray ? '#B8C0C8' : '#E8EDF2'} />
      <circle cx="75" cy="58" r="28" fill={gray ? '#8E98A3' : '#C3CCD6'} />
      <path d="M25 140 C25 100 55 92 75 92 C95 92 125 100 125 140 Z" fill={gray ? '#8E98A3' : '#C3CCD6'} />
      <text x="75" y="66" textAnchor="middle" fontSize="26" fill={gray ? '#DDE2E8' : '#fff'} fontFamily="sans-serif">?</text>
    </svg>
  )
}
