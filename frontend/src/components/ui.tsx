import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'

// ---------------------------------------------------------------- toast
const ToastCtx = createContext<(msg: string) => void>(() => {})
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)
  const toast = useCallback((m: string) => {
    setMsg(m)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setMsg(null), 2200)
  }, [])
  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className={'toast' + (msg ? ' show' : '')}>{msg}</div>
    </ToastCtx.Provider>
  )
}

// ---------------------------------------------------------------- modal
export function Modal({ title, onClose, children, bodyClass }: { title: string; onClose: () => void; children: ReactNode; bodyClass?: string }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="modal-bg" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal">
        <div className="modal-head"><strong>{title}</strong><button className="modal-close" onClick={onClose}>✕</button></div>
        <div className={'modal-body ' + (bodyClass ?? '')}>{children}</div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- helpers
export const fmtMin = (m: number | null | undefined) =>
  m == null ? '–' : m < 1 ? '1분 이내' : m < 60 ? `${Math.round(m)}분` : m < 1440 ? `${(m / 60).toFixed(1)}시간` : `${(m / 1440).toFixed(1)}일`
export const fmtDate = (iso: string) => `${iso.slice(0, 4)}.${iso.slice(5, 7)}.${iso.slice(8, 10)}`
export const fmtShort = (iso: string) => `${+iso.slice(5, 7)}.${iso.slice(8, 10)}`
export const fmtTime = (iso: string) => {
  const d = new Date(iso)
  const h = d.getHours()
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${h < 12 ? '오전' : '오후'} ${h % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ---------------------------------------------------------------- motion
const prefersReduced = () =>
  typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * 숫자 카운트업 (requestAnimationFrame, ease-out cubic).
 * - target 이 바뀌면 현재 표시값에서 새 target 으로 이어서 올라간다
 * - reduced-motion 이면 즉시 target
 * - 소수점 자릿수는 target 을 따라간다 (정수면 정수, 36.5 면 한 자리)
 */
export function useCountUp(target: number, ms = 900): number {
  const reduce = prefersReduced()
  const [val, setVal] = useState(() => (reduce || !Number.isFinite(target) ? target : 0))
  const shown = useRef(reduce || !Number.isFinite(target) ? target : 0)
  useEffect(() => {
    if (!Number.isFinite(target)) { shown.current = target; setVal(target); return }
    if (reduce || ms <= 0) { shown.current = target; setVal(target); return }
    const from = shown.current
    const dec = Number.isInteger(target) ? 0 : Math.min(2, (String(target).split('.')[1] ?? '').length)
    const t0 = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms)
      const e = 1 - Math.pow(1 - p, 3)
      const v = +(from + (target - from) * e).toFixed(dec)
      shown.current = v
      setVal(v)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms, reduce])
  return val
}

// ---------------------------------------------------------------- svg
type Pt = [number, number]
const f1 = (n: number) => n.toFixed(1)

/**
 * Catmull-Rom → cubic bezier path.
 * null 은 끊긴 구간(데이터 없음)으로 보고 새 서브패스를 연다.
 * yClamp 를 주면 제어점이 그 범위를 넘지 않게 눌러서 곡선이 축 밖으로 튀지 않게 한다.
 */
export function smoothPath(pts: (Pt | null)[], tension = 0.5, yClamp?: [number, number]): string {
  const runs: Pt[][] = []
  let cur: Pt[] = []
  for (const p of pts) { if (p) cur.push(p); else if (cur.length) { runs.push(cur); cur = [] } }
  if (cur.length) runs.push(cur)
  const k = tension / 3
  const cy = (y: number) => (yClamp ? Math.min(yClamp[1], Math.max(yClamp[0], y)) : y)
  return runs.map(run => {
    let d = `M${f1(run[0][0])} ${f1(run[0][1])}`
    for (let i = 0; i < run.length - 1; i++) {
      const p0 = run[i - 1] ?? run[i], p1 = run[i], p2 = run[i + 1], p3 = run[i + 2] ?? p2
      const c1x = p1[0] + (p2[0] - p0[0]) * k, c1y = cy(p1[1] + (p2[1] - p0[1]) * k)
      const c2x = p2[0] - (p3[0] - p1[0]) * k, c2y = cy(p2[1] - (p3[1] - p1[1]) * k)
      d += ` C${f1(c1x)} ${f1(c1y)} ${f1(c2x)} ${f1(c2y)} ${f1(p2[0])} ${f1(p2[1])}`
    }
    return d
  }).join(' ')
}
