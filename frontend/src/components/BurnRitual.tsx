import { useEffect, useMemo, useState } from 'react'
import type { Amulet } from '../api'

/** 부적 태우기 전체화면 의식. phase: ignite(불 붙음) → slam(부적 내리꽂힘) → stamp(도장) → done */
type Phase = 'ignite' | 'slam' | 'stamp' | 'done'

export function BurnRitual({ amulet, loading, onClose }: { amulet: Amulet | null; loading: boolean; onClose: () => void }) {
  const [phase, setPhase] = useState<Phase>('ignite')
  const flames = useMemo(() => Array.from({ length: 34 }, (_, i) => ({ i, x: (i * 37) % 100, d: 0.9 + ((i * 7) % 10) / 10, s: 22 + ((i * 13) % 5) * 9, delay: ((i * 11) % 14) / 10 })), [])
  const embers = useMemo(() => Array.from({ length: 60 }, (_, i) => ({ i, x: (i * 53) % 100, d: 1.6 + ((i * 3) % 12) / 6, s: 3 + (i % 4), delay: ((i * 17) % 20) / 10 })), [])

  useEffect(() => { playIgnite() }, [])
  useEffect(() => {
    if (loading || !amulet) return
    // 데이터가 도착하면 최소 1.8초 불태운 뒤 내리꽂기
    const t1 = setTimeout(() => { setPhase('slam'); playSlam() }, 1800)
    const t2 = setTimeout(() => { setPhase('stamp'); playStamp() }, 1800 + 1400 + amulet.hanja.replace(/\n/g, '').length * 160)
    const t3 = setTimeout(() => setPhase('done'), 1800 + 1400 + amulet.hanja.replace(/\n/g, '').length * 160 + 700)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [loading, amulet])

  const chars = amulet ? amulet.hanja.split('\n') : []
  let idx = 0
  return (
    <div className={'burn ' + phase} onClick={phase === 'done' ? onClose : undefined}>
      <div className="burn-bg" />
      <div className="burn-flash" />
      <div className="burn-fire">
        {flames.map(f => <span key={f.i} className="fl" style={{ left: `${f.x}%`, fontSize: f.s, animationDuration: `${f.d}s`, animationDelay: `${f.delay}s` }}>{f.i % 5 === 0 ? '🔥' : f.i % 5 === 1 ? '🔥' : f.i % 5 === 2 ? '✨' : '🔥'}</span>)}
        {embers.map(e => <i key={e.i} className="em" style={{ left: `${e.x}%`, width: e.s, height: e.s, animationDuration: `${e.d}s`, animationDelay: `${e.delay}s` }} />)}
      </div>

      {phase === 'ignite' && (
        <div className="burn-center">
          <div className="burn-title pen">{loading ? '부적에 불을 붙이는 중…' : '불이 붙었다'}</div>
          <div className="burn-sub">{amulet ? `${amulet.attachment_label} 저주가 깨어난다` : '상대의 카톡 패턴을 읽는 중'}</div>
        </div>
      )}

      {amulet && phase !== 'ignite' && (
        <div className="burn-center">
          <div className="amulet big">
            <div className="am-head">{amulet.attachment_label} · X 저주 부적</div>
            <div className="am-hanja">
              {chars.map((col, ci) => (
                <span key={ci} className="am-col">
                  {Array.from(col).map(ch => { const k = idx++; return <b key={k} className="am-ch" style={{ animationDelay: `${0.5 + k * 0.16}s` }}>{ch}</b> })}
                </span>
              ))}
            </div>
            <div className="am-read">{amulet.reading}</div>
            <div className="am-mean">{amulet.meaning}</div>
            <div className="am-line">“{amulet.line}”</div>
            <div className={'am-seal' + (phase === 'stamp' || phase === 'done' ? ' hit' : '')}>封</div>
          </div>
          {phase === 'done' && <div className="burn-hint">아무 데나 눌러 닫기 · 저주는 이미 발송됐어</div>}
        </div>
      )}
    </div>
  )
}

/* ---------------- 합성 사운드 (파일 없음) */
let ctx: AudioContext | null = null
function ac() { try { ctx = ctx ?? new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)(); return ctx } catch { return null } }

function noise(c: AudioContext, dur: number, gainV: number, lp: number, hp = 80) {
  const buf = c.createBuffer(1, c.sampleRate * dur, c.sampleRate); const d = buf.getChannelData(0)
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length)
  const src = c.createBufferSource(); src.buffer = buf
  const f1 = c.createBiquadFilter(); f1.type = 'lowpass'; f1.frequency.value = lp
  const f2 = c.createBiquadFilter(); f2.type = 'highpass'; f2.frequency.value = hp
  const g = c.createGain(); g.gain.setValueAtTime(gainV, c.currentTime); g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + dur)
  src.connect(f1).connect(f2).connect(g).connect(c.destination); src.start()
}
function tone(c: AudioContext, f0: number, f1: number, dur: number, gainV: number, type: OscillatorType = 'sine') {
  const o = c.createOscillator(); o.type = type; o.frequency.setValueAtTime(f0, c.currentTime); o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), c.currentTime + dur)
  const g = c.createGain(); g.gain.setValueAtTime(gainV, c.currentTime); g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + dur)
  o.connect(g).connect(c.destination); o.start(); o.stop(c.currentTime + dur)
}
function playIgnite() { const c = ac(); if (!c) return; noise(c, 2.4, 0.5, 900, 120); tone(c, 55, 38, 2.6, 0.35, 'sawtooth') }
function playSlam() { const c = ac(); if (!c) return; noise(c, 0.35, 0.9, 400, 40); tone(c, 120, 30, 0.6, 0.9, 'square'); setTimeout(() => noise(c, 1.2, 0.3, 1200, 200), 120) }
function playStamp() { const c = ac(); if (!c) return; noise(c, 0.18, 0.8, 600, 60); tone(c, 90, 40, 0.35, 0.8, 'triangle') }
