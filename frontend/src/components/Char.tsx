/** 테루테루보즈 캐릭터 3종: 서 있는 것(sad/dark), 누운 것(매장용), 영정(흑백). */

export function Char({ mood = 'sad', size = 150 }: { mood?: 'sad' | 'dark'; size?: number }) {
  const body = mood === 'dark' ? '#B8BEC6' : '#FDFEFF'
  const line = mood === 'dark' ? '#7A828C' : '#C9D2DA'
  const ribbon = '#E8503A'
  return (
    <svg width={size} height={size} viewBox="0 0 150 172">
      <ellipse cx="75" cy="168" rx="36" ry="5" fill="#000" opacity=".14" />
      {mood === 'dark' ? (
        <>
          <path className="drop" style={{ animationDelay: '0s' }} d="M30 40 q-4 6 0 9 q4 -3 0 -9" fill="#8FB8D8" />
          <path className="drop" style={{ animationDelay: '1.2s' }} d="M118 40 q-4 6 0 9 q4 -3 0 -9" fill="#8FB8D8" />
        </>
      ) : (
        <>
          <path className="drop" style={{ animationDelay: '0s' }} d="M30 42 q-4 6 0 9 q4 -3 0 -9" fill="#9FC4E0" />
          <path className="drop" style={{ animationDelay: '.9s' }} d="M118 40 q-4 6 0 9 q4 -3 0 -9" fill="#9FC4E0" />
          <path className="drop" style={{ animationDelay: '1.6s' }} d="M122 70 q-3 5 0 8 q3 -3 0 -8" fill="#9FC4E0" />
        </>
      )}
      <path d="M75 18 C102 18 120 40 120 68 C120 84 116 96 116 108 L120 150 L108 140 L98 152 L86 140 L75 154 L64 140 L52 152 L42 140 L30 150 L34 108 C34 96 30 84 30 68 C30 40 48 18 75 18 Z"
        fill={body} stroke={line} strokeWidth="3" strokeLinejoin="round" />
      <circle cx="75" cy="88" r="5" fill={ribbon} />
      <path d="M75 88 Q60 80 58 92 Q60 100 75 88 Z" fill={ribbon} />
      <path d="M75 88 Q90 80 92 92 Q90 100 75 88 Z" fill={ribbon} />
      <path d="M73 92 Q68 108 64 120" stroke={ribbon} strokeWidth="3.2" fill="none" strokeLinecap="round" />
      <path d="M77 92 Q82 108 86 118" stroke={ribbon} strokeWidth="3.2" fill="none" strokeLinecap="round" />
      {mood === 'dark' ? (
        <>
          <path d="M60 60 L69 66 M69 60 L60 66" stroke="#3A424D" strokeWidth="3" strokeLinecap="round" />
          <path d="M81 60 L90 66 M90 60 L81 66" stroke="#3A424D" strokeWidth="3" strokeLinecap="round" />
          <path d="M68 76 Q75 72 82 76" stroke="#3A424D" strokeWidth="2.6" fill="none" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="63" cy="62" r="5.5" fill="#2E353D" /><circle cx="87" cy="62" r="5.5" fill="#2E353D" />
          <circle cx="61" cy="60" r="1.6" fill="#fff" /><circle cx="85" cy="60" r="1.6" fill="#fff" />
          <circle cx="54" cy="72" r="7" fill="#F4A9A0" opacity=".7" /><circle cx="96" cy="72" r="7" fill="#F4A9A0" opacity=".7" />
        </>
      )}
    </svg>
  )
}

export function LyingChar({ width = 160 }: { width?: number }) {
  return (
    <svg width={width} viewBox="0 0 210 96" style={{ display: 'block' }}>
      <ellipse cx="105" cy="84" rx="78" ry="8" fill="#000" opacity=".12" />
      <path d="M40 50 C40 26 66 16 100 16 C150 16 184 26 184 48 C184 60 180 68 180 74 L186 88 L176 82 L168 90 L158 82 L150 90 L142 82 L134 88 L128 80 C120 80 110 78 100 78 L70 78 C52 78 40 66 40 50 Z"
        fill="#FDFEFF" stroke="#C9D2DA" strokeWidth="3" strokeLinejoin="round" />
      <circle cx="70" cy="46" r="4.5" fill="#2E353D" /><circle cx="94" cy="46" r="4.5" fill="#2E353D" />
      <circle cx="60" cy="56" r="6" fill="#F4A9A0" opacity=".6" /><circle cx="104" cy="56" r="6" fill="#F4A9A0" opacity=".6" />
      <circle cx="118" cy="52" r="4" fill="#E8503A" />
      <path d="M118 52 Q126 62 132 70" stroke="#E8503A" strokeWidth="2.6" fill="none" strokeLinecap="round" />
      <path d="M118 52 Q124 60 128 72" stroke="#E8503A" strokeWidth="2.6" fill="none" strokeLinecap="round" />
    </svg>
  )
}

export function MemorialChar({ size = 150 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 150 150" style={{ filter: 'grayscale(1) brightness(.95)' }}>
      <ellipse cx="75" cy="140" rx="28" ry="4" fill="#000" opacity=".25" />
      <path d="M75 96 L60 114 M75 96 L90 114" stroke="#6B7480" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M60 88 Q75 96 90 88 L88 98 Q75 104 62 98 Z" fill="#9AA5B0" stroke="#6B7480" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="75" cy="52" r="34" fill="#B8C0C8" stroke="#6B7480" strokeWidth="3" />
      <path d="M60 50 L70 50 M80 50 L90 50" stroke="#3E4650" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M66 64 L84 64" stroke="#3E4650" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}
