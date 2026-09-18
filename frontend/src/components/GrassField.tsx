/** 매장 씬 배경: 흰 하늘 + 손으로 그린 듯한 초록 언덕 3겹 + 큰 수풀(고정) + 작은 풀 포기(살랑살랑). 800x450 뷰박스. */
export function GrassField() {
  return (
    <svg className="grass-field" viewBox="0 0 800 450" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <defs>
        <style>{`
          @keyframes grassSway1 { 0%,100%{transform:rotate(0)} 30%{transform:rotate(4deg) skewX(2deg)} 70%{transform:rotate(-3deg) skewX(-1deg)} }
          @keyframes grassSway2 { 0%,100%{transform:rotate(0)} 40%{transform:rotate(-5deg) skewX(-2deg)} 80%{transform:rotate(3deg) skewX(1deg)} }
          .gr{transform-box:fill-box;transform-origin:50% 100%;animation-timing-function:cubic-bezier(.2,.8,.2,1);animation-iteration-count:infinite}
          .g1{animation-name:grassSway1;animation-duration:2.5s;animation-delay:0s}
          .g2{animation-name:grassSway2;animation-duration:3.1s;animation-delay:.35s}
          .g3{animation-name:grassSway1;animation-duration:2.2s;animation-delay:.7s}
          .g4{animation-name:grassSway2;animation-duration:2.8s;animation-delay:.15s}
          .g5{animation-name:grassSway1;animation-duration:2.95s;animation-delay:1.1s}
          .g6{animation-name:grassSway2;animation-duration:2.4s;animation-delay:.55s}
          .g7{animation-name:grassSway1;animation-duration:3.3s;animation-delay:1.45s}
          .g8{animation-name:grassSway2;animation-duration:2.65s;animation-delay:.9s}
          .g9{animation-name:grassSway1;animation-duration:2.05s;animation-delay:1.7s}
          .g10{animation-name:grassSway2;animation-duration:3.45s;animation-delay:.25s}
          .g11{animation-name:grassSway1;animation-duration:2.75s;animation-delay:1.3s}
          .g12{animation-name:grassSway2;animation-duration:2.3s;animation-delay:1.95s}
          @keyframes cloudDrift { from{transform:translateX(0)} to{transform:translateX(40px)} }
          @keyframes cloudDrift2 { from{transform:translateX(0)} to{transform:translateX(-28px)} }
          .cloud{animation:cloudDrift 18s cubic-bezier(.2,.8,.2,1) infinite alternate}
          .cloud2{animation:cloudDrift2 25s cubic-bezier(.2,.8,.2,1) infinite alternate;animation-delay:-6s}
          @media (prefers-reduced-motion: reduce){ .gr,.cloud,.cloud2{animation:none} }
        `}</style>
        {/* 풀 포기 3종: 뾰족 2잎 / 둥근 3잎 / 길쭉 1잎 (원점 = 밑동) */}
        <path id="tuft-a" d="M-4 0 Q-6.5 -9 -2 -19 Q0 -10 1 -3 Q2.5 -12 7 -17 Q6 -8 4 0 Z" />
        <path id="tuft-b" d="M-7 0 Q-9.5 -8 -6 -13 Q-3 -8 -2 -3 Q-3.5 -12 0 -18 Q3 -12 2 -3 Q3.5 -9 6.5 -13 Q8 -7 6 0 Z" />
        <path id="tuft-c" d="M-2 0 Q-4.5 -12 3 -24 Q4 -10 2 0 Z" />
      </defs>

      {/* 하늘 */}
      <rect width="800" height="450" fill="#ffffff" />
      <g className="cloud" fill="#F1F5F3">
        <ellipse cx="140" cy="72" rx="44" ry="15" />
        <ellipse cx="172" cy="61" rx="28" ry="16" />
        <ellipse cx="199" cy="73" rx="23" ry="11" />
      </g>
      <g className="cloud2" fill="#EEF3F0">
        <ellipse cx="612" cy="86" rx="50" ry="14" />
        <ellipse cx="646" cy="76" rx="25" ry="14" />
        <ellipse cx="582" cy="80" rx="19" ry="10" />
      </g>

      {/* 먼 언덕 */}
      <path d="M0 254 Q42 230 88 206 Q124 191 166 189 Q208 186 246 205 Q288 227 326 233 Q372 244 418 227 Q470 205 520 195 Q574 181 626 191 Q690 203 742 211 Q776 219 800 222 L800 450 L0 450 Z" fill="#8FCB56" />
      <path d="M0 254 Q42 230 88 206 Q124 191 166 189 Q208 186 246 205 Q288 227 326 233 Q372 244 418 227 Q470 205 520 195 Q574 181 626 191 Q690 203 742 211 Q776 219 800 222" fill="none" stroke="#79B542" strokeWidth="1.5" strokeLinecap="round" opacity=".75" />

      {/* 중간 언덕 */}
      <path d="M0 302 Q36 287 74 270 Q112 253 156 259 Q196 263 232 279 Q272 301 318 306 Q360 312 402 297 Q448 285 492 271 Q536 261 582 255 Q628 253 672 263 Q716 271 758 283 Q782 289 800 292 L800 450 L0 450 Z" fill="#6FBA36" />
      <path d="M0 302 Q36 287 74 270 Q112 253 156 259 Q196 263 232 279 Q272 301 318 306 Q360 312 402 297 Q448 285 492 271 Q536 261 582 255 Q628 253 672 263 Q716 271 758 283 Q782 289 800 292" fill="none" stroke="#5AA328" strokeWidth="1.5" strokeLinecap="round" opacity=".8" />

      {/* 앞 언덕 (매장 구덩이가 놓이는 면) */}
      <path d="M0 348 Q40 337 92 326 Q146 315 204 319 Q262 321 316 329 Q368 341 420 342 Q476 343 528 351 Q584 356 636 345 Q690 337 744 330 Q774 326 800 332 L800 450 L0 450 Z" fill="#58a618" />
      <path d="M0 348 Q40 337 92 326 Q146 315 204 319 Q262 321 316 329 Q368 341 420 342 Q476 343 528 351 Q584 356 636 345 Q690 337 744 330 Q774 326 800 332" fill="none" stroke="#498E13" strokeWidth="1.5" strokeLinecap="round" opacity=".8" />

      {/* 큰 수풀 (고정) */}
      <g fill="#3E7D0F" opacity=".5">
        <ellipse cx="104" cy="301" rx="72" ry="6" transform="rotate(-1 104 301)" />
        <ellipse cx="712" cy="286" rx="68" ry="5.5" transform="rotate(1.5 712 286)" />
        <ellipse cx="346" cy="339" rx="50" ry="5" />
      </g>
      <g fill="#4C9414">
        <path d="M38 301 Q44 268 62 258 Q70 240 90 252 Q100 226 122 240 Q134 228 148 246 Q166 244 172 268 Q182 286 176 301 Z" />
        <path d="M636 286 Q644 250 664 244 Q672 226 694 236 Q708 212 730 230 Q748 226 758 246 Q778 250 782 286 Z" />
        <path d="M298 339 Q306 314 322 306 Q330 292 348 304 Q356 288 374 304 Q392 300 398 322 Q404 334 398 339 Z" />
      </g>
      {/* 수풀 안쪽 어두운 잎 덩어리 */}
      <g fill="#3E7D0F" opacity=".55">
        <ellipse cx="80" cy="283" rx="18" ry="11" transform="rotate(-8 80 283)" />
        <ellipse cx="128" cy="279" rx="22" ry="12" transform="rotate(6 128 279)" />
        <ellipse cx="106" cy="293" rx="14" ry="7" />
        <ellipse cx="672" cy="268" rx="16" ry="10" transform="rotate(-6 672 268)" />
        <ellipse cx="726" cy="262" rx="22" ry="12" transform="rotate(9 726 262)" />
        <ellipse cx="752" cy="275" rx="12" ry="7" />
        <ellipse cx="326" cy="326" rx="14" ry="8" transform="rotate(-5 326 326)" />
        <ellipse cx="368" cy="322" rx="16" ry="9" transform="rotate(7 368 322)" />
      </g>

      {/* 작은 풀 포기 (살랑살랑) — 크기 3단계, 색 3단계, 위상 전부 다름 */}
      <g transform="translate(58 226)"><g className="gr g1" fill="#6FBA36"><use href="#tuft-a" /></g></g>
      <g transform="translate(470 212)"><g className="gr g2" fill="#6FBA36"><use href="#tuft-c" /></g></g>
      <g transform="translate(598 196)"><g className="gr g3" fill="#6FBA36"><use href="#tuft-b" /></g></g>
      <g transform="translate(215 278) scale(1.5)"><g className="gr g4" fill="#58a618"><use href="#tuft-a" /></g></g>
      <g transform="translate(452 288) scale(1.5)"><g className="gr g5" fill="#58a618"><use href="#tuft-b" /></g></g>
      <g transform="translate(560 264) scale(1.5)"><g className="gr g6" fill="#58a618"><use href="#tuft-c" /></g></g>
      <g transform="translate(762 333) scale(1.5)"><g className="gr g7" fill="#58a618"><use href="#tuft-a" /></g></g>
      <g transform="translate(240 372) scale(1.5)"><g className="gr g8" fill="#4C9414"><use href="#tuft-a" /></g></g>
      <g transform="translate(138 400) scale(2.2)"><g className="gr g9" fill="#4C9414"><use href="#tuft-b" /></g></g>
      <g transform="translate(706 382) scale(2.2)"><g className="gr g10" fill="#4C9414"><use href="#tuft-a" /></g></g>
      <g transform="translate(30 402) scale(2.2)"><g className="gr g11" fill="#4C9414"><use href="#tuft-c" /></g></g>
      <g transform="translate(486 408) scale(2.2)"><g className="gr g12" fill="#4C9414"><use href="#tuft-b" /></g></g>

      {/* 작은 꽃 6송이 — 살짝 찌그러진 타원, 두 송이는 줄기 */}
      <g fill="none" stroke="#4C9414" strokeWidth="1" strokeLinecap="round">
        <path d="M200 372 Q201.5 366 199 360" />
        <path d="M560 358 Q558.5 352 561 346" />
      </g>
      <g>
        <ellipse cx="199" cy="358" rx="3.2" ry="2.8" fill="#FFD166" transform="rotate(-12 199 358)" />
        <ellipse cx="561" cy="344" rx="3.4" ry="3" fill="#FF8FA3" transform="rotate(15 561 344)" />
        <ellipse cx="430" cy="392" rx="2.4" ry="2.7" fill="#FFE08A" />
        <ellipse cx="88" cy="355" rx="2.6" ry="2.3" fill="#FFA5B8" transform="rotate(20 88 355)" />
        <ellipse cx="655" cy="398" rx="2.1" ry="2.4" fill="#F4B942" transform="rotate(-8 655 398)" />
        <ellipse cx="342" cy="368" rx="1.9" ry="1.7" fill="#FF8FA3" />
        <circle cx="199.3" cy="358.2" r=".9" fill="#E8A23A" />
        <circle cx="560.8" cy="344.3" r="1" fill="#E85D7A" />
      </g>
    </svg>
  )
}
