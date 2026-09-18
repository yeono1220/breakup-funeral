/** 매장 씬 배경: 흰 하늘 + 초록 언덕 + 큰 수풀(고정) + 작은 풀 포기(살랑살랑). 800x450 뷰박스. */
export function GrassField() {
  return (
    <svg className="grass-field" viewBox="0 0 800 450" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <defs>
        <style>{`
          @keyframes grassSway1 { 0%,100%{transform:rotate(0)} 30%{transform:rotate(4deg) skewX(2deg)} 70%{transform:rotate(-3deg) skewX(-1deg)} }
          @keyframes grassSway2 { 0%,100%{transform:rotate(0)} 40%{transform:rotate(-5deg) skewX(-2deg)} 80%{transform:rotate(3deg) skewX(1deg)} }
          .g1{transform-box:fill-box;transform-origin:50% 100%;animation:grassSway1 2.5s ease-in-out infinite}
          .g2{transform-box:fill-box;transform-origin:50% 100%;animation:grassSway2 3s ease-in-out infinite .3s}
          .g3{transform-box:fill-box;transform-origin:50% 100%;animation:grassSway1 2.2s ease-in-out infinite .7s}
          .g4{transform-box:fill-box;transform-origin:50% 100%;animation:grassSway2 2.8s ease-in-out infinite .2s}
          .g5{transform-box:fill-box;transform-origin:50% 100%;animation:grassSway1 2.9s ease-in-out infinite 1.1s}
          .g6{transform-box:fill-box;transform-origin:50% 100%;animation:grassSway2 2.4s ease-in-out infinite .5s}
          @keyframes cloudDrift { from{transform:translateX(0)} to{transform:translateX(40px)} }
          .cloud{animation:cloudDrift 18s ease-in-out infinite alternate}
        `}</style>
      </defs>

      {/* 하늘 */}
      <rect width="800" height="450" fill="#ffffff" />
      <g className="cloud" fill="#F1F5F3">
        <ellipse cx="150" cy="70" rx="46" ry="16" /><ellipse cx="180" cy="62" rx="30" ry="14" />
        <ellipse cx="620" cy="50" rx="52" ry="17" /><ellipse cx="655" cy="44" rx="28" ry="12" />
      </g>

      {/* 먼 언덕 */}
      <path d="M0 250 Q140 170 300 230 Q420 275 560 210 Q690 155 800 220 L800 450 L0 450 Z" fill="#8FCB56" />
      {/* 중간 언덕 */}
      <path d="M0 300 Q120 240 260 285 Q400 330 540 275 Q680 225 800 290 L800 450 L0 450 Z" fill="#6FBA36" />
      {/* 앞 언덕 (매장 구덩이가 놓이는 면) */}
      <path d="M0 345 Q200 300 400 335 Q600 370 800 330 L800 450 L0 450 Z" fill="#58a618" />

      {/* 큰 수풀 (고정) */}
      <g fill="#4C9414">
        <path d="M40 300 Q60 240 95 262 Q110 230 140 262 Q170 250 175 300 Z" />
        <path d="M640 280 Q660 225 700 248 Q720 215 745 250 Q775 240 780 285 Z" />
        <path d="M300 335 Q318 300 340 316 Q350 296 372 318 Q392 312 396 338 Z" />
      </g>
      <g fill="#3E7D0F" opacity=".55">
        <ellipse cx="108" cy="300" rx="70" ry="6" /><ellipse cx="710" cy="284" rx="70" ry="6" /><ellipse cx="348" cy="337" rx="48" ry="5" />
      </g>

      {/* 작은 풀 포기 (살랑살랑) */}
      <g fill="#58a618">
        <g className="g1"><path d="M55 250 Q58 235 62 230 Q65 240 68 250 Z" /></g>
        <g className="g2"><path d="M120 400 Q135 340 150 320 Q155 360 170 400 Z" fill="#4C9414" /></g>
        <g className="g3"><path d="M465 300 Q470 280 475 275 Q480 290 485 300 Z" /></g>
        <g className="g4"><path d="M595 235 Q600 215 605 210 Q610 225 615 235 Z" /></g>
        <g className="g5"><path d="M690 380 Q700 345 712 335 Q716 360 726 380 Z" fill="#4C9414" /></g>
        <g className="g6"><path d="M230 372 Q236 350 242 345 Q247 358 252 372 Z" /></g>
        <g className="g1"><path d="M760 330 Q764 315 768 311 Q771 320 774 330 Z" /></g>
        <g className="g3"><path d="M20 400 Q28 372 36 366 Q40 385 48 400 Z" fill="#4C9414" /></g>
      </g>

      {/* 작은 꽃 */}
      <g>
        <circle cx="200" cy="360" r="3" fill="#FFD166" /><circle cx="560" cy="345" r="3" fill="#FF8FA3" /><circle cx="430" cy="392" r="2.5" fill="#FFD166" /><circle cx="88" cy="355" r="2.5" fill="#FF8FA3" />
      </g>
    </svg>
  )
}
