/** 관계 코치 상담 모달. 백엔드 /chat(SSE)에 붙고, 코치가 update_context 툴로 사정을 기록하면
 *  context_updated 이벤트가 와서 onContextUpdated() → 앱이 진단서를 다시 받는다 (분석이 대화에 따라 바뀜). */
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Modal } from './ui'

export type CoachMsg = { role: 'user' | 'assistant'; content: string; sys?: boolean }

const OPENERS = ['우리 언제부터 식었어?', '내가 너무 매달렸나?', '걔가 먼저 연락한 적 있어?']
const HL = /<highlight>[\s\S]*?<\/highlight>/g

export function CoachChat({ name, msgs, setMsgs, onContextUpdated, onClose }: {
  name: string; msgs: CoachMsg[]; setMsgs: (m: CoachMsg[]) => void; onContextUpdated: () => void; onClose: () => void
}) {
  const [v, setV] = useState('')
  const [busy, setBusy] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => { box.current?.scrollTo({ top: 1e9 }) }, [msgs, busy])

  async function send(text?: string) {
    const t = (text ?? v).trim(); if (!t || busy) return
    const hist: CoachMsg[] = [...msgs, { role: 'user', content: t }]
    setMsgs(hist); setV(''); setBusy(true)
    let acc = ''
    let updated = false
    const paint = (extra?: CoachMsg) => setMsgs([...hist, { role: 'assistant', content: acc.replace(HL, '').trimEnd() }, ...(extra ? [extra] : [])])
    try {
      const r = await api.chat(hist.filter(m => !m.sys).map(m => ({ role: m.role, content: m.content })))
      if (!r.ok || !r.body) throw new Error(`${r.status}`)
      const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = ''
      for (;;) {
        const { value, done } = await reader.read(); if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n\n'); buf = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const ev = JSON.parse(line.slice(6)) as { delta?: string; error?: string; done?: boolean; text?: string; event?: { context_updated?: unknown } }
          if (ev.delta) { acc += ev.delta; paint() }
          if (ev.event?.context_updated) { updated = true; onContextUpdated() }
          if (ev.error) throw new Error(ev.error)
          if (ev.done && ev.text) acc = ev.text
        }
      }
      paint(updated ? { role: 'assistant', content: '↑ 네가 말해준 사정을 기록했어. 진단서·향년·사인·소환술이 그걸 우선해서 다시 계산됐어.', sys: true } : undefined)
    } catch (e) {
      setMsgs([...hist, { role: 'assistant', content: '지금은 코치가 답을 못 해. ' + String(e).slice(0, 80), sys: true }])
    } finally { setBusy(false) }
  }

  return (
    <Modal title="관계 코치 상담" onClose={onClose} bodyClass="summon-body coach-body">
      <p className="tiny muted" style={{ marginBottom: 12 }}>카톡 데이터를 보는 코치야 · 숫자엔 <span className="num">[#영수증]</span>이 붙어 · 사정을 말해주면 진단서가 그걸 우선해서 바뀌어</p>
      <div className="summon-chat" ref={box}>
        {msgs.length === 0 && <div className="rp-msg them">{name}이랑 어떻게 된 건지, 데이터에 없는 사정부터 말해줘도 되고 그냥 물어봐도 돼.</div>}
        {msgs.map((m, i) => (
          m.sys
            ? <div key={i} style={{ fontSize: 11, color: 'var(--rose-soft)', textAlign: 'center', margin: '4px 0 12px' }}>{m.content}</div>
            : <div key={i} className={'rp-msg ' + (m.role === 'user' ? 'me' : 'them')}>{m.content || (busy ? '…' : '')}</div>
        ))}
        {busy && (msgs[msgs.length - 1]?.role !== 'assistant' || msgs[msgs.length - 1]?.sys) && <div className="rp-msg them">…데이터 보는 중</div>}
      </div>
      {msgs.length === 0 && <div className="summon-quick">{OPENERS.map(q => <button key={q} onClick={() => send(q)}>{q}</button>)}</div>}
      <div className="summon-in"><input value={v} onChange={e => setV(e.target.value)} placeholder="물어보거나, 사정을 말해줘…" onKeyDown={e => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) send() }} disabled={busy} /><button onClick={() => send()} aria-label="보내기" disabled={busy}>↑</button></div>
    </Modal>
  )
}
