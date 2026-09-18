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
  m == null ? '–' : m < 60 ? `${Math.round(m)}분` : m < 1440 ? `${(m / 60).toFixed(1)}시간` : `${(m / 1440).toFixed(1)}일`
export const fmtDate = (iso: string) => `${iso.slice(0, 4)}.${iso.slice(5, 7)}.${iso.slice(8, 10)}`
export const fmtShort = (iso: string) => `${+iso.slice(5, 7)}.${iso.slice(8, 10)}`
export const fmtTime = (iso: string) => {
  const d = new Date(iso)
  const h = d.getHours()
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${h < 12 ? '오전' : '오후'} ${h % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')}`
}
